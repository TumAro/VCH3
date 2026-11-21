# Spec Memory: Pipeline Bridge & Move Integration
- Spec: `docs/spec/feature-pipeline-bridge-001.md`
- Implemented: 2026-11-21

## 1. Summary of steps taken
- Implemented `build_engine_inputs` in `src/services/bridge.py` mapping Track 1 (`InMemoryRepositoryContainer`) and Track 2 (`VelocityCoverResult`) domain structures into Track 3's `EngineInputs`.
- Built `ExportService` in `src/services/export_service.py` to produce `moves.csv` and styled multi-tab `moves.xlsx` (*Moves*, *Findings*, *Rejected Moves*) using `openpyxl`.
- Extended `DataContext` in `src/api/data_context.py` to run `VelocityCoverPipeline` and `MoveEngine`, cache move results, findings, and summaries, and support in-memory decision toggles.
- Enhanced `src/api/app.py` adding `/api/moves`, `/api/moves/{id}/decision`, `/api/findings`, `/api/moves/summary`, `/api/export/csv`, and `/api/export/xlsx`.
- Created `src/cli.py` headless runner.
- Implemented and verified the complete 8-part integration test suite in `tests/test_integration_pipeline.py`.
- Connected real move data, interactive filtering, and Approve/Reject toggles in `src/web/js/moves.js` and `src/web/index.html`.

## 2. Decisions & rationale
- **Defensive DataContext loading**: `DataContext._load()` checks for container capabilities before triggering Track 2 and Track 3 pipelines, ensuring unit tests using minimalist fake containers (e.g. testing only revenue or notifications) continue to pass without mocks for all tables.
- **Export exclusion**: Moves marked as `Rejected` by the user in the UI are omitted from the primary approved *Moves* export sheet/CSV while remaining recorded in the session.
- **Deterministic reason strings**: Every approved move includes a traceable, template-based explanation referencing exact store cover, units, and velocity.

## 3. Deviations from the spec
- None. All 10 requirements and 8 acceptance criteria were met.

## 4. Verification evidence
- Integration tests: `python -m pytest tests/test_integration_pipeline.py -v` -> 8 passed in 16.96s.
- Full test suite: `python -m pytest tests -q` -> 153 passed in 49.79s.
- Real data CLI execution: `python -m src.cli --data-dir data/csv --output-dir .`
  - Total Approved Moves: 54
  - Total Units: 133
  - Total Move Value (MRP): Rs 858,467
  - Moves Requiring Sign-off: 1
  - Execution time: 2.94 seconds.
- Independent Validator verification: 0 rule violations found across all 54 approved moves on real data.

## 5. Failures & dead ends
- Initial assertion in `test_move_engine_real_data_execution` checked for `"warehouse"` in `move_type.value`; `MoveType` enum uses values `"W2S"` and `"S2S"`. Updated assertion to test for `"W2S"` and `"S2S"`.
- Unit tests in `test_data_context.py` used a fake container without `items` attribute; added defensive capability check in `DataContext._load()` to handle minimalist fake containers.

## 6. Known issues & follow-ups
- None. The end-to-end recommender pipeline is completely operational.
