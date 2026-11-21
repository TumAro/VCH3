"""Network overview: revenue by state/city/store, store stock totals, monthly revenue.

Revenue always comes from SalesLine.line_revenue (single source of truth, REQ-8).
"""
from collections import defaultdict
from datetime import date
from typing import Dict, List, Tuple

from src.domain.models import Store
from src.domain.overview import (
    CityOverview,
    MonthlyRevenue,
    NetworkOverview,
    StateOverview,
    StoreOverview,
)
from src.domain.repositories import IStockRepository, ISalesRepository, IStoreRepository


def _share_pct(part: float, whole: float) -> float:
    return (part / whole * 100.0) if whole else 0.0


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _month_range(first: date, last: date) -> List[str]:
    months = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return months


class NetworkOverviewService:
    def __init__(
        self,
        stores: IStoreRepository,
        sales: ISalesRepository,
        stock: IStockRepository,
    ):
        self._stores = stores
        self._sales = sales
        self._stock = stock

    def get_network_overview(self) -> NetworkOverview:
        stores = self._stores.get_all()
        revenue_by_store = self._revenue_by_store()
        stock_by_store = self._stock_by_store()

        # state -> city -> [StoreOverview]
        grouped: Dict[str, Dict[str, List[StoreOverview]]] = defaultdict(lambda: defaultdict(list))
        for store in stores:
            grouped[store.state][store.city].append(
                self._store_overview(store, revenue_by_store, stock_by_store)
            )

        total_revenue = sum(revenue_by_store.get(s.store_id, 0.0) for s in stores)

        states: List[StateOverview] = []
        for state_name, cities in grouped.items():
            state_revenue = sum(st.revenue for city in cities.values() for st in city)
            city_overviews = [
                CityOverview(
                    city=city_name,
                    store_count=len(city_stores),
                    revenue=sum(st.revenue for st in city_stores),
                    share_of_state_pct=_share_pct(sum(st.revenue for st in city_stores), state_revenue),
                    stores=sorted(city_stores, key=lambda st: (-st.revenue, st.store_id)),
                )
                for city_name, city_stores in cities.items()
            ]
            states.append(
                StateOverview(
                    state=state_name,
                    store_count=sum(c.store_count for c in city_overviews),
                    revenue=state_revenue,
                    share_pct=_share_pct(state_revenue, total_revenue),
                    cities=sorted(city_overviews, key=lambda c: (-c.revenue, c.city)),
                )
            )

        return NetworkOverview(
            total_revenue=total_revenue,
            store_count=len(stores),
            states=sorted(states, key=lambda s: (-s.revenue, s.state)),
        )

    def get_monthly_revenue(self) -> MonthlyRevenue:
        store_state = {s.store_id: s.state for s in self._stores.get_all()}
        state_names = sorted(set(store_state.values()))
        lines = [line for line in self._sales.get_all_sales_lines() if line.store_id in store_state]

        if not lines:
            return MonthlyRevenue(months=[], series={state: [] for state in state_names})

        months = _month_range(
            min(line.bill_date for line in lines),
            max(line.bill_date for line in lines),
        )
        index = {m: i for i, m in enumerate(months)}
        series = {state: [0.0] * len(months) for state in state_names}
        for line in lines:
            series[store_state[line.store_id]][index[_month_key(line.bill_date)]] += line.line_revenue
        return MonthlyRevenue(months=months, series=series)

    def _revenue_by_store(self) -> Dict[str, float]:
        totals: Dict[str, float] = defaultdict(float)
        for line in self._sales.get_all_sales_lines():
            totals[line.store_id] += line.line_revenue
        return totals

    def _stock_by_store(self) -> Dict[str, Tuple[int, int, int]]:
        """store_id -> (on_hand, in_transit, zero_stock_skus). Includes untrusted rows (see spec Risks)."""
        totals: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0])
        for pos in self._stock.get_snapshot_positions():
            t = totals[pos.location_id]
            t[0] += pos.on_hand
            t[1] += pos.in_transit
            if pos.on_hand == 0:
                t[2] += 1
        return {k: (v[0], v[1], v[2]) for k, v in totals.items()}

    @staticmethod
    def _store_overview(
        store: Store,
        revenue_by_store: Dict[str, float],
        stock_by_store: Dict[str, Tuple[int, int, int]],
    ) -> StoreOverview:
        on_hand, in_transit, zero_skus = stock_by_store.get(store.store_id, (0, 0, 0))
        return StoreOverview(
            store_id=store.store_id,
            tier=store.tier,
            revenue=revenue_by_store.get(store.store_id, 0.0),
            on_hand=on_hand,
            in_transit=in_transit,
            capacity=store.stock_capacity_units,
            utilisation_pct=_share_pct(on_hand, store.stock_capacity_units),
            zero_stock_skus=zero_skus,
        )
