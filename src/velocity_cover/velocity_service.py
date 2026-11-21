"""Stockout-aware velocity calculations and peer fallbacks."""
from collections import defaultdict
from datetime import timedelta
from typing import Dict, Iterable, Tuple

from src.domain.models import Store, WeeklyStock
from src.velocity_cover.models import AggregateVelocity, DailyVelocity
from src.velocity_cover.repositories import VelocityCoverRepository


AS_OF_DATE = (2026, 10, 31)


class VelocityService:
    def __init__(self, repository: VelocityCoverRepository):
        self.repository = repository

    def compute(
        self,
    ) -> Tuple[Tuple[DailyVelocity, ...], Tuple[AggregateVelocity, ...], Tuple[AggregateVelocity, ...]]:
        weekly = self.repository.stock.get_all_weekly_stock()
        sales = self.repository.sales.get_all_sales_lines()
        items = {item.sku_id: item for item in self.repository.items.get_all()}
        stores = {store.store_id: store for store in self.repository.stores.get_all()}

        week_dates = sorted({row.week_ending for row in weekly})
        if not week_dates:
            return (), (), ()

        window_start = week_dates[0] - timedelta(days=6)
        window_end = week_dates[-1]
        sales_totals: Dict[Tuple[str, str], int] = defaultdict(int)
        for line in sales:
            if window_start <= line.bill_date <= window_end:
                sales_totals[(line.store_id, line.sku_id)] += line.qty

        weekly_totals: Dict[Tuple[str, str], list] = defaultdict(lambda: [0, 0])
        for row in weekly:
            if row.store_id in stores and row.sku_id in items:
                aggregate = weekly_totals[(row.store_id, row.sku_id)]
                aggregate[0] += row.days_in_stock
                aggregate[1] += row.closing_on_hand

        sku_keys = set(weekly_totals)
        sku_keys.update(key for key in sales_totals if key[1] in items)

        base_velocities: Dict[Tuple[str, str], DailyVelocity] = {}
        for store_id, sku_id in sorted(sku_keys):
            quantity_sold = sales_totals[(store_id, sku_id)]
            days_in_stock = weekly_totals[(store_id, sku_id)][0]
            base_velocities[(store_id, sku_id)] = self._direct_velocity(
                store_id, sku_id, quantity_sold, days_in_stock
            )

        velocities = {}
        for key, direct in sorted(base_velocities.items()):
            store = stores.get(key[0])
            if store and store.is_new_store:
                fallback = self._peer_fallback(key[1], store, stores, base_velocities)
                velocities[key] = DailyVelocity(
                    store_id=key[0],
                    sku_id=key[1],
                    quantity_sold=direct.quantity_sold,
                    days_in_stock=direct.days_in_stock,
                    velocity=fallback.velocity,
                    is_peer_fallback=True,
                    peer_store_ids=fallback.peer_store_ids,
                )
            else:
                velocities[key] = direct

        sku_results = tuple(velocities[key] for key in sorted(velocities))
        style_totals: Dict[Tuple[str, str], list] = defaultdict(lambda: [0, 0])
        category_totals: Dict[Tuple[str, str], list] = defaultdict(lambda: [0, 0])

        for result in sku_results:
            item = items.get(result.sku_id)
            if not item:
                continue
            style_key = (result.store_id, item.style_id)
            category_key = (result.store_id, item.category)
            style_totals[style_key][0] += result.quantity_sold
            style_totals[style_key][1] += result.days_in_stock
            category_totals[category_key][0] += result.quantity_sold
            category_totals[category_key][1] += result.days_in_stock

        style_results = tuple(
            self._aggregate("style", store_id, level_id, totals)
            for (store_id, level_id), totals in sorted(style_totals.items())
        )
        category_results = tuple(
            self._aggregate("category", store_id, level_id, totals)
            for (store_id, level_id), totals in sorted(category_totals.items())
        )
        return sku_results, style_results, category_results

    @staticmethod
    def _direct_velocity(store_id: str, sku_id: str, quantity_sold: int, days: int) -> DailyVelocity:
        if days > 0:
            velocity = quantity_sold / days
        elif quantity_sold == 0:
            velocity = 0.0
        else:
            velocity = 0.0
        return DailyVelocity(store_id, sku_id, quantity_sold, days, velocity)

    def _peer_fallback(
        self,
        sku_id: str,
        target_store: Store,
        stores: Dict[str, Store],
        velocities: Dict[Tuple[str, str], DailyVelocity],
    ) -> DailyVelocity:
        peer_tiers = (target_store.tier, "A", "S+", "S++")
        peer_ids = ()
        peer_values = []

        for tier in peer_tiers:
            candidates = [
                store.store_id
                for store in stores.values()
                if store.store_id != target_store.store_id
                and store.city == target_store.city
                and not store.is_new_store
                and store.tier == tier
            ]
            peer_rows = [
                velocities[(peer_id, sku_id)]
                for peer_id in sorted(candidates)
                if (peer_id, sku_id) in velocities
                and velocities[(peer_id, sku_id)].days_in_stock > 0
            ]
            peer_values = [row.velocity for row in peer_rows]
            if peer_values:
                peer_ids = tuple(row.store_id for row in peer_rows)
                break

        if not peer_values:
            candidates = [
                store.store_id
                for store in stores.values()
                if store.store_id != target_store.store_id
                and store.city == target_store.city
                and not store.is_new_store
            ]
            peer_rows = [
                velocities[(peer_id, sku_id)]
                for peer_id in sorted(candidates)
                if (peer_id, sku_id) in velocities
                and velocities[(peer_id, sku_id)].days_in_stock > 0
            ]
            peer_values = [row.velocity for row in peer_rows]
            peer_ids = tuple(row.store_id for row in peer_rows)

        fallback_velocity = sum(peer_values) / len(peer_values) if peer_values else 0.0
        return DailyVelocity(
            target_store.store_id,
            sku_id,
            0,
            0,
            fallback_velocity,
            True,
            peer_ids,
        )

    @staticmethod
    def _aggregate(level: str, store_id: str, level_id: str, totals: Iterable[int]) -> AggregateVelocity:
        quantity_sold, days = tuple(totals)
        velocity = quantity_sold / days if days > 0 else (0.0 if quantity_sold == 0 else 0.0)
        return AggregateVelocity(store_id, level, level_id, quantity_sold, days, velocity)
