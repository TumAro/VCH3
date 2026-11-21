"""Deterministic evidence retrieval for the Manager Assistant."""
from typing import Iterable, List, Optional, Sequence, Tuple

from src.domain.assistant import DailyTask, EvidenceRecord
from src.domain.notifications import Notification
from src.domain.overview import MonthlyRevenue, NetworkOverview


class AssistantEvidenceService:
    def __init__(
        self,
        overview: NetworkOverview,
        monthly: MonthlyRevenue,
        notifications: Sequence[Notification] = (),
    ):
        self.overview = overview
        self.monthly = monthly
        self.notifications = tuple(notifications)

    def retrieve(self, query: str) -> List[EvidenceRecord]:
        query_l = query.lower()
        records: List[EvidenceRecord] = []

        for state in self.overview.states:
            for city in state.cities:
                for store in city.stores:
                    if self._asks_scope(query_l, store.store_id, "store"):
                        records.append(self._store_record(
                            store.store_id,
                            store.tier,
                            store.revenue,
                            store.on_hand,
                            store.in_transit,
                            store.capacity,
                            store.zero_stock_skus,
                            store.utilisation_pct,
                        ))

        if self._asks_network(query_l):
            records.append(EvidenceRecord(
                source_id="network-total",
                source_type="network_overview",
                scope="network",
                metric="total_revenue",
                value=round(self.overview.total_revenue, 2),
                unit="INR",
                source_label="Network total revenue",
            ))
            records.append(EvidenceRecord(
                source_id="network-store-count",
                source_type="network_overview",
                scope="network",
                metric="store_count",
                value=self.overview.store_count,
                unit="stores",
                source_label="Network store count",
            ))

        for state in self.overview.states:
            if self._asks_scope(query_l, state.state, "state"):
                records.append(EvidenceRecord(
                    source_id=f"state-revenue-{state.state}",
                    source_type="network_overview",
                    scope=f"state:{state.state}",
                    metric="revenue",
                    value=round(state.revenue, 2),
                    unit="INR",
                    source_label=f"State revenue / {state.state}",
                    details={"store_count": state.store_count, "revenue_share_pct": state.share_pct},
                ))
                for city in state.cities:
                    if self._asks_scope(query_l, city.city, "city") or not self._has_specific_location(query_l):
                        records.append(EvidenceRecord(
                            source_id=f"city-revenue-{city.city}",
                            source_type="network_overview",
                            scope=f"city:{city.city}",
                            metric="revenue",
                            value=round(city.revenue, 2),
                            unit="INR",
                            source_label=f"City revenue / {city.city}",
                            details={"store_count": city.store_count},
                        ))
                        for store in city.stores:
                            if self._asks_scope(query_l, store.store_id, "store") or not self._has_specific_location(query_l):
                                records.append(self._store_record(store.store_id, store.tier, store.revenue,
                                                                   store.on_hand, store.in_transit,
                                                                   store.capacity, store.zero_stock_skus,
                                                                   store.utilisation_pct))

        if self._asks_monthly(query_l):
            for state, values in self.monthly.series.items():
                if not self._has_state_or_location(query_l) or state.lower() in query_l:
                    total = sum(values)
                    records.append(EvidenceRecord(
                        source_id=f"monthly-revenue-{state}",
                        source_type="monthly_revenue",
                        scope=f"state:{state}",
                        metric="revenue_total",
                        value=round(total, 2),
                        unit="INR",
                        source_label=f"Monthly revenue total / {state}",
                        details={
                            "months": len(values),
                            "latest_month": self.monthly.months[-1] if self.monthly.months else "",
                            "latest_value": values[-1] if values else 0,
                        },
                    ))

        if self._asks_notifications(query_l):
            for notification in self.notifications:
                records.append(EvidenceRecord(
                    source_id=f"notification-{notification.id}",
                    source_type="notification",
                    scope="network",
                    metric="data_issue",
                    value=notification.title,
                    unit="notification",
                    source_label=f"Notification / {notification.title}",
                    details={"detail": notification.detail},
                ))

        if not records and self._has_specific_location(query_l):
            return []
        if not records:
            records = [EvidenceRecord(
                source_id="network-total",
                source_type="network_overview",
                scope="network",
                metric="total_revenue",
                value=round(self.overview.total_revenue, 2),
                unit="INR",
                source_label="Network total revenue",
            )]
        return records[:20]

    def daily_tasks(self) -> List[DailyTask]:
        candidates: List[DailyTask] = []

        for state in self.overview.states:
            for city in state.cities:
                for store in city.stores:
                    if store.zero_stock_skus > 0:
                        evidence_id = f"store-stock-{store.store_id}"
                        candidates.append(DailyTask(
                            rank=0,
                            owner=store.store_id,
                            action=f"Review the {store.zero_stock_skus} zero-stock SKU positions at opening.",
                            reason="The latest trusted snapshot contains zero on-hand stock for these SKU positions.",
                            timing="Today, before replenishment review",
                            impact_value=float(store.zero_stock_skus),
                            impact_unit="zero-stock SKUs",
                            evidence_ids=[evidence_id],
                        ))

        for notification in self.notifications:
            evidence_id = f"notification-{notification.id}"
            owner = notification.detail.split(":", 1)[0].strip() or "Network"
            candidates.append(DailyTask(
                rank=0,
                owner=owner,
                action="Verify the flagged source row with operations before using it in a decision.",
                reason=notification.title,
                timing="Today",
                impact_value=1.0,
                impact_unit="data-issue",
                evidence_ids=[evidence_id],
            ))

        candidates.sort(key=lambda task: (
            task.impact_unit == "data-issue",
            -task.impact_value,
            task.owner,
        ))
        ranked: List[DailyTask] = []
        for rank, task in enumerate(candidates[:5], start=1):
            ranked.append(DailyTask(
                rank=rank,
                owner=task.owner,
                action=task.action,
                reason=task.reason,
                timing=task.timing,
                impact_value=task.impact_value,
                impact_unit=task.impact_unit,
                evidence_ids=task.evidence_ids,
            ))
        return ranked

    @staticmethod
    def _store_record(store_id, tier, revenue, on_hand, in_transit, capacity,
                      zero_stock_skus, utilisation_pct) -> EvidenceRecord:
        return EvidenceRecord(
            source_id=f"store-stock-{store_id}",
            source_type="network_overview",
            scope=f"store:{store_id}",
            metric="stock_and_revenue",
            value=round(revenue, 2),
            unit="INR",
            source_label=f"Store overview / {store_id}",
            details={
                "tier": tier,
                "on_hand": on_hand,
                "in_transit": in_transit,
                "capacity": capacity,
                "utilisation_pct": utilisation_pct,
                "zero_stock_skus": zero_stock_skus,
            },
        )

    @staticmethod
    def _asks_network(query: str) -> bool:
        return any(word in query for word in ("network", "overall", "all stores", "total"))

    @staticmethod
    def _asks_monthly(query: str) -> bool:
        return any(word in query for word in ("month", "trend", "revenue"))

    @staticmethod
    def _asks_notifications(query: str) -> bool:
        return any(word in query for word in ("notification", "issue", "data problem"))

    @staticmethod
    def _has_state_or_location(query: str) -> bool:
        return any(word in query for word in (
            "uttar", "pradesh", "bihar", "karnataka", "lucknow", "kanpur",
            "patna", "muzaffarpur", "bengaluru", "mysuru", "store",
            "lko-", "knp-", "pat-", "muz-", "blr-", "mys-",
        ))

    @staticmethod
    def _has_specific_location(query: str) -> bool:
        return any(word in query for word in (
            "lucknow", "kanpur", "patna", "muzaffarpur", "bengaluru", "mysuru",
            "lko-", "knp-", "pat-", "muz-", "blr-", "mys-",
        ))

    @staticmethod
    def _asks_scope(query: str, name: str, scope_type: str) -> bool:
        del scope_type
        normalized = name.lower().replace("_", " ")
        return normalized in query
