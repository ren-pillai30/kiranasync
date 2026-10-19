# KiranaSync Developer & Contributor Guide

A practical handbook for setting up, running, understanding, testing, and extending the multilingual voice-enabled inventory application.

**Audience**: A developer receiving the repository for the first time. Commands below use Windows PowerShell unless stated otherwise.

---

## 1. Project Overview

KiranaSync is a local desktop application designed for Indian kirana (small retail) shops. A React interface provides a live inventory dashboard, customer credit balances, a transaction ledger, voice-command controls, and review dialogs. A Flask backend provides the API and connects the UI to SQLite and external speech and language services. PyWebView presents the local web application in an always-on-top desktop window.

- **Frontend**: React 19, Vite 8, Tailwind CSS, Framer Motion, and RecordRTC.
- **Backend**: Python, Flask, Flask-CORS, SQLite, requests, and the application modules under `backend/app`.
- **Speech**: Gnani STT (Prisma) and Gnani Timbre TTS.
- **Command Understanding**: Gemini structured output selects a transcript and extracts an action, entity, and amount.
- **Product Lookup**: DuckDuckGo search results are filtered for product relevance and used to present unverified MRP/price suggestions.

Voice transactions are previewed for the user before the database is changed. New products and ambiguous inventory variants have their own confirmation/selection flows.

---

## 2. Repository Map

| Path | Responsibility |
| :--- | :--- |
| [`README.md`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/README.md) | Feature notes, supported voice languages, external API requirements, and user-facing behavior. |
| [`overlay.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/overlay.py) | Starts Flask in a background thread, opens the PyWebView overlay, and registers keyboard shortcuts. |
| [`backend/app/main.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/main.py) | Flask app, HTTP endpoints, Gnani STT/TTS calls, Gemini orchestration, and request validation. |
| [`backend/app/intent_parser.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/intent_parser.py) | Intent application, fuzzy matching, SQLite transactions, product/MRP lookup, and similar-name suggestions. |
| [`backend/app/gemini_understanding.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/gemini_understanding.py) | Gemini prompt, API retries, structured-output parsing, and interpretation validation. |
| [`backend/app/db_setup.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/db_setup.py) | Creates database tables and attempts to insert starter/demo inventory and a customer. |
| [`backend/app/services/`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/services/) | Domain services: `command_service.py` (drafts), `transaction_service.py` (atomic mutations), `alias_service.py` (nicknames), `query_service.py` (analytics). |
| [`backend/app/evaluation/`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/evaluation/) | Evaluation suite: `dataset.json`, `runner.py`, `production_evaluator.py`, `benchmark_cli.py`. |
| [`backend/tests/`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/tests/) | Python unit and Flask API tests. External service calls are mocked in tests. |
| [`frontend/src/App.jsx`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/App.jsx) | Main React UI: language dictionaries, STT selector, dashboard, review modals, TTS playback, and product workflow. |
| [`frontend/src/main.jsx`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/main.jsx) | React bootstrap and stylesheet entry. |
| [`frontend/src/App.css`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/App.css) & [`frontend/src/index.css`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/index.css) | Application and global styling. |
| [`frontend/package.json`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/package.json) | Frontend scripts and dependency manifest. |
| [`backend/requirements.txt`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/requirements.txt) | Python dependencies. |
| [`.env.example`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/.env.example) | Names/defaults for environment variables; copy to a private root `.env` and fill in keys. |
| [`catalog.json`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/catalog.json) | Small sample product catalog used by parser-related features. |
| [`kirana.db`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/kirana.db) | SQLite database. It contains mutable inventory, customers, and transaction history; treat it as private data. |

---

## 3. Prerequisites

- **Windows 10/11** (the commands in this guide use PowerShell).
- **Python 3.12** is a known working development version for this project. Use a compatible Python version supported by all listed packages.
- **Node.js and npm** compatible with the Vite 8 toolchain in `frontend/package.json`.
- **WebView2 Runtime** for the Windows PyWebView desktop experience.
- **Gnani API key** for speech-to-text and text-to-speech; **Gemini API key** for command interpretation.

> [!NOTE]
> An internet connection is required for API-backed STT, TTS, Gemini interpretation, and DuckDuckGo product lookup. The dashboard and local database are local services, but voice features are not fully offline.

---

## 4. Clone and Install

```powershell
git clone https://github.com/ren-pillai30/kiranasync.git
Set-Location kiranasync
```

Create a virtual environment at the repository root, activate it, and install backend requirements:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

If PowerShell prevents script activation, either permit activation for the current PowerShell process (`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`) or invoke the virtualenv interpreter explicitly:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests
```

Install frontend dependencies from the lockfile:

```powershell
Set-Location frontend
npm ci
Set-Location ..
```

---

## 5. API Keys and Environment Configuration

Copy the example environment file to the repository-root `.env` (if it does not already exist), then edit it locally:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Configure your `.env` with valid keys:

```env
GNANI_API_KEY=your_gnani_api_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
GNANI_TTS_MODEL=timbre-v3.0
GNANI_TTS_VOICE=Shivani
```

- `GNANI_API_KEY` is used for Gnani STT and Timbre TTS.
- `GEMINI_API_KEY` is required for command interpretation; `GEMINI_MODEL` optionally selects the Gemini model (default: `gemini-3.5-flash-lite`).
- `GNANI_TTS_MODEL` and `GNANI_TTS_VOICE` are optional overrides; defaults are `timbre-v3.0` and `Shivani`.

> [!WARNING]
> Never put real API keys in source code, screenshots, tickets, chat, commits, or the example file. `.env` is ignored by Git. Do not commit secrets.

---

## 6. Run the Application

### 6.1 Desktop Overlay (Normal Usage)

The desktop app loads the compiled frontend from `frontend/dist`. Build it first whenever frontend source changes:

```powershell
Set-Location frontend
npm run build
Set-Location ..
python overlay.py
```

`overlay.py` starts the Flask API on `127.0.0.1:5000` and opens an always-on-top PyWebView window. 
- **Ctrl+Shift+V**: Activate voice input
- **Ctrl+Shift+D**: Toggle dashboard

Close the overlay window to stop its background Flask thread.

### 6.2 Separate Development Servers (Hot Reload)

Use two PowerShell terminals from the repository root.

**Terminal A (Flask API Backend)**:
```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.app.main
```

**Terminal B (Vite Frontend with Hot Reload)**:
```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Open the local URL printed by Vite. The frontend calls the API at `http://127.0.0.1:5000`. Flask CORS is enabled. In this mode Vite serves the live frontend; Flask's `/` route serves the last compiled frontend build in `frontend/dist`.

---

## 7. Architecture and Request Flows

### 7.1 Voice Command Flow

```
[User Speech] 
      │ (RecordRTC WAV)
      ▼
[POST /api/process-audio] ──► [Gnani STT (Prisma)] 
                                      │
                                (Transcripts)
                                      ▼
                             [Gemini Structured NLU]
                                      │
                            (Action, Entity, Qty)
                                      ▼
                        [Deterministic Domain Validation]
                                      │
                                (Draft Created)
                                      ▼
                         [Frontend Review Modal]
                                      │ (User Confirmation)
                                      ▼
                       [POST /api/commands/:id/confirm]
                                      │
                        [Atomic DB & Ledger Commit]
                                      │
                                      ▼
                       [POST /api/voice/synthesize]
                                      │
                          [Spoken Receipt Playback]
```

1. React captures audio with RecordRTC and sends the WAV file plus a `language_code` to `POST /api/process-audio`.
2. For a selected STT language, Flask sends one request to Gnani. In auto mode it requests transcripts in all 10 configured STT language codes concurrently.
3. Gemini receives the transcript candidates, the current inventory names, and customer names. It returns a structured action, entity, quantity, and transcript index.
4. The backend validates the interpretation and creates a preview draft. A sale/restock/credit is **never** committed at this stage.
5. The selected transcript's language code is retained for the TTS read-back. The user can edit the draft, replay it, confirm it, or cancel it.
6. On confirmation, the backend revalidates stock/debt, atomically commits the inventory/balance change and transaction log, then returns success.

### 7.2 Language Responsibilities

- STT/TTS language selection and dashboard display language are separate controls.
- **Supported STT Options**: `bn-IN`, `en-IN`, `gu-IN`, `hi-IN`, `kn-IN`, `ml-IN`, `mr-IN`, `pa-IN`, `ta-IN`, `te-IN`. English STT selection is labeled English/Hinglish.
- **Auto STT**: An application strategy, not a single Gnani auto-detect call: the backend submits up to 10 transcriptions and Gemini compares them.
- **Dashboard Locales**: `bn`, `en`, `gu`, `hi`, `kn`, `ml`, `mr`, `pa`, `ta`, `te`. Locale dictionaries fall back to English for unlocalized strings.
- **TTS Generation**: For auto-detected voice transactions, TTS uses the selected transcript's detected STT language. Manual-entry speech uses the specific voice-language selection, or English when voice language remains auto.

### 7.3 New Product and Product Search Flow

When an unknown product is restocked, the backend looks for relevant product results and extracts possible price/MRP options. When there are no relevant results, a secondary lookup may return a few similar-looking product names. These are candidates only: a user must deliberately select a name and search again. Online price/MRP values are not trusted until checked against the package/source.

The product confirmation window lets the user review/edit the product name, set quantities per selected MRP, add an MRP manually, check sources, and confirm. The optional phonetic pronunciation changes spoken text only; it must not alter the product name used for lookup or saved to inventory.

---

## 8. Important Backend API Routes

| Method / Route | Purpose |
| :--- | :--- |
| `GET /` | Serves `frontend/dist/index.html`. |
| `GET /api/dashboard` | Returns inventory and customer credit data. |
| `GET /api/ledger` | Returns transaction history. |
| `GET /api/analytics/hisaab` | Returns today's sales, cash collections, repayments, and outstanding udhaar. |
| `GET /api/analytics/low-stock` | Lists products with stock under the reorder threshold ($\le 5$). |
| `GET /api/query/balance?customer=...` | Retrieves outstanding udhaar balance for a specific customer. |
| `GET /api/aliases` | Lists all approved spoken aliases. |
| `POST /api/aliases` | Adds a verified spoken nickname mapped to an existing product or customer. |
| `DELETE /api/aliases/:id` | Deletes an approved alias mapping. |
| `GET /api/evaluation/benchmark` | Returns the empirical benchmark scorecard and stage latency breakdown. |
| `POST /api/process-audio` | Transcribes and interprets recorded audio; creates a pending draft. |
| `POST /api/voice/synthesize` | Returns WAV audio for server-verified text using Gnani Timbre TTS. |
| `POST /api/product-lookup` | Looks up product/MRP sources and similar-name candidates online. |
| `POST /api/commands/:id/confirm` | Atomically commits a reviewed draft command (`sale`, `restock`, `udhaar_sale`, `repayment`). |
| `POST /api/commands/:id/cancel` | Explicitly cancels a pending draft without mutating data. |
| `POST /api/inventory/confirm-command` | Applies a reviewed sell/restock command for a selected inventory variant. |
| `POST /api/inventory/confirm-restock` | Creates selected new product/MRP variants and corresponding transaction rows. |
| `POST /api/inventory/add`; `/api/credit/add` | Direct add routes used by API clients; UI additions use the review flow. |
| `POST /api/inventory/edit`; `/api/credit/edit` | Renames inventory items and customers. |

---

## 9. Database, Paths, and Data Safety

SQLite tables are `Inventory`, `CustomerCredit`, `Transactions`, `PendingCommands`, and `Aliases`. 
- `Transactions` records include a timestamp, originating command/action, type, entity, quantity, and total amount.
- `PendingCommands` tracks drafts through `PENDING`, `COMMITTED`, or `CANCELLED` states.

Database paths depend on the environment: in desktop packaged mode, the app uses `%LOCALAPPDATA%\KiranaSync\kirana.db`; in local development, it defaults to `./kirana.db`.

> [!CAUTION]
> The checked-in database may hold mutable demo or test data: back it up before write-flow testing, and never overwrite or reset it without explicit authorization.

```powershell
Copy-Item kirana.db "$env:TEMP\kirana-backup-$(Get-Date -Format yyyyMMdd-HHmmss).db"
```

The application sends audio to Gnani for transcription, transcript candidates and catalog names to Gemini for interpretation, and product queries to the search provider. Use synthetic data for demos/tests. Review current service terms and privacy policies before using real customer information or recorded conversations.

---

## 10. How to Make Changes

1. Start from a clean, up-to-date branch. Use a feature branch for work intended for review.
2. Read the relevant frontend component, API route, parser/helper, and existing tests before editing. Follow existing names, response shapes, and validation conventions.
3. If changing behavior, update the owning implementation and every related interface: caller, API schema, localization, docs, and tests.
4. **Preserve confirmation-before-write behavior** for voice transactions and new-product flows. Validate inputs server-side even when the UI also validates them.
5. Use parameterized SQL queries for user-controlled values. Keep network/API errors explicit; do not convert failures into successful-looking results.
6. For translations, update the correct display dictionary; for speech, update voice-language speech templates separately. Do not couple TTS to the dashboard locale.
7. For online suggestions, preserve provenance and show that suggestions are unverified. Never silently overwrite a user-entered product name or price.
8. Add a regression test for the behavior and run the smallest relevant test set first, then broader checks when appropriate.
9. Review `git status` and diff. Do not stage `.env`, private database changes, build outputs, `node_modules`, or unrelated local files.

### Where Common Changes Belong

| Change | Likely Files |
| :--- | :--- |
| Dashboard UI, language selector, modal, or TTS player | [`frontend/src/App.jsx`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/App.jsx); styles in [`frontend/src/App.css`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/App.css) or [`frontend/src/index.css`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/src/index.css) |
| STT/TTS/API route or response behavior | [`backend/app/main.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/main.py), [`backend/app/providers/`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/providers/) and [`backend/tests/test_transaction_ledger_api.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/tests/test_transaction_ledger_api.py) |
| Draft lifecycle & atomic commits | [`backend/app/services/command_service.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/services/command_service.py), [`backend/app/services/transaction_service.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/services/transaction_service.py), [`backend/tests/test_trust_safety.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/tests/test_trust_safety.py) |
| Spoken nicknames & aliases | [`backend/app/services/alias_service.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/services/alias_service.py) and [`backend/tests/test_alias_integration.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/tests/test_alias_integration.py) |
| Intent validation, fuzzy matching, DB writes, product suggestions | [`backend/app/intent_parser.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/intent_parser.py) and [`backend/tests/test_intent_parser_interpretation.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/tests/test_intent_parser_interpretation.py) |
| Gemini prompt, schema, candidate/quantity interpretation | [`backend/app/gemini_understanding.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/gemini_understanding.py) and [`backend/tests/test_gemini_understanding.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/tests/test_gemini_understanding.py) |
| Tables or starter data | [`backend/app/db_setup.py`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/app/db_setup.py); preserve and back up existing DB data |
| Runtime configuration or dependencies | [`.env.example`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/.env.example) and/or [`backend/requirements.txt`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/backend/requirements.txt) or [`frontend/package.json`](file:///c:/Users/nitta/Downloads/kiranasync/kiranasync-main/frontend/package.json); never add real secrets |

---

## 11. Test, Lint, and Build

### 11.1 Backend Tests

Run all unit and integration tests:

```powershell
python -m unittest discover -s backend/tests -v
```

Run one test module while iterating:
```powershell
python -m unittest backend.tests.test_trust_safety -v
```

Run the reproducible evaluation benchmark suite:
```powershell
python -m backend.app.evaluation.benchmark_cli
```

> [!TIP]
> Tests use temporary SQLite databases and deterministic mocks for external API calls, so routine tests run 100% offline and do not consume live Gnani or Gemini API credits.

### 11.2 Frontend Production Build

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

The build writes `frontend/dist`, which the Flask app and desktop wrapper serve. Rebuild before validating the packaged desktop experience.

### 11.3 Frontend Lint

```powershell
Set-Location frontend
npm run lint
Set-Location ..
```

Address issues introduced by your change. If lint reports an existing unrelated issue, note it separately rather than broadening a focused feature change.

### 11.4 Diff Hygiene

```powershell
git diff --check
git status --short
```

---

## 12. Troubleshooting

| Symptom | Checks |
| :--- | :--- |
| Desktop app is blank or source changes are missing | Run `npm run build` in `frontend`, confirm `frontend/dist` exists, then restart `overlay.py`. |
| Frontend cannot reach API | Check Flask is running at `127.0.0.1:5000`; ensure no other process occupies port 5000. |
| Missing Gnani configuration | Check root `.env` has `GNANI_API_KEY` and restart the backend. Never paste the key into logs/issues. |
| Gemini interpretation fails | Check `GEMINI_API_KEY`, internet connectivity, service status, and Flask output. Verify mocked tests before testing with real requests. |
| Microphone is unavailable | Grant Windows/WebView microphone permissions and check the selected audio input device. |
| Changes do not appear in overlay | The desktop loads the built frontend, not Vite dev source. Rebuild (`npm run build`) and restart. |
| Wrong or uncertain MRP/brand suggestion | Treat search data as unverified. Verify packaging and explicitly choose/edit the correct product. |
| Unexpected database file or data | Stop the app and check the current working directory. Back up before changing DB setup or path handling. |

---

## 13. Git Workflow and Pull Request Checklist

```powershell
git switch -c feature/short-description
# make changes and run relevant checks
git status --short
git diff --check
git add <specific-files>
git commit -m "Describe the change"
```

- [ ] Do not stage `.env`, API keys, customer details, local recordings, or unintended `kirana.db` changes.
- [ ] Include tests for API validation, state transitions, and database writes when relevant.
- [ ] Mention commands run and any skipped checks in the pull request.
- [ ] Keep commits focused; do not include generated `frontend/dist` or `node_modules` unless project policy changes.

---

## 14. Quick Reference

| Task | Command |
| :--- | :--- |
| Install Python dependencies | `python -m pip install -r backend\requirements.txt` |
| Install frontend dependencies | `Set-Location frontend; npm ci; Set-Location ..` |
| Run desktop app | Build frontend, then run `python overlay.py` from repository root |
| Run Flask for development | `python -m backend.app.main` |
| Run Vite for development | `npm run dev -- --host 127.0.0.1` in `frontend` |
| Run backend tests | `python -m unittest discover -s backend/tests -v` |
| Run benchmark CLI | `python -m backend.app.evaluation.benchmark_cli` |
| Build frontend | `npm run build` in `frontend` |
| Lint frontend | `npm run lint` in `frontend` |
