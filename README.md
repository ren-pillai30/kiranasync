# kiranasync

## Hindi-English voice commands

Voice commands are transcribed by Gnani using its `en-IN` mode, which accepts mixed Hindi-English speech. If the English-script transcript has no recognizable quantity, the app also retries with Gnani's `hi-IN` mode. Gemini Flash-Lite then interprets both transcripts and extracts the action, product/customer, and whole-number quantity as structured JSON. The app validates these fields and performs all inventory and customer-balance changes locally; unclear commands or quantities are rejected without database changes.

The speech endpoint requires a valid `GNANI_API_KEY`; language understanding requires a valid `GEMINI_API_KEY`. Put both in the root `.env` file. The model defaults to `gemini-3.5-flash-lite`; set `GEMINI_MODEL` to override it. The API call sends the recognized transcript(s), inventory item names, and customer names to Google. For challenge demos, use synthetic data only and do not send real customer details or recorded calls. Google's unpaid Gemini service may use submitted content to improve its products; review the current API terms before using it with anything sensitive.