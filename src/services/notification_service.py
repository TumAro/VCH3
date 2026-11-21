"""Notifications: pluggable sources merged by one service (REQ-15).

New notification kinds (e.g. Part B sign-off) are added as new INotificationSource
implementations; NotificationService does not change.
"""
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Sequence

from src.domain.models import DataIssue
from src.domain.notifications import Notification
from src.domain.repositories import IRulesRepository


def content_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


class INotificationSource(ABC):
    @abstractmethod
    def collect(self) -> List[Notification]:
        """Return this source's current notifications."""


class DataIssueNotificationSource(INotificationSource):
    """One notification per ingestion data issue.

    Depends on IRulesRepository only because Track 1 exposes data issues there
    (interface-segregation issue noted in the spec; not changed here).
    """

    KIND = "data_issue"
    TITLES: Dict[str, str] = {
        "on_hand >= 0": "Negative stock on hand",
        "snapshot on_hand == final weekly closing": "Snapshot disagrees with weekly stock",
        "store total on_hand <= capacity": "Store stock over capacity",
    }

    def __init__(self, rules: IRulesRepository):
        self._rules = rules

    def collect(self) -> List[Notification]:
        return [self._to_notification(issue) for issue in self._rules.get_all_data_issues()]

    def _to_notification(self, issue: DataIssue) -> Notification:
        title = self.TITLES.get(issue.rule_violated, f"Data issue in {issue.table}")
        return Notification(
            id=content_id(self.KIND, issue.table, issue.key, issue.column, issue.rule_violated, issue.value_seen),
            kind=self.KIND,
            title=title,
            detail=f"{issue.key}: {issue.value_seen}. {issue.action_taken}.",
        )


class NotificationService:
    def __init__(self, sources: Sequence[INotificationSource]):
        self._sources = list(sources)

    def get_all(self) -> List[Notification]:
        return [n for source in self._sources for n in source.collect()]
