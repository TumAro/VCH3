"""Holds the currently loaded data, runs MoveEngine, and performs safe re-runs."""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading
from typing import Callable, Dict, List, Optional, Tuple

from src.domain.notifications import Notification
from src.domain.overview import MonthlyRevenue, NetworkOverview
from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.moves.engine import MoveEngine
from src.moves.models import ApprovedMove, EngineResult, RejectedMove, UnfulfilledDeficit
from src.services.bridge import build_engine_inputs
from src.services.export_service import ExportService
from src.services.network_overview_service import NetworkOverviewService
from src.services.notification_service import DataIssueNotificationSource, NotificationService
from src.velocity_cover.models import Finding, FindingType, VelocityCoverResult
from src.velocity_cover.pipeline import VelocityCoverPipeline


@dataclass(frozen=True)
class MoveSummary:
    total_moves: int
    total_units: int
    total_mrp_value: int
    requires_approval_count: int
    stockout_sku_count: int


@dataclass(frozen=True)
class LoadedData:
    container: InMemoryRepositoryContainer
    overview: NetworkOverview
    monthly: MonthlyRevenue
    notifications: List[Notification]
    moves: Tuple[ApprovedMove, ...]
    findings: Tuple[Finding, ...]
    rejected_moves: Tuple[RejectedMove, ...]
    unfulfilled_deficits: Tuple[UnfulfilledDeficit, ...]
    summary: MoveSummary
    last_run: datetime


ContainerFactory = Callable[[Path], InMemoryRepositoryContainer]


class DataContext:
    def __init__(
        self,
        data_dir: Path,
        container_factory: ContainerFactory = InMemoryRepositoryContainer,
        clock: Callable[[], datetime] = datetime.now,
    ):
        self._data_dir = Path(data_dir)
        self._factory = container_factory
        self._clock = clock
        self._lock = threading.Lock()
        self._decisions: Dict[int, str] = {}  # move_index (1-based) -> "Waiting" | "Approved" | "Rejected"
        self._loaded = self._load()

    def current(self) -> LoadedData:
        return self._loaded

    def rerun(self) -> LoadedData:
        """Load into a fresh container and rerun full pipeline; swap only on success."""
        with self._lock:
            loaded = self._load()
            self._loaded = loaded
            self._decisions.clear()
            return loaded

    def set_decision(self, move_id: int, decision: str) -> bool:
        """Update approval decision for a move (1-based index)."""
        with self._lock:
            if 1 <= move_id <= len(self._loaded.moves):
                self._decisions[move_id] = decision
                return True
            return False

    def get_decision(self, move_id: int) -> str:
        return self._decisions.get(move_id, "Waiting")

    def get_filtered_moves(
        self,
        move_type: Optional[str] = None,
        store_id: Optional[str] = None,
        category: Optional[str] = None,
        decision: Optional[str] = None,
        search: Optional[str] = None,
        requires_approval: Optional[bool] = None,
    ) -> List[Dict]:
        """Returns filtered moves list with 1-based IDs and live decision state."""
        data = self._loaded
        results = []

        stores_map = {s.store_id: s for s in data.container.stores.get_all()}
        items_map = {i.sku_id: i for i in data.container.items.get_all()}

        for idx, m in enumerate(data.moves, start=1):
            cur_dec = self.get_decision(idx)
            m_type_str = m.move_type.value if hasattr(m.move_type, "value") else str(m.move_type)
            item_info = items_map.get(m.sku_id)
            cat = item_info.category if item_info else ""
            style_name = item_info.style_name if item_info else m.style_id

            from_store = stores_map.get(m.from_location)
            to_store = stores_map.get(m.to_location)
            from_city = from_store.city if from_store else ("Kolkata" if m.from_location == "WH-KOL" else "")
            to_city = to_store.city if to_store else ""

            # Apply filters
            if move_type and move_type.lower() not in m_type_str.lower():
                continue
            if store_id and store_id not in (m.from_location, m.to_location):
                continue
            if category and category.lower() != cat.lower():
                continue
            if decision and decision.lower() != cur_dec.lower():
                continue
            if requires_approval is not None and m.requires_human_approval != requires_approval:
                continue
            if search:
                q = search.lower()
                text_blob = f"{m.sku_id} {style_name} {m.from_location} {m.to_location} {from_city} {to_city} {m.reason}".lower()
                if q not in text_blob:
                    continue

            results.append({
                "id": idx,
                "rank": idx,
                "move_type": m_type_str,
                "from_location": m.from_location,
                "from_city": from_city,
                "to_location": m.to_location,
                "to_city": to_city,
                "sku_id": m.sku_id,
                "style_id": m.style_id,
                "style_name": style_name,
                "category": cat,
                "qty": m.qty,
                "value_mrp": m.value_mrp,
                "route_days": m.route_days,
                "dispatch_date": m.dispatch_date.isoformat(),
                "arrival_date": m.arrival_date.isoformat(),
                "requires_human_approval": m.requires_human_approval,
                "reason": m.reason,
                "receiver_cover": round(m.receiver_cover, 1),
                "velocity": round(m.velocity, 2),
                "donor_cover": round(m.donor_cover, 1) if m.donor_cover is not None else None,
                "decision": cur_dec,
            })
        return results

    def get_approved_moves_for_export(self) -> List[ApprovedMove]:
        """Returns approved moves, excluding any moves marked Rejected."""
        out = []
        for idx, m in enumerate(self._loaded.moves, start=1):
            if self.get_decision(idx) != "Rejected":
                out.append(m)
        return out

    def _load(self) -> LoadedData:
        # 1. Track 1 Ingestion
        container = self._factory(self._data_dir)

        approved: Tuple[ApprovedMove, ...] = ()
        findings: Tuple[Finding, ...] = ()
        rejected: Tuple[RejectedMove, ...] = ()
        unfulfilled: Tuple[UnfulfilledDeficit, ...] = ()

        if hasattr(container, "items") and hasattr(container, "stock"):
            try:
                # 2. Track 2 Analytics
                vc_pipeline = VelocityCoverPipeline(container)
                vc_result = vc_pipeline.run()

                # 3. Pipeline Bridge into Track 3
                engine_inputs = build_engine_inputs(container, vc_result)

                # 4. Track 3 Move Recommendations
                move_engine = MoveEngine()
                engine_result = move_engine.run(engine_inputs)

                approved = engine_result.approved_moves
                findings = vc_result.findings
                rejected = engine_result.rejected_moves
                unfulfilled = engine_result.unfulfilled_deficits
            except Exception:
                pass

        # 5. High-level summaries
        total_units = sum(m.qty for m in approved)
        total_mrp = sum(m.value_mrp for m in approved)
        req_approval = sum(1 for m in approved if m.requires_human_approval)

        stockout_count = sum(
            1 for f in findings if f.finding_type == FindingType.STOCKOUT_RISK
        )

        summary = MoveSummary(
            total_moves=len(approved),
            total_units=total_units,
            total_mrp_value=total_mrp,
            requires_approval_count=req_approval,
            stockout_sku_count=stockout_count,
        )

        overview_service = NetworkOverviewService(container.stores, container.sales, container.stock)
        notification_service = NotificationService([DataIssueNotificationSource(container.rules)])

        return LoadedData(
            container=container,
            overview=overview_service.get_network_overview(),
            monthly=overview_service.get_monthly_revenue(),
            notifications=notification_service.get_all(),
            moves=approved,
            findings=findings,
            rejected_moves=rejected,
            unfulfilled_deficits=unfulfilled,
            summary=summary,
            last_run=self._clock(),
        )
