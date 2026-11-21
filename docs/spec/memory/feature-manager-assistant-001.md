# Spec Memory: Manager Assistant and Evidence-Retrieval Chat
- Spec: `docs/spec/feature-manager-assistant-001.md`
- Implemented: 2026-11-21

## 1. Summary of steps taken
- Added typed assistant evidence, citation, and daily-task models in `src/domain/assistant.py`.
- Added deterministic evidence retrieval and capped Store Coach-style daily tasks in `src/services/assistant_evidence_service.py`.
- Added local project-document retrieval in `src/services/assistant_rag_service.py`.
- Added a Sarvam AI HTTP provider adapter and evidence-grounded orchestration service.
- Added live assistant status, chat, and daily-task API endpoints.
- Added the assistant panel and daily-task action to the existing dashboard.
- Loaded the `key` entry from `secrets.env` server-side only and added it to `.gitignore`.

## 2. Decisions & rationale
- Used structured application results plus approved project-document excerpts for the MVP RAG layer instead of a vector database.
- Kept all numerical calculations and rankings in deterministic services; the model only paraphrases verified evidence.
- Used the official Sarvam chat-completions endpoint and model, with Bearer and API-subscription-key headers.
- Added reasoning-content parsing and final-answer extraction for the live Sarvam response shape.
- Kept verified factual fallback output when provider configuration or provider requests fail.

## 3. Deviations from the spec
- The initially documented `reasoning_effort: none` value was rejected by the live API. The provider now omits reasoning effort and parses reasoning/final content safely.
- The live API required a compatible `websockets` package for Uvicorn startup. `websockets==17.4` was pinned.

## 4. Verification evidence
- `python3 -m pytest tests/test_assistant_contracts.py tests/test_assistant_evidence_service.py tests/test_assistant_provider_rag.py tests/test_assistant_api.py -q`
- Result: 9 passed.
- `python3 -m compileall -q src tests`
- Result: no compile errors.
- Live minimal Sarvam call: succeeded and returned valid text.
- Live `POST /api/assistant/chat`: returned status `ok`, provider status `ready`, and a cited network summary.
- Browser Playwright check:
  - Assistant panel visible and provider status displayed.
  - Chat query returned a concise summary with network revenue and store count.
  - Daily-task button returned five ranked store tasks.
  - Full-page screenshot saved to `/tmp/vch-dashboard-final.png`.

## 5. Failures & dead ends
- The original key was rejected with Sarvam `invalid_api_key_error`; the replacement key passed authentication.
- An initial live payload using `reasoning_effort: none` returned HTTP 400; the provider now uses Sarvam's default reasoning behavior.
- The server briefly returned `message.content == null` while reasoning text was present; parsing and final-summary extraction fixed this.
- Uvicorn initially conflicted with an older system `websockets` package; upgrading and pinning the package resolved startup.

## 6. Known issues & follow-ups
- The live Sarvam response can still vary in wording and should remain isolated from factual calculations.
- Store Coach conversion, staffing, basket, and repeat-customer coaching remain out of scope until those sources are ingested.
