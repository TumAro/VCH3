# Spec memory: feature-moves-validator-001

Spec: `docs/spec/feature-moves-validator-001.md`

## 1. Summary of steps
1. Spec written; Gate 1 approved by the user.
2. Plan written, then revised with the user's decisions D-1..D-23 (from Q-1..Q-16, R-OQ-1..6, OQ-T1..5). Tasks T-1..T-15 written; Gate 2 approved.
3. T-1..T-14 implemented, one fresh agent per task, in dependency order: T-1; T-2 and T-3; T-4, T-10 and T-12; T-5 and T-7; T-6; T-8; T-9; T-11; T-13; T-14 (final verification). T-15 was not built (see section 3).
4. Delivered files:
   - `requirements-dev.txt`
   - `src/moves/`: `__init__.py`, `config.py`, `inputs.py`, `models.py`, `ledger.py`, `rules.py`, `validation.py`, `generation.py`, `explain.py`, `engine.py`
   - `tests/moves/`: `fakes.py`, `independent_validator.py`, `test_config.py`, `test_inputs_models.py`, `test_ledger.py`, `test_explain.py`, `test_independent_validator.py`, `test_rules.py`, `test_generation_core.py`, `test_validation.py`, `test_generation_w2s.py`, `test_generation_s2s.py`, `test_engine.py`, `test_determinism.py`, `test_edge_cases.py`
5. Spec header Status set to `Implemented`; T-15 marked DEFERRED (checkbox left unticked).

## 2. Decisions & rationale
All confirmed by the user (spec Section 2.10).
- D-1 Quantity fills to lead-time cover (`ceil(velocity x lead_time) - on_hand - in_transit`), capped by supply and rules: sends what the receiver needs to survive the route, not a fixed amount.
- D-2, D-5, D-13, D-14 Deficit and donor eligibility use style cover (across sizes) against one threshold `T` = longest viable route; undefined cover (`None`) is never a deficit or donor. Avoids literal per-route rules that would starve receivers.
- D-9 Own input contract in `src/moves/inputs.py`; tests build fakes. Track 1/2 adapt later, so Track 3 was not blocked on them.
- D-3 W2S supply is `WH-KOL` on-hand only (REQ-1 wording); `warehouse_inbound` ignored.
- D-4 Unfulfilled deficits in their own list, separate from `RejectedMoveLog`, which stays for rejected candidate moves (REQ-7).
- D-19 When several rules bind, the logged rule is the one allowing the smallest qty; ties go to the lower rule number. Deterministic and auditable.
- D-20 Reason renders `retains n/a cover` when warehouse cover is undefined (D-16: no velocity invented).
- D-22 S2S donor eligibility reads a running ledger, so a donor drained by earlier moves is not reused wrongly.
- D-9, D-15, D-21 Quarantined rows are excluded from candidates but still counted in R1/R2 aggregates (they physically occupy stock/capacity); a quarantined receiver with need is reported unfulfilled.
- D-7 R1 uses on-hand only; outbound never frees capacity for R2 (conservative).
- D-8 pytest is dev-only; engine is stdlib only. D-12 constants in `src/moves/config.py` until a shared config exists.

## 3. Deviations from the spec
- T-15 (real-data integration test) not delivered. Deferred by user decision on 2026-11-21: no Track 1/2 adapter builds `EngineInputs` from `data/csv/`, and Track 2 velocity/cover has no code. AC-1, AC-2 and AC-4 were therefore verified on synthetic fakes only; nothing was run on `data/csv/`.
- `requirements-dev.txt` added (`pytest==8.3.5`); pytest was installed with `pip --user`.
- The unknown-zone `KeyError` is raised in `route_days`/`detect_deficits` in `src/moves/generation.py`, not in `src/moves/inputs.py` (`EngineInputs` has no zone lookup).
- `detect_deficits` in `src/moves/generation.py` reads the private `inputs._styles` (no public accessor) and takes a style's display category from its first SKU (`_style_category`).
- In `batch_pass` (`src/moves/validation.py`), a tie between source availability and a rule logs the rule; `RuntimeError` is raised only when availability is strictly smaller than the rule limit.
- Spec Plan 2.1 corrected during the work (it wrongly said no source existed).
- `AGENTS.md` names two spec locations (`docs\spec` and `Documentation/Specs`). User ruled `docs/spec/` (and `docs/spec/memory/`) is correct; `AGENTS.md` was not edited.
- Header Status used a non-standard value, `Approved (Gate 2) - building`, during the build instead of the `AGENTS.md` values (`Approved` / `In Progress`).
- Spec text in Section 2.8 and 2.9 still says the real-data test "waits for" / is "marked skip until the adapters exist"; no skipped test file exists. Left unedited (minimal-edit instruction).

## 4. Verification evidence
Run fresh on 2026-11-21 from the repo root:
- `python3 -m pytest tests/moves -q` -> `100 passed in 0.12s`
- `python3 -m pytest -q` -> `108 passed in 3.30s` (Track 1 `tests/test_ingestion.py` contributes 8)
- `grep -n import tests/moves/independent_validator.py` shows only `__future__`, `collections`, `datetime` imports; no `src` import.
- `git status` shows only the spec file modified under `docs/spec/` (plus `requirements-dev.txt`, `src/moves/`, `tests/moves/`, untracked `__pycache__/`).
Reported earlier by the T-14 agent (not re-run by me beyond the counts above): REQ-1..7 and AC-1..6 each mapped to a proving test (AC-1 `find_violations == []` in T-13 tests, AC-2 `test_rule_flagship`, AC-3 `test_rule_approval` and `finalize` trim re-flag, AC-4 `test_batch_pass`, AC-5 `test_reason_reconciles`, AC-6 `test_rejected_log`).
Not verified: behaviour on real `data/csv/` inputs.

## 5. Failures & dead ends
- During test-first work, several tests first failed because of the implementing agents' own wrong fixtures or expectations: T-6 (2 tests), T-8 (1), T-9 (1). Fixed in the tests, not in the code.
- T-10 and T-12 ticked their checkbox with `sed -i`, which risks a race with parallel agents; all ticks were later verified intact.
- `python` is not installed, only `python3`.
- T-13 (edge cases) found no source bugs.

## 6. Known issues & follow-ups
- T-15 and real-data verification still open: needs Track 2 plus an adapter from `data/csv/` to `EngineInputs`; belongs in a later spec.
- `src/moves/generation.py` accesses private `inputs._styles` and assumes a style's category equals that of its first SKU; add a public accessor and decide on mixed-category styles.
- `InventoryLedger` in `src/moves/ledger.py` keeps a per-SKU inbound tally (`_in`) that appears unused.
- No engine-run test has a move at exactly 1,00,000 (the boundary is covered only by the `finalize` test in `tests/moves/test_engine.py`).
- `AGENTS.md` path inconsistency (`docs\spec` vs `Documentation/Specs`) remains.
- `__pycache__/` directories are untracked and not ignored for `src/` and `tests/` subfolders at the time of writing.
