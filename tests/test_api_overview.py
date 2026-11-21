"""API tests on a temporary copy of data/csv (T7). The real data folder is never modified."""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

SOURCE_DIR = Path("data/csv")


@pytest.fixture()
def data_dir(tmp_path):
    target = tmp_path / "csv"
    shutil.copytree(SOURCE_DIR, target)
    return target


@pytest.fixture()
def client(data_dir):
    return TestClient(create_app(data_dir))


def _state_revenue(client, state):
    return next(s["revenue"] for s in client.get("/api/network").json()["states"] if s["state"] == state)


def _append(path, line):
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")


def test_network_shape(client):
    body = client.get("/api/network").json()
    assert body["store_count"] == 20
    state = body["states"][0]
    assert {"state", "store_count", "revenue", "share_pct", "cities"} <= set(state)
    store = state["cities"][0]["stores"][0]
    assert {"store_id", "tier", "revenue", "on_hand", "in_transit", "capacity",
            "utilisation_pct", "zero_stock_skus"} <= set(store)


def test_monthly_shape(client):
    body = client.get("/api/revenue/monthly").json()
    assert len(body["months"]) == 24
    assert {s["state"] for s in body["series"]} == {"Uttar Pradesh", "Bihar", "Karnataka"}
    assert all(len(s["values"]) == 24 for s in body["series"])


def test_ac5_manual_csv_edit_reflected_after_sync(client, data_dir):
    before_rev = _state_revenue(client, "Uttar Pradesh")
    before_run = client.get("/api/status").json()["last_run"]

    _append(data_dir / "bills.csv", "B9999999,2026-10-31,LKO-01,SP1009,C00000001")
    _append(data_dir / "bill_lines.csv", "B9999999,SHW-01-M,1,24599,20000")

    resp = client.post("/api/sync")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ok"
    assert _state_revenue(client, "Uttar Pradesh") == pytest.approx(before_rev + 20000)
    assert client.get("/api/status").json()["last_run"] >= before_run


def _notification_ids(client):
    return [n["id"] for n in client.get("/api/notifications").json()["items"]]


def test_ac13_notifications_on_real_data(client):
    items = client.get("/api/notifications").json()["items"]
    assert len(items) == 4
    assert all({"id", "kind", "title", "detail"} <= set(n) for n in items)
    assert any("KNP-03/SHW-02-L" in n["detail"] for n in items)


def test_ac13_new_issue_after_sync_adds_one_id(client, data_dir):
    before = _notification_ids(client)
    # Warehouse row: a store row would also break the snapshot-vs-weekly rule and raise two issues.
    _append(data_dir / "stock_snapshot.csv", "2026-10-31,WH-KOL,SHW-01-M,-2,0,,2026-10-01")

    assert client.post("/api/sync").status_code == 200
    after = _notification_ids(client)

    assert set(before) <= set(after)
    assert len(set(after) - set(before)) == 1


def test_failed_sync_keeps_last_good_data(client, data_dir):
    before_net = client.get("/api/network").json()
    before_run = client.get("/api/status").json()["last_run"]

    (data_dir / "stores.csv").unlink()

    resp = client.post("/api/sync")
    assert resp.status_code == 500
    assert resp.json()["status"] == "error"
    assert client.get("/api/network").json() == before_net
    assert client.get("/api/status").json()["last_run"] == before_run
