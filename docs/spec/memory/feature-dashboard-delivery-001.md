# Spec Memory: Track 4: Web Dashboard, API & Export
- Spec: `docs/spec/feature-dashboard-delivery-001.md`
- Implemented: 2026-11-21

## 1. Summary of steps taken
- Implemented domain models in `src/domain/overview.py` and `src/domain/notifications.py` representing network hierarchical metrics and data issue alerts.
- Built `NetworkOverviewService` in `src/services/network_overview_service.py` aggregating state/city/store revenue (excluding packaging), capacity utilization, zero-stock counts, and 24-month revenue time-series.
- Built `NotificationService` in `src/services/notification_service.py` to collect data issue alerts and pending sign-off alerts with deterministic SHA-1 content IDs.
- Implemented thread-safe `DataContext` caching with `POST /api/sync` re-run capabilities in `src/api/data_context.py`.
- Developed FastAPI backend in `src/api/app.py` serving static assets and REST endpoints (`/api/network`, `/api/revenue/monthly`, `/api/notifications`, `/api/sync`).
- Built modular front-end UI (`src/web/index.html`, `src/web/styles.css`, `src/web/js/`) supporting:
  - Sticky navigation bar with Overview and Moves tabs.
  - Light/Dark mode with automatic system detection and persistent toggle.
  - Profile menu with personalized hero greeting dialog ("Namaskar {name}").
  - Notification popover listing quarantined ingestion records.
  - Hand-drawn SVG line chart of monthly revenue with interactive state toggles.
  - Expandable state -> city -> store drill-down table.
  - Moves table filter bar, summary count, and empty-state placeholders.
- Integrated end-to-end move review, in-memory approval toggles, and Excel/CSV streaming as planned in Part B through `docs/spec/feature-pipeline-bridge-001.md`.

## 2. Decisions & rationale
- **Native ES Modules**: Split front-end code into modular ES scripts (`api.js`, `dom.js`, `storage.js`, `theme.js`, `tabs.js`, `profile.js`, `notifications.js`, `overview.js`, `moves.js`, `main.js`) avoiding heavy bundlers while maintaining strict single-responsibility principles.
- **Deterministic Notification IDs**: Computed SHA-1 hashes over notification content (`table|key|column|rule|value`) so seen notifications persist across pipeline re-runs without duplicate badge alerts.
- **Strict Revenue Definition**: Excluded packaging SKUs (`is_packaging = 1`) across all bill line calculations ensuring exact consistency with physical garment revenues.
- **Pure CSS / Native SVG**: Implemented charts and UI widgets without third-party CDN scripts, guaranteeing offline execution and fast rendering under 2 seconds.

## 3. Deviations from the spec
- Part B move generation integration and Excel export implementation was formalized and completed via `docs/spec/feature-pipeline-bridge-001.md` once Track 3 contracts were finalized.

## 4. Verification evidence
- Overview and real-data unit tests:
  - `tests/test_network_overview_service.py`: 16 passed
  - `tests/test_overview_real_data.py`: 4 passed (exact revenue and store count matches)
  - `tests/test_notification_service.py`: 4 passed
  - `tests/test_api_overview.py`: 6 passed
  - `tests/test_data_context.py`: 3 passed
- UI manual and browser validation: Verified dark mode toggle, notification popover, hero greeting persistence, and expandable drill-down table.
- Complete test suite: `python -m pytest tests -q` -> 153 passed.

## 5. Failures & dead ends
- Legacy unit tests in `tests/test_data_context.py` supplied a minimalist fake container without `items` attribute; solved by adding capability checks before triggering the full move recommender bridge.

## 6. Known issues & follow-ups
- None.
