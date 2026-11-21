"""Holds the currently loaded data and performs safe re-runs (REQ-6, REQ-12)."""
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List

from src.domain.notifications import Notification
from src.domain.overview import MonthlyRevenue, NetworkOverview
from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.services.network_overview_service import NetworkOverviewService
from src.services.notification_service import DataIssueNotificationSource, NotificationService


@dataclass(frozen=True)
class LoadedData:
    container: InMemoryRepositoryContainer
    overview: NetworkOverview
    monthly: MonthlyRevenue
    notifications: List[Notification]
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
        self._loaded = self._load()

    def current(self) -> LoadedData:
        return self._loaded

    def rerun(self) -> LoadedData:
        """Load into a fresh container; swap only on success. On failure the previous data stays."""
        with self._lock:
            loaded = self._load()
            self._loaded = loaded
            return loaded

    def _load(self) -> LoadedData:
        container = self._factory(self._data_dir)
        overview_service = NetworkOverviewService(container.stores, container.sales, container.stock)
        notification_service = NotificationService([DataIssueNotificationSource(container.rules)])
        return LoadedData(
            container=container,
            overview=overview_service.get_network_overview(),
            monthly=overview_service.get_monthly_revenue(),
            notifications=notification_service.get_all(),
            last_run=self._clock(),
        )
