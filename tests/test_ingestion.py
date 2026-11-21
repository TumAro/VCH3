"""Unit and integration tests for Track 1 Data Ingestion & Repository Layer."""
from datetime import date
from pathlib import Path
import time
import pytest

from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.infrastructure.csv_adapter import CSVDataSourceAdapter


DATA_DIR = Path("data/csv")


@pytest.fixture(scope="module")
def repo_container():
    """Load the full dataset once for the test module."""
    return InMemoryRepositoryContainer(DATA_DIR)


def test_store_loading(repo_container):
    stores = repo_container.stores.get_all()
    assert len(stores) == 20, f"Expected 20 stores, got {len(stores)}"

    # Check store IDs are strings
    for s in stores:
        assert isinstance(s.store_id, str)
        assert len(s.store_id) >= 5

    # Check BLR-05 is marked as new store (< 28 days history)
    blr05 = repo_container.stores.get_by_id("BLR-05")
    assert blr05 is not None
    assert blr05.is_new_store is True
    assert blr05.opened_on == date(2026, 10, 10)

    # Check established stores have is_new_store == False
    lko01 = repo_container.stores.get_by_id("LKO-01")
    assert lko01 is not None
    assert lko01.is_new_store is False


def test_packaging_exclusion(repo_container):
    items = repo_container.items.get_all()
    # 385 items total - 3 packaging items = 382 non-packaging items
    assert len(items) == 382, f"Expected 382 items, got {len(items)}"

    # Verify PKG-BAG, PKG-COVER, PKG-BOX are completely absent
    for item in items:
        assert item.is_packaging is False
        assert not item.sku_id.startswith("PKG-")
        assert item.category.lower() != "packaging"

    # Verify packaging SKUs do not exist in sales lines
    sales = repo_container.sales.get_all_sales_lines()
    for s in sales[:5000]:  # Sample test
        assert not s.sku_id.startswith("PKG-")


def test_quarantine_negative_stock(repo_container):
    issues = repo_container.rules.get_all_data_issues()
    # Check for negative on_hand issue at MYS-02
    neg_issues = [
        iss for iss in issues
        if "MYS-02" in iss.key and "KUR-02-M" in iss.key
    ]
    assert len(neg_issues) >= 1, "Expected KUR-02-M at MYS-02 to be quarantined"
    issue = neg_issues[0]
    assert issue.table == "stock_snapshot"
    assert issue.column == "on_hand"
    assert issue.value_seen == "-4"

    # Check that the position itself is flagged untrusted
    pos = repo_container.stock.get_position("MYS-02", "KUR-02-M")
    assert pos is not None
    assert pos.is_untrusted is True


def test_quarantine_snapshot_mismatch(repo_container):
    issues = repo_container.rules.get_all_data_issues()
    # Check for mismatch at KNP-03 for SHW-02-L
    mismatch_issues = [
        iss for iss in issues
        if "KNP-03" in iss.key and "SHW-02-L" in iss.key
    ]
    assert len(mismatch_issues) >= 1, "Expected snapshot mismatch for SHW-02-L at KNP-03"
    assert "300" in mismatch_issues[0].value_seen

    pos = repo_container.stock.get_position("KNP-03", "SHW-02-L")
    assert pos is not None
    assert pos.is_untrusted is True


def test_lead_times_matrix(repo_container):
    rules = repo_container.rules

    # WH-KOL to East (Bihar - PAT-01) -> 3 days
    assert rules.get_lead_time_days("WH-KOL", "PAT-01") == 3
    # WH-KOL to North (UP - LKO-01) -> 4 days
    assert rules.get_lead_time_days("WH-KOL", "LKO-01") == 4
    # WH-KOL to South (Karnataka - BLR-01) -> 6 days
    assert rules.get_lead_time_days("WH-KOL", "BLR-01") == 6

    # Store to store: same city (LKO-01 to LKO-02) -> 2 days
    assert rules.get_lead_time_days("LKO-01", "LKO-02") == 2
    # Store to store: same zone, diff city (LKO-01 to KNP-01) -> 4 days
    assert rules.get_lead_time_days("LKO-01", "KNP-01") == 4
    # Store to store: diff zone (LKO-01 to BLR-01) -> 7 days
    assert rules.get_lead_time_days("LKO-01", "BLR-01") == 7


def test_min_display_accessories_mapping(repo_container):
    rules = repo_container.rules
    # In min_display.csv: S++ has Accessories (Safa/Mala/Stole) = 20
    safa_min = rules.get_min_display("S++", "Safa")
    mala_min = rules.get_min_display("S++", "Mala")
    stole_min = rules.get_min_display("S++", "Stole")
    assert safa_min == 20
    assert mala_min == 20
    assert stole_min == 20

    # In min_display.csv: A has Accessories = 6
    assert rules.get_min_display("A", "Safa") == 6


def test_repository_performance(repo_container):
    start = time.perf_counter()
    for _ in range(1000):
        s = repo_container.stores.get_by_id("LKO-01")
        assert s is not None
        i = repo_container.items.get_by_id("SHW-01-M")
        assert i is not None
    elapsed = time.perf_counter() - start
    avg_ms = (elapsed / 1000) * 1000
    assert avg_ms < 1.0, f"Average lookup time {avg_ms:.4f} ms exceeded 1 ms limit"


def test_missing_file_error(tmp_path):
    adapter = CSVDataSourceAdapter(tmp_path)
    with pytest.raises(FileNotFoundError):
        adapter.load_stores()
