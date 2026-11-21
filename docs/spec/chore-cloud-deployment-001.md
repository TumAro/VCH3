# Chore: Cloud PaaS Deployment Packaging
- Status: Implemented
- Created: 2026-11-21

## 1. Spec

### Goal & context
Package the application for containerized deployment on cloud Platform-as-a-Service (PaaS) providers such as Render, Railway, or Fly.io. When code is pushed to GitHub (`main`), the cloud platform will automatically build the container image, inject the platform-assigned network port, start the FastAPI web server, and expose a public HTTPS URL for merchandisers and evaluators.

### Scope

**In Scope:**
- Multi-stage or slim `Dockerfile` optimized for Python web deployment.
- Dynamic port resolution in `run.py` supporting the platform-provided `PORT` environment variable (falling back to 8000 locally).
- `.dockerignore` file excluding cache artifacts, local virtual environments, and temporary files from the build context.
- Verification of container configuration and port resolution.
- Step-by-step deployment guide for deploying the repository (`https://github.com/TumAro/VCH3`) on Render and Railway.

**Explicitly Out of Scope:**
- Cloud infrastructure provisioning via Terraform or Kubernetes manifests.
- External database hosting (the engine remains file/memory backed with `data/csv/`).
- User authentication and multi-tenant access control.
- Paid cloud subscriptions or custom domain DNS management.

### Requirements
- **REQ-1:** Provide a standard `Dockerfile` that packages Python 3.11/3.12, installs dependencies from `requirements.txt`, copies the application codebase and initial dataset (`data/csv/`), and launches the web application.
- **REQ-2:** Support dynamic host and port configuration: `run.py` must inspect the `PORT` environment variable so platforms that dynamically assign ports (like Render and Railway) bind successfully without hardcoding.
- **REQ-3:** Provide a `.dockerignore` file to maintain small container image sizes and prevent local development artifacts (`.git`, `__pycache__`, `.pytest_cache`) from polluting the image layer.
- **REQ-4:** Provide a deployment reference document (`docs/deployment.md`) detailing the exact click-through and configuration steps to connect the GitHub repository to Render and Railway.

### Acceptance criteria
- **AC-1 (Port Resolution):** Running `run.py` with `PORT=9000` starts Uvicorn bound to port 9000 without requiring command-line argument overrides.
- **AC-2 (Image Cleanliness):** `.dockerignore` correctly excludes `.git`, `.venv`, `__pycache__`, and temporary test artifacts.
- **AC-3 (Container Readiness):** Dockerfile syntax adheres to best practices: non-root or slim image base, pinned Python version, pre-copied `requirements.txt` for layer caching, and default command pointing to `run.py`.
- **AC-4 (Documentation):** `docs/deployment.md` contains clear, tested steps to launch the service on Render or Railway from GitHub.

### Edge cases & failure modes
- **PaaS Sleep / Cold Starts:** Free tiers on Render sleep after 15 minutes of inactivity; initial cold start can take 30-50 seconds. Documented in deployment guide.
- **Port Variable Types:** Ensure `PORT` environment variable parsing safely handles non-integer edge cases or missing values gracefully defaulting to 8000.
- **Headless Cloud Execution:** Cloud environments lack a GUI/browser display; the container must run with `--no-browser` by default or handle display absence without throwing exceptions.

### Assumptions & open questions
- The application will be deployed as a public web dashboard for evaluation.
- Dataset in `data/csv/` will be packaged within the container image for standalone execution.

## 2. Plan

### Files and components to add or change
| File | Change | Reason |
|---|---|---|
| `run.py` | Change | Inspect `PORT` environment variable for dynamic PaaS port assignment (`os.environ.get("PORT", 8000)`). |
| `.dockerignore` | New | Ignore git repository metadata, virtual environments, cache dirs, and temp artifacts. |
| `Dockerfile` | New | Container definition using `python:3.11-slim`, layer caching for dependencies, copying code and data, and defining container entry point. |
| `docs/deployment.md` | New | Complete step-by-step guide for hosting on Render and Railway directly from GitHub. |

### Data models, interfaces, and contracts
- No modifications to domain models, services, or repository interfaces.

### Dependencies
- No new external Python dependencies. Docker utilizes existing `fastapi`, `uvicorn`, and `openpyxl` from `requirements.txt`.

### Risks and trade-offs
- **Ephemeral filesystem:** Edits or exported files generated inside the container remain during that container's lifetime. Since CSV exports can be downloaded directly from the browser, local container persistence is not a blocker.
- **Cold start delays:** Render free tier spins down idle instances. Mentioned in the deployment guide so judges expect a 30-45s wake-up on first load.

### Test strategy
- Test `PORT` environment variable reading logic in `run.py`.
- Validate syntax of `Dockerfile` and verify file presence in `.dockerignore`.
- Run full test suite (`python -m pytest tests -q`) to ensure zero regressions across all 153 tests.

## 3. Tasks

- [x] **T1 - Dynamic port and host resolution in `run.py`** (REQ-2). Done when: `run.py` reads `os.environ.get("PORT", 8000)` and defaults `--host 0.0.0.0` in container mode.
- [x] **T2 - Add `.dockerignore`** (REQ-3). Done when: file is present and ignores `.git`, `.venv`, `__pycache__`, `.pytest_cache`, and export outputs.
- [x] **T3 - Add `Dockerfile`** (REQ-1). Done when: valid slim Dockerfile builds cleanly with dependency layer caching and launches `run.py`.
- [x] **T4 - Author deployment guide `docs/deployment.md`** (REQ-4). Done when: document details full step-by-step setup for Render and Railway.
- [x] **T5 - Verification and test suite execution** (AC-1, AC-2, AC-3, AC-4). Done when: automated test suite passes 153/153 and port binding logic is verified.
