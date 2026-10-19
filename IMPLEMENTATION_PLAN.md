# KiranaSync 2.0 Implementation Plan

## Phase Structure & Milestones

### Phase 0: Audit & Baseline (Completed / In Progress)
- [x] Create database backup (`kirana.db.bak`).
- [x] Run baseline backend tests (21 tests passing after installing missing `number-parser`).
- [x] Audit frontend dependencies & run production build (`npm run build` succeeds).
- [x] Audit ESLint warnings/errors in `App.jsx`.
- [x] Create core specifications:
  - `PRODUCT_SPEC.md`
  - `ARCHITECTURE.md`
  - `IMPLEMENTATION_PLAN.md`
  - `EVALUATION_PROTOCOL.md`
  - `BUILD_STATUS.md`

### Phase 1: Trust Engine & Write Safety
- [ ] Implement `tempfile.NamedTemporaryFile` with collision-safe cleanup in `/api/process-audio`.
- [ ] Create `PendingCommands` table and repository service.
- [ ] Refactor voice processing into two-stage flow:
  1. `/api/process-audio` generates a structured preview draft with a unique `CommandID`.
  2. `/api/commands/<id>/confirm` commits the transaction atomically.
  3. `/api/commands/<id>/cancel` safely abandons the draft.
- [ ] Add strict server-side re-validation of inventory stock and customer balances at confirmation time.
- [ ] Implement database transactions (`BEGIN IMMEDIATE`) with idempotency guarantees.
- [ ] Add test suite verifying zero unconfirmed writes and duplicate confirmation safety.

### Phase 2: Real Voice Loop (Gnani STT + Gnani Timbre TTS)
- [ ] Extract Gnani STT logic into modular `backend/app/providers/gnani_stt.py`.
- [ ] Implement Gnani Timbre TTS adapter in `backend/app/providers/gnani_tts.py`.
- [ ] Add `/api/voice/synthesize` endpoint with streaming audio response.
- [ ] Update frontend UI to play audio feedback from committed transactions.
- [ ] Add microphone permission states, manual text command fallback, and audio mute/replay toggle.
- [ ] Add mock provider unit tests ensuring 100% test coverage without consuming Gnani API credits.

### Phase 3: Complete Retail Accounting Workflows
- [ ] Safe database migration: update `Inventory` schema with explicit `SellingPrice`, `MRP`, `PurchaseCost`, and `ReorderLevel` while preserving existing `Price` data.
- [ ] Implement `udhaar_sale` workflow (atomic stock decrement + customer debt increment).
- [ ] Implement `repayment` workflow (atomic debt reduction + repayment ledger entry + overpayment safeguard).
- [ ] Implement read-only SQL queries:
  - `balance_query`
  - `inventory_query`
  - `low_stock_query`
  - `today_summary`
  - `day_close`
- [ ] Update frontend tables and cards to reflect differentiated pricing and accounting labels.

### Phase 4: Indian Voice & Domain Adaptation
- [ ] Implement `Aliases` table and repository for shopkeeper-approved local nicknames (e.g. "chhota Maggi").
- [ ] Add conservative domain word-boosting for Gnani STT.
- [ ] Support Hindi Devanagari, code-mixed Romanized Hinglish, and mixed numeral expressions.
- [ ] Measure accuracy and latency impact across language variations.

### Phase 5: Evaluation Harness & Voice AI Lab
- [ ] Construct versioned benchmark dataset with 200+ test utterances across all intents.
- [ ] Split dataset by base scenario group to prevent data leakage.
- [ ] Build automated evaluation runner measuring Intent F1, Slot Exact Match, Unsafe Write Rate, and Latency.
- [ ] Create interactive **Voice AI Lab** screen in the frontend displaying truthful, measured metrics.
- [ ] Generate `EVALUATION_REPORT.md`.

### Phase 6: Product Polish & Differentiators
- [ ] Add spoken receipt generation with verifiable transaction details.
- [ ] Add "Why did it ask me?" transparent explanations for clarification requests.
- [ ] Build deterministic End-of-Day Hisaab summary view.
- [ ] Build safe synthetic-data Demo Mode with one-click reset.
- [ ] Fix frontend ESLint issues and optimize polling intervals.

### Phase 7: Windows Desktop Release Packaging
- [ ] Clean up `overlay.py` (remove secret/key prefix printing).
- [ ] Configure writable data directory in `%LOCALAPPDATA%\KiranaSync`.
- [ ] Test PyInstaller build and PyWebView frameless launcher.
- [ ] Verify clean execution, microphone access, and audio playback on clean Windows instance.
- [ ] Produce `build_windows.ps1` and delivery checklist.
