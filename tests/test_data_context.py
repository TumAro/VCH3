"""DataContext safe re-run behaviour, with a fake container factory (T6)."""
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from src.api.data_context import DataContext
from src.domain.models import SalesLine, Store
from tests.fakes import FakeRulesRepository, FakeSalesRepository, FakeStockRepository, FakeStoreRepository

STORE = Store("A-01", "Alpha", "StateX", "Z", "A", 1000, 100, date(2020, 1, 1), "AM-01")


def container_with_revenue(price):
    line = SalesLine("B1", date(2025, 1, 1), "A-01", "SP", "C", "S", 1, price, price)
    return SimpleNamespace(
        stores=FakeStoreRepository([STORE]),
        sales=FakeSalesRepository([line]),
        stock=FakeStockRepository([]),
        rules=FakeRulesRepository([]),
    )


class ScriptedFactory:
    """Returns the next scripted result per call; an Exception instance is raised."""

    def __init__(self, *results):
        self._results = list(results)

    def __call__(self, _path):
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class TickingClock:
    def __init__(self):
        self.t = 0

    def __call__(self):
        self.t += 1
        return datetime(2026, 11, 21, 10, 0, self.t)


def test_successful_rerun_swaps_data_and_updates_last_run():
    ctx = DataContext("unused", ScriptedFactory(container_with_revenue(100), container_with_revenue(250)), TickingClock())
    first = ctx.current()
    assert first.overview.total_revenue == 100

    ctx.rerun()
    after = ctx.current()
    assert after.overview.total_revenue == 250
    assert after.last_run > first.last_run


def test_failed_rerun_keeps_previous_data_and_last_run():
    ctx = DataContext("unused", ScriptedFactory(container_with_revenue(100), ValueError("bad csv")), TickingClock())
    before = ctx.current()

    with pytest.raises(ValueError):
        ctx.rerun()

    assert ctx.current() is before
    assert ctx.current().overview.total_revenue == 100
