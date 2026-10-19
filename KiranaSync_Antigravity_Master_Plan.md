# ANTIGRAVITY MASTER BUILD BRIEF
# KiranaSync 2.0 — a trustworthy voice-first operating assistant for Indian kirana shops

## How to use this brief

Treat this as the product north star and staged implementation contract. Do not attempt a blind, one-shot rewrite. First inspect the actual repository, record a baseline, and create a phase plan. Then implement in small, testable increments, preserving useful existing behavior. After each phase, run the relevant checks, fix regressions, and update `BUILD_STATUS.md` with what changed, what passed, what remains, and the next concrete step.

The target is not merely a pretty demo. It is a working, defensible product with a reliable voice loop, safe financial/inventory mutations, useful Indian-language support, reproducible evaluation, polished UX, clear technical documentation, and finally a Windows executable.

---

# 1. Product thesis

## Name
**KiranaSync 2.0 — the voice-first operating assistant for India's neighbourhood shops.**

Possible tagline: **“Bolkar hisaab. Bharose ke saath.”** (Keep this as optional marketing copy; do not overuse it in the actual UI.)

## The problem
Many small retailers manage inventory, daily sales and customer *udhaar* through memory, notebooks, calculators and fragmented apps. Typing is inconvenient when serving customers. Speech is more natural, but a voice assistant that misunderstands “do packet” versus “do sau packet,” the wrong product variant, a cash sale versus an udhaar sale, or a repayment versus new credit can cause real financial harm.

## The product promise
A shopkeeper can speak naturally in Hindi, Hinglish/Romanized Hinglish and English to:
- record a sale, restock, udhaar sale, customer repayment or approved adjustment;
- ask for stock, low-stock items, today's sales, a customer's balance and a day-end summary;
- receive a spoken answer and a readable receipt/summary;
- inspect exactly what the system understood before any consequential write;
- correct mistakes, audit activity and recover from supported mistakes without silently erasing history.

## What makes this meaningfully different
Do not compete on “we added a microphone to CRUD.” Build **Trustworthy Voice Commerce**:
1. **Trust Engine:** transcription → structured interpretation → local validation → preview/clarify/reject → explicit confirmation → atomic database commit → receipt + spoken feedback.
2. **Indian speech robustness:** deliberately evaluate Hindi-English code-switching, Romanized Hinglish, number/currency expressions, product names and controlled noise. Use Gnani Prisma for STT and Timbre for TTS, within the account's supported models/voices.
3. **Grounded business answers:** numerical business answers come from SQL, never from a generative model inventing totals or balances.
4. **Evidence, not hype:** a Voice AI Lab shows the actual test-set composition, exact metrics, failure examples, latency and limitations. Never hardcode or fabricate a score.
5. **Real retail workflows:** distinguish cash sales, udhaar sales, restocking and repayments. Keep stock and customer balances consistent.

The strongest initial story is code-mixed voice plus practical shop impact. Do not claim the project is production-ready or perfectly accurate. Demonstrate where it is safe, where it asks questions, and how it handles failure.

---

# 2. Starting point: inspect the supplied repository, then verify all assumptions

The current repository supplied with the project appears to contain:
- Frontend: React, Vite, Tailwind CSS and Framer Motion (`frontend/src/App.jsx`, `App.css`, `index.css`).
- Backend: Flask (`backend/app/main.py`), SQLite handling/intent logic (`backend/app/intent_parser.py`, `db_setup.py`) and Gemini command interpretation (`gemini_understanding.py`).
- Gnani speech-to-text call using `POST https://api.vachana.ai/stt/v3` with `X-API-Key-ID`, multipart audio, language code and text normalization.
- Dashboard inventory/customer balances, transaction ledger, inventory/customer manual forms, product/MRP lookup, ambiguous variant selection and new-product restock confirmation.
- Some backend tests under `backend/tests/`.
- `overlay.py` uses PyWebView to run a local Flask server in a desktop window and registers global hotkeys.

Initial issues to verify—not assumptions to blindly patch:
- `/api/process-audio` appears to save every recording to a fixed filename (`temp_command.wav`), creating collision risk if two requests overlap.
- Interpreted sales/credit actions appear to be committed immediately by `parse_and_execute`; the new design must preview and confirm every voice-initiated write.
- `Price` appears to be used for both sales totals and restock cost/MRP. The data model needs to distinguish MRP, selling price and purchase cost before claiming profit or correct purchase economics.
- The current recognized intents appear to be `sell`, `restock`, `credit`, and `unknown`; repayments and grounded read-only query intents need to be added carefully.
- No complete Timbre TTS integration was obvious in the supplied source.
- Dashboard polling appears frequent; assess whether it can be replaced with sensible refreshes without making the UI stale.
- `main.py`'s direct-run path uses Flask debug mode, while `overlay.py` starts a non-debug server. Production packaging must never use debug/reloader mode.
- CORS, error logging, API key handling, writable database paths and packaged asset paths require an audit.

At the start, inspect current files and git status. Do not assume this list is exhaustive. Do not reveal or print secret values. Do not overwrite user edits. If git is available, work on a feature branch. Back up the current SQLite database before schema changes. Treat the included database as user/project data, not disposable test data.

Create these planning files before major edits:
- `PRODUCT_SPEC.md`: user journeys, supported commands, safety rules, non-goals.
- `ARCHITECTURE.md`: component diagram, data flow, external service calls, error paths.
- `IMPLEMENTATION_PLAN.md`: phases, tasks, dependencies and acceptance criteria.
- `BUILD_STATUS.md`: current tests/build status, completed items, known blockers and next action.
- `EVALUATION_PROTOCOL.md`: benchmark methodology, split policy, metric definitions and limitations.

After writing them, proceed with implementation phase by phase. Do not stop at merely producing a plan unless a genuine blocker prevents safe execution.

---

# 3. Non-negotiable engineering rules

1. **Never invent results.** No fake benchmark numbers, fake model comparisons, fake TTS functionality, fake API responses or fabricated citations/source information.
2. **Never let an LLM directly write to SQLite.** The model only proposes a typed command. Python validation and domain services decide whether it is allowed; the database is changed only by trusted deterministic code.
3. **Never mutate on an unclear command.** Missing quantity, amount/product/customer, ambiguous entity, conflicting intent or invalid arithmetic must trigger a question or a rejection, not a guess.
4. **All voice writes need an explicit preview and confirmation.** Read-only queries can answer directly after resolving their targets. Make the UI clearly distinguish “draft/pending” from “committed.”
5. **Confirmation must be idempotent.** Repeated clicks, network retries, WebView double events or repeated confirm calls must not create duplicate sales, credit entries or payments.
6. **Use atomic database transactions.** Stock mutation, customer-balance mutation and corresponding ledger entry must commit together or roll back together.
7. **Never silently delete history to fix mistakes.** Use reversal/correction entries and preserve an audit trail. Undo must be a reversing transaction, not a hidden destructive edit.
8. **Keep API secrets out of frontend code, logs, git and the packaged binary.** Never print even the prefix/length of a real API key for debugging. Load credentials from a local config/env file or a setup screen and never return them via an API.
9. **Be transparent about internet needs.** SQLite and manual bookkeeping should work locally. Speech recognition, TTS and external LLM interpretation require network/API access. Show this state honestly; do not claim full offline AI.
10. **Use synthetic demo data.** Do not record, expose or upload real customers' names, phone numbers, balances or audio for the public demo. Don't send a full customer database or unnecessary personal data to an LLM.
11. **Do not bundle secrets in the EXE.** The owner must supply API credentials on first run or through an external local config.
12. **Keep current useful features working.** Migrate schemas in a backward-compatible way, keep old ledger rows visible, and provide safe failure paths.
13. **No architectural rewrite for aesthetics alone.** Refactor only to improve correctness, testability, maintainability, speed or user experience.
14. **Pin/review dependencies.** Do not add a large framework if a small module solves the problem. Explain any added native dependency that may affect PyInstaller/WebView.
15. **No unverified sales/margin claims.** If a data field is missing, mark the metric unavailable rather than infer it.

---

# 4. Main user journeys and command contract

Build a common typed command contract before adding many intents. A model output should be schema-constrained where possible and validated locally regardless of schema adherence.

A practical internal representation (adapt names to the project's style) is:

```json
{
  "command_id": "server-generated-uuid",
  "operation": "sale | restock | udhaar_sale | repayment | balance_query | inventory_query | low_stock_query | today_summary | day_close | manual_credit_adjustment | unknown",
  "entity_text": "text actually mentioned by the user",
  "item_id": null,
  "customer_id": null,
  "quantity": null,
  "unit": null,
  "amount_paise": null,
  "language": "en-IN | hi-IN | mixed | unknown",
  "missing_fields": [],
  "ambiguities": [],
  "needs_confirmation": true
}
```

This is a design example, not a requirement to copy blindly. Use strict enum/schema validation and keep API payloads versionable. Do not trust model-supplied `command_id`, database IDs, final balances, stock levels, totals, permissions or a self-reported confidence score.

## Supported intents, in order of priority

### A. Sale (cash sale)
Examples:
- “Do packet Maggi bech diya.”
- “Sell three Tata Salt packets.”
- “Teen Maggi, cash.”

Expected handling:
- Resolve the exact product variant.
- Resolve a whole-number package count initially; only add weight/volume quantities after defining conversion semantics. Never treat “2 kilo” as two packets.
- Validate enough stock exists.
- Calculate the sale total from the verified selling price, not from model output.
- Show product, variant, quantity, unit price, total and resulting stock estimate in the confirmation preview.
- After confirmation, atomically decrement stock and add a Sale ledger record.

### B. Restock
Examples: “Add ten Maggi packets”; “Aaj Fortune oil ke 12 bottles aayi hain.”
- Resolve existing product variants or enter the new-product flow.
- Validate positive quantity and variant.
- Show the impact before changing stock.
- Do not call an online price/MRP suggestion a verified truth. Keep source links and label suggestions clearly. Let the owner review packaging/MRP before accepting.
- Purchase cost must not be calculated from MRP unless the owner explicitly entered the same number as purchase cost.

### C. Udhaar sale (sale on customer credit)
Example: “Ramesh ke udhaar mein do Maggi add kar do.”
- This is not just a balance increment. If a product is being sold on credit, stock must decrease and the customer's balance must increase in the same atomic transaction; sales/credit ledger entries must make the relationship understandable.
- Resolve customer and product. If either is ambiguous, ask a targeted question.
- Preview both effects: stock after sale and new outstanding balance.
- Confirm before committing.

### D. Repayment / payment received
Examples: “Ramesh ne 200 rupaye de diye”; “Ramesh paid ₹500 towards his udhaar.”
- Reduce outstanding balance by the payment amount; do not increase it.
- Ask a clarification if the speech could mean a new credit entry versus a repayment.
- If payment exceeds the outstanding balance, stop and ask how to handle it. Do not silently create negative debt or reinterpret it.
- Support partial payments and record time, amount and linked customer.
- Commit payment and balance update atomically.

### E. Customer/account query
Examples: “Ramesh ka kitna udhaar hai?”; “Show outstanding balances.”
- Answer from SQLite.
- If multiple customers match, ask which one.
- Never call the language model to calculate the balance.

### F. Inventory query and low-stock query
Examples: “Maggi kitni bachi hai?”; “What is running low?”
- Read from SQLite.
- Configure reorder thresholds per item; don't use a mystery universal threshold.
- Distinguish “low stock based on the owner's threshold” from “predicted to sell out soon.” The latter is only available with enough trustworthy sales history and must be labeled an estimate.

### G. Today's sales / day-end summary
Examples: “Aaj ki sale kitni hui?”; “Give me today's hisaab.”
- Query event/ledger records over a clearly defined local day boundary and timezone.
- Separate cash sales, udhaar sales, repayments, restock purchases and any recorded expenses. Do not equate repayments received with new revenue.
- Distinguish sales revenue, cash collected and outstanding credit. Explain the metric label in the UI.
- Only show gross profit if the purchase cost and selling price are known and consistent for the relevant sold items. Otherwise show “margin unavailable: cost not recorded.”

### H. Unknown / unsafe / unrelated request
Examples: product or quantity can't be determined, unknown business intent, unsupported refund, request with contradictory values, or an instruction embedded in a transcript trying to override rules.
- No write.
- Show a useful, concise clarification or say what isn't supported yet.

### Later/stretch intents—do not begin these until the core test suite passes
- Returns/refunds with stock restoration policy.
- Expenses and supplier payments.
- Multi-item basket/orders.
- Supplier ledger and purchase invoices.
- Expiry/batch tracking for food products.
- Barcodes, WhatsApp ordering, cloud sync and multi-store roles.
- Demand forecasting beyond a transparent simple baseline.

Do not add these simply to inflate the feature list. Each must have a clearly defined accounting/data model and tests before implementation.

---

# 5. Trust Engine: the signature architecture

Implement a predictable lifecycle for every command:

`RECEIVED → TRANSCRIBED → INTERPRETED → VALIDATING → NEEDS_CLARIFICATION | REJECTED | READY_FOR_CONFIRMATION → COMMITTED`

Terminal/alternate states should include `CANCELLED`, `EXPIRED`, `FAILED_EXTERNAL_SERVICE` and `FAILED_COMMIT` where useful. Persist enough information to debug and audit a command without keeping audio forever by default.

## Rules
- Read-only queries can proceed once entity ambiguity is resolved.
- Every write is a draft until the user confirms.
- Drafts expire after a reasonable interval and cannot be committed twice.
- Server-side confirmation must check the current state and perform the mutation under a database transaction.
- Re-check stock, balance, item variant, price and any relevant constraints at confirmation time. The preview can become stale while a dialog is open.
- Store a generated idempotency key with a unique constraint or equivalent mechanism.
- Keep the original transcript as the user input record where appropriate; allow the user to inspect/edit the transcript before interpretation is finalized.
- The system may use model outputs to identify likely intent/entities, but local validation determines allowed actions.
- Return explicit machine-readable error codes (for example `AMBIGUOUS_PRODUCT`, `INSUFFICIENT_STOCK`, `OVERPAYMENT_CONFIRMATION_REQUIRED`, `API_UNAVAILABLE`, `DRAFT_EXPIRED`) plus human-readable bilingual messages.

## Trust timeline
For each command, display a short timeline such as:
1. Voice received.
2. Transcript recognized.
3. Action interpreted.
4. Product/customer/amount validated.
5. User confirmed / cancelled.
6. Database committed / rejected.

Do not expose private chain-of-thought or raw hidden model reasoning. Explain the concrete parsed fields and validation outcomes instead: “I found two products named Maggi with different variants,” not “the AI thought…”

## Correction and undo
- Let the user cancel any draft.
- For a recently committed transaction, offer “Undo” only if safe and supported. Implement this as a reversing/correction entry, preserving original record and audit metadata.
- If reversing a sale would cause stock/balance inconsistency, explain why and offer a proper correction workflow instead of forcing a delete.
- Add a bounded undo time window only if it can be enforced reliably.

---

# 6. Database integrity and domain model

First inspect actual schema and data. Create migrations, not a destructive database reinitialization. A migration must back up the database, run in a transaction where possible, preserve historical rows, and have a test on a copy of a legacy database.

## Product pricing must become unambiguous
The existing `Price` value appears to serve multiple purposes. Correct this before showing profit/cost insights. Prefer explicit fields such as:
- `MRP` — printed maximum retail price, when known.
- `SellingPrice` — price charged to the customer.
- `PurchaseCost` — what the shopkeeper pays the supplier.
- `Unit` — `piece`, `packet`, `bottle`, `kg`, `g`, `l`, `ml`, etc.; define supported quantity semantics clearly.
- `ReorderLevel` — store owner setting.
- `Aliases`/product alias table — alternative spoken names, spelling variants and local nicknames.

A safe migration must not silently assert that a legacy price is both MRP and purchase cost. Preserve legacy values and label them “legacy price—review mapping.” For demo seed data, enter clearly defined sample purchase cost, selling price and MRP. Do not backfill financial facts that are unknowable.

## Customers and accounts
Preserve customer IDs/balances from the existing database. Add aliases if useful. Do not expose phone numbers unless essential. Customer balance changes must be transactionally linked to ledger entries.

## Ledger and audit
- Preserve the existing `Transactions` table and historical rows.
- Define clear transaction types and sign semantics in documentation.
- Ensure the UI doesn't present restock spend as negative “sales” or customer repayments as new revenue.
- Consider normalized transaction/event entries for `Sale`, `UdhaarSale`, `Repayment`, `Restock`, `Adjustment` and reversal entries.
- Store command ID / idempotency reference when possible so the transaction can be traced to the voice action.
- For currency math, avoid repeated floating-point accumulation; use integer paise or `Decimal` with explicit conversion and rounding. If adding an integer-paise representation, preserve backward-compatible API fields while migrating carefully.
- Add a consistency-check utility that compares customer balances to the relevant ledger entries if the ledger contains enough complete historical information. For old/incomplete data, report that it cannot reconcile rather than making a silent correction.

## SQLite engineering
- Use context managers or a shared repository/service layer.
- Configure sensible `timeout`, transactions and foreign keys where tables support them.
- Add relevant indexes for timestamp/type/entity/customer queries.
- Use parameterized SQL everywhere.
- Check affected-row counts for edits and confirms.
- Never leave a connection open on exceptions.

---

# 7. Gnani model integration: implement real end-to-end speech

## Speech-to-text: Prisma
The repository already calls the Gnani STT REST endpoint. Keep it behind a provider adapter (for example `GnaniSTTProvider`) so it can be tested with mocks and changed without rewriting route logic.

Use the official account documentation as the source of truth for endpoint/auth/model versions. Existing code/docs reference:
- endpoint `https://api.vachana.ai/stt/v3`;
- `X-API-Key-ID` auth header;
- multipart `audio_file`, `language_code`, `format=transcribe`;
- `itn_native_numerals` option.

The shared uploaded API guide says `format=transcribe` normalizes amounts/numbers and that the REST service supports up to 60-second clips, with shorter clips preferred. It also documents a domain `bias_list` with single-word entries and positive `bias_score`. Verify the actual account permissions and current docs rather than assuming every optional field is enabled.

Implementation requirements:
- Replace the fixed temp audio filename with a unique temporary file and reliable cleanup in `finally`.
- Set upload limits and a reasonable audio-duration limit. Reject unsupported formats with a helpful UI message.
- Use explicit timeout values; handle 400, 403, 429, 500 and 503 separately enough to give useful feedback. Use bounded retries with backoff only for transient errors; don't retry malformed inputs indefinitely.
- Limit repeat transcription calls to avoid wasting the programme credits. Start with the existing primary language strategy and evaluate it; only run Hindi/English alternatives when a useful rule or measurable result justifies the extra call.
- Keep digits normalized to western digits for internal parsing where possible; preserve original transcript for display. Test Hindi native digits if needed.
- Experiment with word boosting for frequently misheard product-brand terms. Because the documented boost list only accepts single-word tokens, don't pass phrases or symbols such as `HDFC2` that violate the documented format. Start conservatively; aggressive boosting can create false recognitions.
- Consider product aliases locally before spending an extra API call.
- Do not log audio bytes or complete transcripts to public logs by default.

## Text-to-speech: Timbre
Implement a real TTS adapter and audio playback. Do not simulate it using browser speech synthesis and claim that it is Gnani Timbre.

Current Gnani public documentation demonstrates the REST endpoint:
`POST https://api.gnani.ai/v1/tts/inference`
with bearer authorization and a JSON body including model `timbre-2.5`, supported language, configured voice, sample rate and text. Check the developer dashboard/current official docs for the exact model/voice names permitted by this account before finalizing. The API may be in beta or expose different voice options by language.

Requirements:
- Read `GNANI_TTS_API_KEY`/configured credentials from server-side settings; if the account uses one key for multiple services, support that intentionally without printing it. Keep STT and TTS credential config separable if headers/permissions differ.
- Use a small provider module that returns audio bytes/content type and a stable error code.
- Play the generated audio in the desktop UI. Clean up object URLs/audio resources and prevent overlapping spoken responses.
- The spoken acknowledgement must be generated from the **committed database result**, not from a model's prediction before a commit.
- For drafts, speak a concise confirmation or clarification prompt. For cancellations/errors, explain what happened without claiming that a change was saved.
- Use the shop's selected language or the detected/selected interaction language only where the TTS voice is actually supported. Fall back to readable text if the requested voice/language is unavailable.
- Provide a mute/voice-output toggle and volume/replay control. Do not force speech while the user is already talking.
- Use request size/text-length limits. Cache only safe static prompts or explicitly safe repeated outputs; don't build a cache that mixes private customer responses across users.

## Model-agnostic intent interface
- Keep the current Gemini provider as a baseline until another provider is actually accessible.
- Add an interface such as `IntentProvider.interpret(transcript, context)` returning schema-validated JSON.
- Do not claim Evon is wired in unless valid API/weight access is actually configured and tested. If access later becomes possible, it should plug into the same interface.
- Minimize data sent to external providers. Prefer sending transcript plus the smallest necessary non-sensitive context, and resolve product/customer names locally. Avoid sending the whole customer database, phone numbers, balances or unrelated inventory records to Gemini.
- Never send API credentials to the frontend or put them inside the packaged executable.

## Programme-credit efficiency
The account has 5,000 challenge credits. Do not guess the unit price or cost per call. Measure usage from the dashboard/API responses if possible. Track calls and approximate request counts locally, avoid repeated same-input experiments during development, batch evaluation thoughtfully, and reserve credits for final end-to-end tests. Do not cache production/private customer payloads unsafely.

---

# 8. Product experience: make the app feel like a real retail tool

Do not redesign everything before functional workflows pass. First map current components and preserve good UI pieces, then improve hierarchy and ergonomics.

## Main views
1. **Home / Voice desk:** one obvious record button, clear listening/transcribing/thinking states, visible transcript, recent action and a concise today summary.
2. **Pending action preview:** a large readable card with intent, item/customer, quantity/amount, price basis, expected stock/balance effect, warnings and Confirm / Edit / Cancel. Keep money and quantity visually distinct.
3. **Inventory:** search, variant grouping, stock, MRP, selling price, purchase cost (if recorded), reorder level, low-stock state and alias management.
4. **Udhaar / Customers:** customer search, outstanding balance, recent credit/repayment history, and payment action.
5. **Ledger:** filter by date/type/customer/product, readable transaction details and reversals clearly marked.
6. **Business insights:** daily sales vs cash collected vs credit outstanding, low stock and day-end report. Display margin only if purchase-cost coverage is adequate.
7. **Voice AI Lab:** real benchmark summary, filters/slices, latency and errors—not vanity charts with invented data.
8. **Settings / Setup:** STT/TTS readiness, intent-provider readiness, selected language/voice, microphone permission, credit/key configuration instructions, local database path, data backup/export and privacy explanation.

## Voice UI states
Visually distinguish at least:
- idle;
- microphone permission needed;
- recording/listening;
- processing/transcribing;
- interpreting;
- clarification needed;
- awaiting confirmation;
- committed/success;
- cancelled;
- API/network failure;
- invalid/rejected command.

Provide manual text entry as a fallback so the product remains testable without a microphone. Have clear errors and a “Try again” action. The current interface is a desktop overlay: consider supporting both a normal resizable main window and a compact voice-desk/overlay mode. Avoid making the whole application permanently topmost unless the user opts in.

## Accessibility and usability
- Large touch/click targets suitable for a shop counter.
- High contrast and legible type; don't communicate error/success by color alone.
- English and Hindi UI strings for core screens. Keep translation keys centralized rather than scattering one-off strings.
- Keyboard navigation and obvious focus state.
- Confirm destructive or financial writes. Avoid modal overload for simple read queries.
- Display rupees with Indian number formatting (`₹1,25,000`).
- Never use decorative animation that makes the core interface laggy or hides operational state.

---

# 9. Useful and distinctive features (ordered by real value)

## Build these after write safety and core workflows

### 9.1 Spoken receipts
After a commit, show and optionally speak a receipt summarizing the exact transaction and its updated effects. Include time, product/customer, quantity, amount and command ID/short reference. The text and voice must reflect the actual stored transaction.

### 9.2 Shop-specific vocabulary and alias memory
Let the owner associate local nicknames/variants with existing products, for example “chhota Maggi” or a commonly misrecognized brand name. Store aliases locally and let the shopkeeper approve learned corrections. Do not silently learn from an uncertain interpretation. Show where to review/remove aliases. Use aliases to improve matching and reduce external calls.

### 9.3 “Why did it ask me?” explanations
When the system asks for clarification, explain the specific ambiguity: two product variants matched, the customer name could refer to two records, the payment exceeds balance, or the quantity isn't clear. Don't show hidden model reasoning.

### 9.4 End-of-day Hisaab / Shopkeeper recap
Generate a deterministic summary from the ledger:
- number/value of cash sales;
- number/value of udhaar sales;
- repayments received;
- current total outstanding udhaar;
- restocks recorded;
- low-stock products;
- missing purchase-cost data that prevents reliable profit estimates.
Let the user play the recap in supported language. Use clear date/time boundaries and explain totals.

### 9.5 Simple reorder suggestions
Start with a transparent baseline using owner-set reorder levels. Only add a time-to-stockout estimate if there are enough days of reasonably complete sales history; disclose sample size and method. Offer suggestions, not autonomous purchases. Never pretend this is advanced ML if it is a rule-based calculation.

### 9.6 Voice AI Lab / benchmark runner
Use the evaluation protocol in Section 10. The UI should let a reviewer inspect real results for language condition, noise condition, failure type and pipeline configuration. Include sample counts and confidence intervals when appropriate. If results haven't been run, show “not measured.”

### 9.7 Transaction timeline / safe undo
Give the owner an understandable history of what was interpreted, what was confirmed and what was committed. Retain an append-only audit trail. Reversals should be explicit ledger events, not silent edits.

### 9.8 Demo mode
Create a one-click demo environment with clearly marked synthetic products/customers and repeatable reset. It must use a separate demo database or a tested safe-reset routine. Never reset/delete real shop data.

## Stretch features only after core acceptance criteria pass
- Tamil/Telugu or another additional locale only after both STT and TTS support is verified and tested end-to-end. STT language availability does not prove a TTS voice is available.
- A controlled noise robustness challenge using consented or generated audio and documented SNR levels.
- A small basket flow for multiple products in one command.
- Stock expiry/batch tracking.
- Supplier ledger and purchase invoice imports.
- Offline text/manual mode and local backup/restore improvements.

Do not prioritize barcode scanning, WhatsApp integration, cloud syncing, automatic supplier ordering, multi-store infrastructure or a large forecasting model before the core product is reliable. They are plausible future directions, not launch requirements.

---

# 10. Evaluation and evidence: treat this like a small applied research project

Create a reproducible offline evaluation harness that can run without spending API credits if it is testing parser/business rules only. Keep model evaluation and database-safety tests separate.

## 10.1 Dataset
Start with a manually reviewed labelled dataset of at least 200–300 **text utterances** across supported intents, then build an audio subset of at least 50–100 commands if time and recording permission allow. These are targets, not claimed results. Clearly label all generated/noisy samples as synthetic. Do not imply synthetic noise is the same as real shop audio.

Ensure coverage of:
- English;
- Hindi in Devanagari;
- Romanized Hinglish/code-mixed text;
- numerals spoken as words and digits;
- currency (`₹`, rupees, rupaye, lakh) and quantities;
- product aliases and variants;
- customer aliases;
- similar names;
- no entity or no amount;
- ambiguous intent (new credit vs repayment, cash sale vs udhaar sale);
- low-stock/unknown product cases;
- contradictory or impossible requests;
- irrelevant requests and transcript-injected instructions;
- normal and synthetic noise conditions for audio.

Each row should have a unique ID, original utterance, language/style, scenario, expected intent, expected slots, ambiguity/clarification expectation, and expected allowed side effect. Keep private data out.

## 10.2 Leakage prevention
Split by **base utterance/scenario group**, not randomly by individual paraphrase. Paraphrases from the same template must not leak across train/tune and holdout sets. Freeze a held-out test set before adjusting prompts/rules against it. Document the split and dataset version.

## 10.3 Metrics
Report definitions and counts for:
- STT word error rate (WER), and character error rate where useful for Indic scripts;
- intent accuracy and macro-F1;
- slot/entity exact match for product, customer, quantity, unit and amount;
- exact transaction correctness: operation + entity + quantity/amount + database outcome all correct;
- unsafe-write rate: incorrect/ambiguous/invalid input that changes the database;
- clarification/rejection rate and clarification precision for ambiguous examples;
- false acceptance of unsupported commands;
- p50 and p95 latency for STT, interpretation, TTS and end-to-end path;
- service/API failure rate and timeouts.

Include denominators and sample counts. One hundred percent over ten examples is not the same evidence as one hundred percent over a larger independent test set. If a metric cannot be measured, state why.

## 10.4 Experiments worth running
1. Existing baseline vs structured/validated command pipeline.
2. STT default config vs conservative domain word boosting.
3. Single transcription vs alternate-language retry policy: compare accuracy gain against extra latency/credit cost.
4. Entity matching with alias rules vs no aliases.
5. Confirmation policy and ambiguity handling: measure whether risky cases are safely deferred.
6. Optional later: compare another reasoning provider only if it is actually accessible and can be evaluated under the same fixed test set.

Do not compare providers using different utterances or different acceptance criteria. Keep prompts/config/version fixed for each reported run and save raw result JSON/CSV.

## 10.5 Trust and safety acceptance targets
Before broadening scope, aim for:
- **zero state mutations** on unknown, rejected, ambiguous or unconfirmed write commands in the deterministic test suite;
- duplicate confirm requests produce exactly one committed transaction;
- all test cases involving insufficient stock are rejected without changing stock;
- all test cases involving repayment direction and overpayment follow the documented rule;
- every successful write has exactly one appropriate ledger/audit linkage;
- no fabricated totals in read-query tests: returned values match SQL fixtures exactly.

Treat these as test requirements; don't report benchmark performance until actually measured.

---

# 11. Testing strategy and quality gates

## Backend unit tests
- Every operation's parser/schema validation.
- Invalid JSON/model shape, unknown enum, missing entity, missing quantity/amount, negative/zero/oversized values.
- Intent confusion: sale vs restock; udhaar sale vs balance adjustment; new credit vs repayment; repayment vs sale.
- Alias normalization and product variant ambiguity.
- Insufficient stock; stale stock after draft creation; duplicate confirmation; expired/cancelled draft.
- Partial repayment, exact repayment, overpayment refusal/clarification.
- Atomic rollback if ledger insertion fails after an inventory update is attempted.
- Customer balance and ledger consistency.
- Correct totals/date boundaries and distinction of sales/repaid amounts/restock costs.
- Invalid/ambiguous query must not accidentally write data.
- API timeout, 401/403, 429, 5xx, malformed provider payload and missing key.
- STT temporary-file cleanup and simultaneous-request collision regression test.
- Legacy schema migration preserves all historical rows and values.
- Demo reset never targets the real database path.

## API/integration tests
Use mock external providers so the test suite does not require internet or consume credits. Test the complete lifecycle: audio/text input → draft → confirm/cancel → DB change/receipt. Have a small opt-in smoke test for real Gnani APIs that runs only when credentials are configured and clearly reports that it consumed an API call.

## Frontend tests/manual checks
At minimum check:
- recording permission and denied state;
- submit/stop recording and no duplicate requests;
- transcript display and edit/retry;
- pending preview confirm/cancel/edit;
- loading/error/retry states;
- spoken response playback/mute/replay;
- narrow window/resizable desktop layouts;
- English/Hindi core UI strings;
- dashboard/ledger refresh after commits;
- microphone/API failure leaves the app usable for manual actions.

## Quality gate after each phase
- `python -m unittest discover -s backend/tests -v` (or the repo's verified preferred test command);
- `npm run lint` in `frontend/`;
- `npm run build` in `frontend/`;
- a short manual end-to-end smoke test on the intended Windows machine;
- update `BUILD_STATUS.md` and note any remaining failures honestly.

---

# 12. API/service layout: separate routes from business rules

Keep Flask if that is the current working stack, but avoid putting complex accounting logic inside route functions. A reasonable small architecture is:

- `providers/gnani_stt.py`: Prisma STT adapter.
- `providers/gnani_tts.py`: Timbre TTS adapter.
- `providers/gemini_intent.py`: current Gemini structured interpretation adapter.
- `domain/command_schema.py`: operation schema, normalization and validation.
- `services/command_service.py`: interpretation, validation, draft lifecycle and confirmation.
- `services/transaction_service.py`: atomic inventory/customer/ledger mutations and reversal behavior.
- `services/query_service.py`: SQL-backed read-only answers and summaries.
- `repositories/`: database access with parameterized queries and managed connections.
- `services/evaluation_service.py`: load labelled test cases, run eval, write real metrics.
- `services/demo_service.py`: create/reset only the demo database.

Adapt to the project rather than creating layers with no useful purpose. Add an app factory/config separation if needed for isolated tests and desktop packaging.

Possible endpoint design—fit it to existing naming where backward compatibility matters:
- `POST /api/voice/interpret` or adapt `/api/process-audio`: audio → transcription → validated draft/query result.
- `POST /api/commands/<id>/confirm`: commits a draft once.
- `POST /api/commands/<id>/cancel`: cancels a pending draft.
- `POST /api/voice/synthesize`: generate spoken response from server-authorized text.
- `GET /api/commands/<id>`: read command state/receipt.
- `GET /api/dashboard`, `/api/ledger`: preserve and improve existing endpoints.
- `GET /api/analytics/today`, `/api/analytics/low-stock`, `/api/analytics/day-close`.
- `GET/POST /api/settings` for non-secret preferences; never return secret keys.
- `/api/demo/reset` only if explicitly in demo mode and separate-database protection is proven.
- `/api/health` that reports service readiness without leaking config/secrets.

Do not create duplicate endpoints if existing ones can be extended safely. Add API contract examples to `ARCHITECTURE.md`.

---

# 13. Security, privacy and resilience

- Keep Flask bound to loopback (`127.0.0.1`) for the desktop build; do not expose the dev server to the LAN by default.
- Disable debug mode and reloader in production/packaged mode.
- Restrict CORS to the actual local frontend origins needed by the app; don't use permissive CORS without a reason.
- Validate all payload types/sizes and reject malformed requests with consistent JSON responses.
- Never trust frontend-supplied product IDs/price/totals or status; re-fetch and verify these on the server immediately before writing.
- Avoid unsafe use of string interpolation in SQL.
- Avoid logging full customer balances, phone numbers or API keys. Keep structured logs useful but privacy-conscious.
- Explain that audio is sent to Gnani for transcription and that transcripts may be sent to the configured interpretation provider. Provide an honest privacy note and use synthetic data for public demos.
- Consider short-lived audio deletion after transcription. Retain audio only if the owner explicitly enables a documented feature for it.
- Use network timeouts, bounded retries and a clear service-health state.
- App must not lose a typed/manual operation because STT or TTS is down.
- Use local backup/export with a guided restore. Never overwrite a database during restore without explicit confirmation and a backup.
- Remove `overlay.py` debug output that exposes even a key prefix. Don't log secrets or env values.
- Do not invent encryption guarantees. If using OS credential storage, document exactly what is protected; at minimum keep `.env` outside the executable and out of version control.

---

# 14. Windows executable: final delivery, not the first milestone

The supplied project includes PyWebView and a launcher script, but packaging paths and database/config locations need a deliberate audit. The final result should be a reliable **Windows desktop executable** (prefer a robust one-folder bundle first; produce a one-file EXE only if it tests cleanly).

## Packaging requirements
1. Build the frontend production assets first (`npm run build`).
2. Use a production Flask configuration (no debug/reloader), start the server on loopback in a managed background thread/process, verify readiness before opening WebView, and shut down cleanly when the window closes.
3. Handle port conflicts gracefully—try a safe free loopback port or report a useful error; don't open the wrong service if a port is taken.
4. Resolve assets correctly in both development and PyInstaller's frozen environment; use `sys._MEIPASS` only for read-only bundled resources.
5. Store writable user data, the SQLite database, settings and logs in a stable user-writable directory such as `%LOCALAPPDATA%\KiranaSync\`, not inside the one-file bundle or an assumed working directory.
6. On first run, create/migrate an empty or existing user database safely; provide a separate demo-data option. Never copy the test/demo DB over an existing user DB.
7. Provide first-run setup for Gnani STT/TTS credentials and the intent provider. Credentials must be entered after installation or supplied in external local config; never bundle a real key.
8. Include all required static assets, Python modules, templates and native PyWebView dependencies. Test on a clean Windows user environment without the development virtualenv.
9. Ensure microphone access, generated audio playback, minimize/close, resizable window and hotkeys work in the packaged app. Hotkeys should be optional, documented and cleanly unregistered.
10. Add app icon, version, friendly startup/error messages, `README_WINDOWS.md`, `requirements-lock`/pinned dependencies and build instructions.
11. Provide `build_windows.ps1` or an equivalent reproducible build script and a clean final output directory such as `dist/KiranaSync/`.
12. Never claim an EXE is successful just because PyInstaller exits with code 0. Launch the actual EXE and test voice/manual flows, DB persistence, API-key setup, no-network errors, exit/restart and an upgrade/migration on a disposable test database.

Do not share API keys in screenshots, logs, demo videos or the repository. If credentials are required at startup, make that clear in installation instructions.

---

# 15. Delivery roadmap and phase gates

The challenge deadline is November 10, 2026, so ship a reliable core well before it and retain time for demo rehearsal and submission. Dates are suggested planning checkpoints, not an excuse to skip tests.

## Phase 0 — Audit and baseline (Oct 17–18)
- Inspect all files and current git changes.
- Run existing backend tests, frontend lint and production build.
- Start the application and document actual current working and broken flows.
- Inspect DB schema and contents without changing the user's DB.
- Confirm current API access/model/voice details in Gnani dashboard/docs.
- Write PRODUCT_SPEC, ARCHITECTURE, IMPLEMENTATION_PLAN, EVALUATION_PROTOCOL, BUILD_STATUS.
- Make a backup before migrations.

**Gate:** know exactly what works today; reproducible baseline captured; no user data changed.

## Phase 1 — Data safety and write lifecycle (Oct 19–21)
- Add pending-command state and server-generated IDs.
- Refactor voice writes into proposal and explicit confirm/cancel steps.
- Add strict validation, idempotency, current-state revalidation, atomic transactions and audit linkage.
- Fix temporary audio file collision and ensure cleanup.
- Add tests proving unconfirmed/ambiguous/duplicate commands do not mutate data.

**Gate:** zero unintended writes in deterministic safety tests; existing dashboard, ledger, inventory and customer management still work.

## Phase 2 — Complete the useful voice loop (Oct 22–24)
- Add real Timbre TTS via a provider adapter and actual account-supported voice/config.
- TTS responses must reflect actual committed results or ask clarification while pending.
- Add visible playback, mute/replay, failure fallback and a clear interaction state machine.
- Add spoken/transcript review and manual text-entry fallback.

**Gate:** a real STT → intent → preview → confirmed DB commit → TTS acknowledgement works end-to-end with credentials; mocked integration tests pass without credentials.

## Phase 3 — Correct retail accounting flows (Oct 25–28)
- Add distinct cash sale, udhaar sale, repayment and balance/inventory query intents.
- Make inventory and customer balance changes atomic.
- Add correct repayment direction and overpayment clarification.
- Resolve price semantics (MRP vs selling price vs purchase cost) through a safe migration and review UI.
- Add daily SQL-derived summary, low-stock thresholds and ledger filters.

**Gate:** transaction/accounting fixtures reconcile; no claimed profit when cost information is missing.

## Phase 4 — Indian voice and domain adaptation (Oct 29–31)
- Build/test local product/customer alias support.
- Evaluate current STT mode and conditional alternate transcription policy.
- Add conservative, measured word boosting for domain words if beneficial.
- Improve handling of Devanagari Hindi, Romanized Hinglish, mixed numbers/currency and similar product variants.

**Gate:** report changes using labelled examples and not anecdotal cherry-picking; no degradation of safety tests.

## Phase 5 — Evaluation harness and trust UI (Nov 1–4)
- Create versioned text dataset and audio subset; define held-out groups.
- Add automated parser/transaction tests and benchmark output CSV/JSON.
- Measure WER/CER where relevant, intent/slot correctness, unsafe-write rate, latency and API failures.
- Implement Voice AI Lab with real values, sample counts and failure examples.
- Write EVALUATION_REPORT.md with limitations and reproducible commands.

**Gate:** an evaluator can reproduce the numbers; all unmeasured claims are marked unmeasured.

## Phase 6 — Product polish and distinctive value (Nov 5–6)
- Complete spoken receipts, “why did you ask?” clarifications and end-of-day Hisaab.
- Add transparent low-stock/reorder suggestions where data supports them.
- Improve English/Hindi experience, error messages, accessible layout and demo mode.
- Check latency/performance and remove unnecessary polling/animations.

**Gate:** core demo is understandable in under 60 seconds and the product remains usable when one API is unavailable.

## Phase 7 — Desktop package, demo and submission (Nov 7–10)
- Package and test Windows desktop build in a clean environment.
- Prepare fresh synthetic demo data and reset script.
- Rehearse 60-second demo several times; record only actual working functionality.
- Finish README, architecture diagram, evaluation report and each person's honest contribution statement.
- Publish demo post on LinkedIn/X, tag Gnani's official account and use both required hashtags; then nominate the correct post link(s) in submission.
- Submit before 11:59 PM IST on November 10, 2026. Do not leave packaging or account submission to the final hour.

**Gate:** real EXE launches, core flow is repeatable, evidence and submission artifacts are ready. Only describe features actually working in the demo.

If schedule slips, reduce stretch features before cutting safety, tests, evaluation integrity or delivery rehearsal.

---

# 16. Definition of done

The project is not “done” because it looks attractive. It is ready for an external review only when all of these are true:

## Product
- A first-time reviewer can understand the purpose immediately.
- User can speak or type a command, see what was understood, clarify/cancel, and confirm a write.
- The UI distinguishes cash sale, udhaar sale, repayment, restock and read-only queries.
- It handles at least one real supported voice path using Gnani STT and one real supported spoken-response path using Gnani TTS.
- Core screens and errors work in English and Hindi; language claims are limited to verified support.
- Dashboard/ledger reflect actual database state and do not contain fake metrics.

## Data integrity and safety
- No write occurs before confirmation.
- Duplicate confirmation cannot double-apply.
- Every committed write has an appropriate ledger record and audit link.
- Inventory and customer balance mutations are atomic.
- Incorrect, ambiguous and failed provider calls do not mutate the database.
- Pricing fields do not silently conflate MRP, sales price and purchase cost.
- Old data is migrated safely and can be backed up/restored.

## Evaluation
- Dataset, split and metric definitions are versioned.
- Benchmark is reproducible and reports sample counts.
- At least one controlled improvement experiment is measured honestly.
- Error examples and limitations are documented.
- No claim of universal accuracy, full offline operation or advanced ML beyond what is implemented.

## Engineering
- Backend tests, frontend lint and production build pass.
- External APIs are mocked in ordinary tests; only opt-in smoke tests spend credits.
- API keys never appear in frontend bundles, logs or source control.
- App shows graceful service failures and manual fallback.
- `BUILD_STATUS.md` reflects the truth.

## Delivery
- Windows EXE/package launches on a clean target environment.
- It stores the user's database/config in a persistent writable location.
- No key is bundled.
- Demo/reset uses synthetic data and cannot erase real data.
- There is a setup README, tested build script, demo video and evaluation report.
- Public claims match the actual build and both required challenge hashtags are included in the nominated post.

---

# 17. First actions to take now

Do these in order and report the results in `BUILD_STATUS.md`:
1. Check git status and back up the current DB without modifying it.
2. Run backend tests, frontend lint and frontend production build; capture failures exactly.
3. Launch the current app and run the simplest existing voice command using synthetic data, noting every state and whether a write occurs before confirmation.
4. Verify STT credentials and test one short synthetic utterance. Verify TTS access and available model/voice from the official dashboard/docs. Do not print secrets.
5. Produce a precise repository audit and a phase-by-phase plan mapped to actual files/functions.
6. Begin Phase 1 after baseline evidence is saved. Prefer small diffs with tests over sweeping refactors.

When finished with each phase, report: files changed, user-visible capabilities added, tests run and outcomes, actual API calls/credits consumed if known, remaining defects, and the next highest-value step. Never say something is complete unless you verified it.
