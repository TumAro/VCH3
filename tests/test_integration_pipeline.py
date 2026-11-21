"""End-to-end integration test suite verifying the complete stock move pipeline."""
import csv
import io
from pathlib import Path
import pytest
from starlette.testclient import TestClient
import openpyxl

from src.api.app import create_app
from src.api.data_context import DataContext
from src.cli import run_pipeline
from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.moves.engine import MoveEngine
from src.services.bridge import build_engine_inputs
from src.velocity_cover.pipeline import VelocityCoverPipeline
from tests.moves.independent_validator import find_violations

DATA_DIR = Path("data/csv")


@pytest.fixture(scope="module")
def repo_and_vc():
    repo = InMemoryRepositoryContainer(DATA_DIR)
    vc = VelocityCoverPipeline(repo).run()
    return repo, vc


@pytest.fixture(scope="module")
def real_engine_inputs(repo_and_vc):
    repo, vc = repo_and_vc
    return build_engine_inputs(repo, vc)


@pytest.fixture(scope="module")
def real_engine_result(real_engine_inputs):
    return MoveEngine().run(real_engine_inputs)


@pytest.fixture(scope="module")
def test_client():
    app = create_app(data_dir=DATA_DIR)
    return TestClient(app)


def test_bridge_adapter_on_real_data(real_engine_inputs):
    """AC-1: Bridge successfully converts real dataset into valid EngineInputs."""
    inputs = real_engine_inputs
    assert len(inputs.stores) == 20
    assert len(inputs.items) == 382
    assert len(inputs.positions) > 7000

    # Quarantined items check
    mys_pos = inputs.position("MYS-02", "KUR-02-M")
    assert mys_pos.quarantined is True

    knp_pos = inputs.position("KNP-03", "SHW-02-L")
    assert knp_pos.quarantined is True

    # Velocities check
    assert len(inputs.sku_velocity) > 0
    assert len(inputs.style_velocity) > 0
    assert len(inputs.style_cover) > 0
    assert len(inputs.flagship) > 0


def test_move_engine_real_data_execution(real_engine_result):
    """AC-2: MoveEngine generates valid non-empty move lists."""
    res = real_engine_result
    assert len(res.approved_moves) > 0
    assert len(res.rejected_moves) > 0

    # Check that both Warehouse to Store (W2S) and Store to Store (S2S) moves exist
    types_found = {m.move_type for m in res.approved_moves}
    assert any(str(mt).endswith("W2S") or mt == "W2S" for mt in types_found)
    assert any(str(mt).endswith("S2S") or mt == "S2S" for mt in types_found)

    # Every move has a data-backed reason
    for m in res.approved_moves:
        assert len(m.reason.strip()) > 10
        assert str(m.qty) in m.reason


def test_zero_rule_violations_on_real_moves(real_engine_inputs, real_engine_result):
    """AC-3: Independent validator verifies 100% compliance across all 6 hard constraints."""
    violations = find_violations(real_engine_inputs, real_engine_result.approved_moves)
    assert len(violations) == 0, f"Found rule violations in real moves: {violations}"


def test_approval_threshold_compliance(real_engine_result):
    """AC-4: High-value approval flag strictly matches qty * mrp > 1,00,000."""
    for m in real_engine_result.approved_moves:
        val = m.value_mrp
        if val > 100000:
            assert m.requires_human_approval is True
        else:
            assert m.requires_human_approval is False


def test_data_context_moves_integration():
    """AC-5: DataContext retains moves, findings, and persists decision updates."""
    ctx = DataContext(DATA_DIR)
    cur = ctx.current()
    assert len(cur.moves) > 0
    assert len(cur.findings) > 0
    assert cur.summary.total_moves == len(cur.moves)

    # Test decision toggle
    assert ctx.get_decision(1) == "Waiting"
    assert ctx.set_decision(1, "Rejected") is True
    assert ctx.get_decision(1) == "Rejected"

    # Export list excludes Rejected
    approved_for_export = ctx.get_approved_moves_for_export()
    assert len(approved_for_export) == len(cur.moves) - 1

    # Safe rerun clears decision overrides
    reloaded = ctx.rerun()
    assert len(reloaded.moves) == len(cur.moves)
    assert ctx.get_decision(1) == "Waiting"


def test_api_endpoints_integration(test_client):
    """AC-6: REST API serves moves, summary, findings, and decision updates."""
    # 1. Summary
    res = test_client.get("/api/moves/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_moves"] > 0
    assert summary["total_units"] > 0

    # 2. Moves list & filters
    res = test_client.get("/api/moves")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == summary["total_moves"]
    first_move = data["items"][0]
    first_id = first_move["id"]

    # Filter by move type
    res_type = test_client.get("/api/moves?move_type=Warehouse")
    assert res_type.status_code == 200
    for it in res_type.json()["items"]:
        assert "warehouse" in it["move_type"].lower()

    # Filter by search
    res_search = test_client.get(f"/api/moves?search={first_move['sku_id']}")
    assert res_search.status_code == 200
    assert res_search.json()["count"] >= 1

    # 3. Decision update
    res_dec = test_client.post(f"/api/moves/{first_id}/decision", json={"decision": "Approved"})
    assert res_dec.status_code == 200
    assert res_dec.json()["decision"] == "Approved"

    # 4. Findings
    res_findings = test_client.get("/api/findings")
    assert res_findings.status_code == 200
    assert res_findings.json()["count"] > 0


def test_export_csv_and_xlsx_integration(test_client):
    """AC-7: Streamed CSV and Excel exports are valid and structured."""
    # CSV export
    res_csv = test_client.get("/api/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    reader = csv.reader(io.StringIO(res_csv.text))
    rows = list(reader)
    assert len(rows) > 1
    assert rows[0][0] == "Rank"
    assert rows[0][4] == "SKU"

    # Excel export
    res_xlsx = test_client.get("/api/export/xlsx")
    assert res_xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert "Moves" in wb.sheetnames
    assert "Findings" in wb.sheetnames
    assert "Rejected Moves" in wb.sheetnames


def test_cli_runner_execution(tmp_path):
    """AC-8: python -m src.cli executes and outputs moves.csv and moves.xlsx."""
    exit_code = run_pipeline(data_dir=DATA_DIR, output_dir=tmp_path)
    assert exit_code == 0
    assert (tmp_path / "moves.csv").exists()
    assert (tmp_path / "moves.xlsx").exists()
    assert (tmp_path / "moves.csv").stat().st_size > 500
    assert (tmp_path / "moves.xlsx").stat().st_size > 1000
