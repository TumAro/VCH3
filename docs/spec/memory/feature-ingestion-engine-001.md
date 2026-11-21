# Spec Memory: Track 1 Data Ingestion & Repository Layer
- Spec: `docs/spec/feature-ingestion-engine-001.md`
- Implemented: 2026-11-21

## 1. Summary of steps taken
- Implemented core domain entities in `src/domain/models.py` as typed, immutable dataclasses.
- Implemented abstract repository interfaces in `src/domain/repositories.py` upholding the Repository Design Pattern and SOLID principles.
- Built `CSVDataSourceAdapter` in `src/infrastructure/csv_adapter.py` parsing the 10 tabular CSV datasets from `data/csv/`. Handled strict string casting for IDs, ISO date parsing, automated packaging SKU filtering (`is_packaging = 1`), and quarantined untrusted records into `DataIssueLog`.
- Built `InMemoryRepositoryContainer` and specialized repositories (`StoreRepository`, `ItemRepository`, `StockRepository`, `SalesRepository`, `RulesRepository`) in `src/infrastructure/in_memory_repository.py` with indexed lookups and a callable `sync()` method.
- Authored test suite in `tests/test_ingestion.py` covering all acceptance criteria (AC-1 to AC-4, edge cases, error handling, performance).

## 2. Decisions & rationale
- **Standard Library only**: Used `csv.DictReader` and standard Python types rather than external dependencies for the ingestion layer. Ingestion of 260k sales lines and 61k weekly rows completes in under 2.5 seconds with zero build fragility.
- **Packaging exclusion at source**: Stripped packaging SKUs (`PKG-BAG`, `PKG-COVER`, `PKG-BOX`) during the CSV read stage to ensure downstream velocity, cover, and constraint engines never receive non-garment rows.
- **Accessories mapping**: Mapped individual categories `Safa`, `Mala`, and `Stole` to `Accessories (Safa/Mala/Stole)` within `RulesRepository.get_min_display()`.
- **Dynamic route matrix**: Derived transit days in `RulesRepository.get_lead_time_days()` from location zones and cities to avoid hardcoding static O(N^2) pairs.

## 3. Deviations from the spec
- None. All requirements REQ-1 through REQ-6 and acceptance criteria AC-1 through AC-4 were satisfied without changes to the spec.

## 4. Verification evidence
- Test execution command: `python -m pytest tests/test_ingestion.py -v`
- Result: 8 passed in 2.51s
  - `test_store_loading`: PASSED (20 stores, string IDs, BLR-05 is_new_store == True)
  - `test_packaging_exclusion`: PASSED (382 items, 0 packaging in items or sales)
  - `test_quarantine_negative_stock`: PASSED (KUR-02-M at MYS-02 flagged untrusted in DataIssueLog)
  - `test_quarantine_snapshot_mismatch`: PASSED (SHW-02-L at KNP-03 flagged untrusted in DataIssueLog)
  - `test_lead_times_matrix`: PASSED (WH routes 3/4/6 days, store routes 2/4/7 days)
  - `test_min_display_accessories_mapping`: PASSED (S++ = 20, A = 6)
  - `test_repository_performance`: PASSED (average lookup time < 0.001 ms)
  - `test_missing_file_error`: PASSED (FileNotFoundError raised on invalid directory)

## 5. Failures & dead ends
- Initial assertion in `test_min_display_accessories_mapping` expected 45 units for S++ Accessories; inspect of `min_display.csv` confirmed the source data specifies 20 units. Fixed test assertion to match source data.
- Windows environment required `python -m pytest` rather than bare `pytest` executable.

## 6. Known issues & follow-ups
- None. Track 1 is fully functional and ready for Tracks 2, 3, and 4 consumption.
