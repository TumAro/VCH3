"""Unit tests for notification sources and service (T13)."""
from dataclasses import replace
from typing import List

from src.domain.models import DataIssue
from src.domain.notifications import Notification
from src.services.notification_service import (
    DataIssueNotificationSource,
    INotificationSource,
    NotificationService,
)
from tests.fakes import FakeRulesRepository

NEGATIVE = DataIssue("stock_snapshot", "LKO-01/SKU-1", "on_hand", "-3", "on_hand >= 0", "Marked untrusted")
MISMATCH = DataIssue(
    "stock_snapshot", "KNP-03/SHW-02-L", "on_hand", "Snapshot 300 vs Weekly 0",
    "snapshot on_hand == final weekly closing", "Marked untrusted",
)
UNKNOWN_RULE = DataIssue("bills", "B1", "bill_date", "2099-01-01", "date in range", "Dropped")


def collect(*issues):
    return DataIssueNotificationSource(FakeRulesRepository(list(issues))).collect()


def test_one_notification_per_issue_with_readable_title():
    items = collect(NEGATIVE, MISMATCH, UNKNOWN_RULE)
    assert [n.kind for n in items] == ["data_issue"] * 3
    assert items[0].title == "Negative stock on hand"
    assert items[1].title == "Snapshot disagrees with weekly stock"
    assert items[2].title == "Data issue in bills"
    assert "KNP-03/SHW-02-L" in items[1].detail
    assert "Marked untrusted" in items[1].detail


def test_same_content_gives_same_id_across_loads():
    assert collect(MISMATCH)[0].id == collect(MISMATCH)[0].id


def test_different_content_gives_different_id():
    changed = replace(MISMATCH, value_seen="Snapshot 301 vs Weekly 0")
    ids = {n.id for n in collect(NEGATIVE, MISMATCH, changed)}
    assert len(ids) == 3


def test_no_issues_gives_empty_list():
    assert collect() == []


class StaticSource(INotificationSource):
    def __init__(self, items: List[Notification]):
        self._items = items

    def collect(self) -> List[Notification]:
        return list(self._items)


def test_service_merges_sources_in_order():
    a = Notification("a", "data_issue", "A", "")
    b = Notification("b", "sign_off", "B", "")
    c = Notification("c", "data_issue", "C", "")
    service = NotificationService([StaticSource([a]), StaticSource([b, c])])
    assert service.get_all() == [a, b, c]


def test_service_with_no_sources_is_empty():
    assert NotificationService([]).get_all() == []
