# kiranasync

KiranaSync is a local-first voice-enabled inventory and customer credit (*udhaar*) dashboard for kirana shops.

## Hindi-English voice commands

Voice commands are transcribed by Gnani using its `en-IN` mode, which accepts mixed Hindi-English speech. If the English-script transcript has no recognizable quantity, the app also retries with Gnani's `hi-IN` mode. Gemini Flash-Lite then interprets both transcripts and extracts the action, product/customer, and whole-number quantity as structured JSON. The app validates these fields and performs all inventory and customer-balance changes locally; unclear commands or quantities are rejected without database changes.

The speech endpoint requires a valid `GNANI_API_KEY`; language understanding requires a valid `GEMINI_API_KEY`. Put both in the root `.env` file. The model defaults to `gemini-3.5-flash-lite`; set `GEMINI_MODEL` to override it. The API call sends the recognized transcript(s), inventory item names, and customer names to Google. For challenge demos, use synthetic data only and do not send real customer details or recorded calls. Google's unpaid Gemini service may use submitted content to improve its products; review the current API terms before using it with anything sensitive.

The dashboard transaction ledger keeps a timestamped history of sales, stock additions/restocks, and customer-credit entries, including the command or action details. Sales show a positive amount; restock costs show a negative amount calculated from the inventory item's current Price and the purchased quantity. Existing transaction tables are upgraded in place when the backend accesses them; previous records remain available.

When a spoken restock/new-product command names an item that is not in inventory, the app searches the web for MRP suggestions and opens a confirmation dialog with the item, quantity, prices, and result sources. Search retries common name variants and filters results against distinctive product-name words, ignoring generic item types such as "biscuit", so unrelated pages and prices are not displayed. Edit the name and search again to refresh its results. Select one or more price options, set the stock quantity for each, and confirm to add a separate inventory product for each selected MRP (the MRP is appended to each product name). You can also add an MRP manually. Search results are suggestions rather than verified live prices; check the product packaging/source before confirming.

If a sell/restock voice command matches multiple inventory variants of the same product, the app asks you to choose the exact item/MRP before changing stock.

## Additions, removals, and audit

Products and customers can be added or removed from the dashboard or through natural voice commands interpreted by Gemini. A credit entry for a new customer creates their customer record. Removing a product sets its active stock to zero, records a write-off, and preserves its transaction history. Removing a customer with an outstanding balance archives the account without discarding its balance or history; a zero-balance customer is deleted from the active customer table while ledger history remains.

Product removals require confirmation. Customer removals require confirmation when the balance is at least ₹1. Use **Archives** in the dashboard to review removal time, entity, action, reason, stock or balance at removal, and the originating command. Existing removal ledger entries are imported during the database upgrade.

Only stock and customer-balance query responses, removal confirmations/results, and new-product confirmation prompts/results are spoken. TTS uses the selected voice language; other command results remain on screen.

---

## Documentation & Developer Guide

- **Developer & Contributor Handbook**: [CONTRIBUTING.md](./CONTRIBUTING.md) (setup, voice flows, API contracts, testing, and Git workflow).
- **Architecture & System Design**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Product Specification & Trust Contract**: [PRODUCT_SPEC.md](./PRODUCT_SPEC.md)
- **Empirical Evaluation & Benchmark Report**: [EVALUATION_REPORT.md](./EVALUATION_REPORT.md)
- **Windows Packaging & Release**: [README_WINDOWS.md](./README_WINDOWS.md)
- **Build & Verification Status**: [BUILD_STATUS.md](./BUILD_STATUS.md)