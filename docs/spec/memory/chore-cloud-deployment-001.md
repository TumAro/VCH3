# Spec Memory: Cloud PaaS Deployment Packaging
- Spec: `docs/spec/chore-cloud-deployment-001.md`
- Implemented: 2026-11-21

## 1. Summary of steps taken
- Updated `run.py` to inspect `PORT` and `HOST` environment variables dynamically with fallback to 8000 and 127.0.0.1.
- Created `.dockerignore` ignoring repository metadata (`.git`), virtual environments (`.venv`), compiler caches (`__pycache__`), and export outputs.
- Created `Dockerfile` based on `python:3.11-slim`, utilizing layer caching for `requirements.txt`, bundling `data/csv/` and `src/`, and exposing port 8000 with headless `run.py` entry point.
- Authored step-by-step deployment guide in `docs/deployment.md` covering Render, Railway, and Fly.io setup directly from GitHub.
- Verified dynamic port parsing and executed end-to-end integration tests.

## 2. Decisions & rationale
- **Dynamic Port Injection**: Platforms like Render and Railway dynamically inject a `$PORT` environment variable at runtime. Supporting `int(os.environ.get("PORT", 8000))` in `run.py` avoids hardcoding or separate startup scripts.
- **Layer Caching**: Copying and installing `requirements.txt` prior to copying the full source tree minimizes container build times on subsequent code updates.
- **Single-Entry Container Command**: Running `python run.py --host 0.0.0.0 --no-browser` provides uniform startup behavior across local and container environments.

## 3. Deviations from the spec
- None.

## 4. Verification evidence
- Port parsing verification: `$env:PORT="9999"; python run.py --help` outputted `Server port (default: 9999)`.
- Integration tests: `python -m pytest tests/test_integration_pipeline.py -q` -> 8 passed in 18.38s.

## 5. Failures & dead ends
- None.

## 6. Known issues & follow-ups
- Render free tier instances sleep after 15 minutes of inactivity; first request after idle can experience a 30-45 second wake-up latency.
