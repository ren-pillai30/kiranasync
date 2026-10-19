# KiranaSync 2.0 Product Specification

## 1. Vision & Problem Statement
KiranaSync 2.0 is a trustworthy, voice-first operating assistant designed specifically for Indian neighborhood grocery (*kirana*) store owners.

Small retail store owners manage daily sales, stock, and customer credit (*udhaar*) under high-stress, noisy counter conditions. Hand typing on mobile/POS keyboards slows down customer service, but naive speech-to-text solutions risk financial errors (e.g., misinterpreting "do packet" as "do sau packet", confusing cash sales with credit, or misrecording a debt repayment as new debt).

KiranaSync eliminates these risks through the **Trust Engine Architecture**:
`Voice Input → Speech-to-Text (Gnani Prisma) → Structured Interpretation (NLU) → Deterministic Domain Validation → Clarification or Safe Preview → Explicit User Confirmation → Atomic Database Mutation → Verified Spoken Receipt (Gnani Timbre TTS)`.

---

## 2. Core User Personas & Use Cases

### Persona: Ramesh Bhai (Kirana Shop Owner)
- **Environment**: Busy, ambient noise (street traffic, ceiling fans, chatter).
- **Languages**: Natural code-mixed speech (Hindi, Romanized Hinglish, Indian English).
- **Need**: Fast checkout and logging without taking his eyes or hands completely off customer goods.

### Core Workflows

#### 1. Cash Sale (`sale`)
- **Utterance**: *"Do packet Maggi bech diya"* / *"Three Tata Salt packets, cash"*
- **Resolution**: Match exact product variant in `Inventory`. Ensure whole number quantity or valid unit. Check stock sufficiency.
- **Preview**: Show item, quantity, unit selling price, total amount, and remaining stock.
- **Commit**: Atomically decrement stock and insert a `Sale` transaction in `Transactions`.

#### 2. Restock / Inventory Addition (`restock`)
- **Utterance**: *"Fortune oil ke 12 packet aaye hain"* / *"Add 10 Dettol soap"*
- **Resolution**: If item exists, prepare restock draft. If item is unlisted, search online MRP suggestions, let shopkeeper confirm MRP/variant.
- **Preview**: Display item, quantity, purchase cost (if provided) or MRP, and resulting stock count.
- **Commit**: Atomically increment stock and record `Restock` transaction.

#### 3. Udhaar Sale (`udhaar_sale`)
- **Utterance**: *"Ramesh ke khate mein 2 Maggi likh do"* / *"5kg sugar on credit for Suresh"*
- **Resolution**: Resolve both product variant and customer account.
- **Preview**: Show product, quantity, sale value, resulting inventory stock, and customer's new balance.
- **Commit**: Atomically decrement stock, increase customer's `OutstandingBalance`, and record an `UdhaarSale` ledger entry with linked `CustomerID`.

#### 4. Repayment / Balance Settlement (`repayment`)
- **Utterance**: *"Ramesh ne 200 rupaye jama kiye"* / *"Ramesh paid ₹500 towards udhaar"*
- **Resolution**: Resolve customer and payment amount. Check against outstanding balance. If payment exceeds balance, require explicit confirmation.
- **Preview**: Show customer name, amount paid, and updated remaining balance.
- **Commit**: Atomically reduce `OutstandingBalance` and record `Repayment` transaction. (Never increases customer debt).

#### 5. Grounded Read-Only Business Queries
- **Utterances**:
  - *"Ramesh ka kitna udhaar baki hai?"* (`balance_query`)
  - *"Maggi ka kitna stock bacha hai?"* (`inventory_query`)
  - *"Kaunse items khatam hone wale hain?"* (`low_stock_query`)
  - *"Aaj ki total sale kitni hui?"* (`today_summary`)
  - *"Aaj ka hisaab batao"* (`day_close`)
- **Execution**: Directly queries SQLite tables with deterministic SQL aggregation. Never generates numbers via LLM. Stock and customer-balance answers are shown in the UI and spoken using Gnani Timbre TTS; other query results remain on screen.

#### 6. Customer Creation and Credit
- A credit entry for a previously unknown customer creates the customer record with the entered balance.
- A repayment is interpreted as money the customer pays the shopkeeper, and reduces (never increases) the outstanding balance.
- Voice interpretation is performed by Gemini, then validated locally before the database is changed.

#### 7. Product and Customer Removal
- Products may be removed manually or by voice for reasons such as expiration or recall. A removal requires confirmation, sets active stock to zero, records a write-off, and retains transaction history.
- Customers may be removed manually or by voice. Removal requires confirmation when the outstanding balance is at least ₹1. A non-zero-balance account is archived with its balance and transaction history retained. A zero-balance customer is deleted from the active customer table while transaction history remains.
- Every removal is written to a durable archive audit record with the time, entity, reason, stock/balance at removal, and originating command. The dashboard **Archives** page exposes these records; earlier removal ledger entries are backfilled during schema upgrade.
- Previously archived products and customers can be reactivated by adding them again.

#### 8. Safe Correction & Reversals
- Pending drafts can be cancelled at any time with zero side effects.
- Committed transactions can be reversed via explicit reversal entries (`Reversal`) preserving complete audit history.

---

## 3. Financial & Accounting Rules
1. **Separation of Pricing**:
   - `MRP`: Maximum Retail Price printed on packaging.
   - `SellingPrice`: Actual price charged to customers.
   - `PurchaseCost`: Actual wholesale/distributor cost paid by shopkeeper.
   - *Rule*: Never conflate MRP with purchase cost. Never claim profit margins unless purchase costs are recorded.
2. **Transaction Atomicity**:
   - Every balance or stock change MUST commit with its corresponding ledger row in a single SQLite transaction.
3. **Idempotency**:
   - Every pending command has a unique `command_id` / idempotency key. Duplicate submission returns the existing result without double-applying.

---

## 4. Non-Goals (Scope Boundaries)
- No multi-store / cloud synchronization in v2.0 (local-first SQLite).
- No barcode scanning or WhatsApp bot before core voice loop passes 100% safety checks.
- No autonomous supplier reordering.
