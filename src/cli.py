"""Headless command-line entry point to execute the full stock move recommender."""
import argparse
from datetime import datetime
from pathlib import Path
import sys
import time

from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.moves.engine import MoveEngine
from src.services.bridge import build_engine_inputs
from src.services.export_service import ExportService
from src.velocity_cover.pipeline import VelocityCoverPipeline


def run_pipeline(data_dir: Path, output_dir: Path) -> int:
    start_time = time.perf_counter()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Manyavar Daily Stock Move Recommender...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ingesting tables from: {data_dir.resolve()}")

    # 1. Ingestion
    t0 = time.perf_counter()
    repo = InMemoryRepositoryContainer(data_dir)
    stores = repo.stores.get_all()
    items = repo.items.get_all()
    issues = repo.rules.get_all_data_issues()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ingested {len(stores)} stores, {len(items)} items. Quarantined {len(issues)} data issues in {time.perf_counter() - t0:.2f}s")

    # 2. Velocity & Cover
    t0 = time.perf_counter()
    vc_pipeline = VelocityCoverPipeline(repo)
    vc_result = vc_pipeline.run()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Calculated velocity & cover ({len(vc_result.findings)} findings surfaced) in {time.perf_counter() - t0:.2f}s")

    # 3. Bridge
    t0 = time.perf_counter()
    engine_inputs = build_engine_inputs(repo, vc_result)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bridged engine inputs ({len(engine_inputs.positions)} positions) in {time.perf_counter() - t0:.2f}s")

    # 4. Move Generation & Validation
    t0 = time.perf_counter()
    move_engine = MoveEngine()
    engine_result = move_engine.run(engine_inputs)
    approved = engine_result.approved_moves
    rejected = engine_result.rejected_moves
    unfulfilled = engine_result.unfulfilled_deficits
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Move engine complete: {len(approved)} approved, {len(rejected)} rejected, {len(unfulfilled)} unfulfilled in {time.perf_counter() - t0:.2f}s")

    # 5. Export
    t0 = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    ExportService.write_files_to_dir(
        output_dir=output_dir,
        moves=approved,
        findings=vc_result.findings,
        rejected=rejected,
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Exported moves.csv and moves.xlsx to {output_dir.resolve()} in {time.perf_counter() - t0:.2f}s")

    total_time = time.perf_counter() - start_time
    total_units = sum(m.qty for m in approved)
    total_mrp = sum(m.value_mrp for m in approved)
    req_approval = sum(1 for m in approved if m.requires_human_approval)

    print("=" * 60)
    print(f"PIPELINE RUN SUMMARY (Completed in {total_time:.2f} seconds):")
    print(f"  - Total Approved Moves:        {len(approved)}")
    print(f"  - Total Units to Move:         {total_units:,}")
    print(f"  - Total Move Value (MRP):      Rs {total_mrp:,}")
    print(f"  - Moves Requiring Sign-off:    {req_approval}")
    print(f"  - Quarantined Data Anomalies:  {len(issues)}")
    print(f"  - Artifacts Written:           {output_dir / 'moves.csv'}, {output_dir / 'moves.xlsx'}")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Daily Stock Move Recommender CLI")
    parser.add_argument("--data-dir", type=Path, default=Path("data/csv"), help="Path to raw CSV data directory")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Directory to save moves.csv and moves.xlsx")
    args = parser.parse_args()

    exit_code = run_pipeline(data_dir=args.data_dir, output_dir=args.output_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
