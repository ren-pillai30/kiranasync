# KiranaSync 2.0 — Windows Desktop Installation & Setup

## 1. Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Microphone**: Working audio input for voice interaction
- **Internet Connection**: Required for Gnani Prisma STT, Gnani Timbre TTS, and NLU providers

---

## 2. API Credentials Configuration
Create a `.env` file in the application directory (or set environment variables on your system):

```env
# Gnani AI API Credentials (Prisma STT & Timbre TTS)
GNANI_API_KEY=your_gnani_api_key_here
GNANI_TTS_API_KEY=your_gnani_tts_api_key_here

# Reasoning / Language Model
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

> **Security Note**: Never commit your `.env` file to source control or share it in demo screenshots. The packaged desktop application reads configuration from local environment variables or the persistent directory `%LOCALAPPDATA%\KiranaSync\.env`.

---

## 3. Running from Source

### 1. Backend Setup
```powershell
cd backend
pip install -r requirements.txt
python -m app.main
```

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

### 3. Desktop Overlay Mode (Frameless PyWebView HUD)
```powershell
python overlay.py
```
- **Hotkeys**:
  - `Ctrl + Shift + V`: Trigger voice recognition
  - `Ctrl + Shift + D`: Toggle full management dashboard

Stock and customer udhaar/balance query answers, removal confirmations/results, and new-product confirmation prompts/results are spoken aloud. Gemini translates speech text into the language selected by the English/Hindi display toggle, and Gnani TTS synthesizes it in that language. Other command results are shown on screen without voice playback. The **Voice ON / Muted** button controls whether these responses are spoken.

You can add and remove products or customers with the dashboard controls or by speaking naturally. Gemini interprets voice requests such as adding a product/customer or removing a recalled/expired product/customer. Adding an amount to a customer's account creates that customer in the table if they are not already present; a repayment is recognized only when the customer is paying the shopkeeper. Product removals require confirmation; customer removals require confirmation when the outstanding balance is ₹1 or more, and are handled directly below ₹1. A removed zero-balance customer is deleted from the customer table (their transaction history is retained); a non-zero balance and customer history are retained in an archived record. Removing a product archives it, sets remaining stock to zero, and records a write-off while retaining transaction history. Adding a previously archived product or customer reactivates its record.

Open **Archives** from the dashboard to review the audit trail for removed products and customers, including when removed, reason, stock/balance at removal, and originating command. Existing removal transactions are imported into the audit list when the backend first upgrades the database.

---

## 4. Building the Windows Desktop Package
To create a standalone Windows distribution bundle:
```powershell
.\build_windows.ps1
```
The resulting executable and bundled runtime assets will be generated in `dist/KiranaSync/`.

---

## 5. Verification & Testing
Run the backend unit and integration tests offline without spending API credits:
```powershell
python -m unittest discover -s backend/tests -v
```
To run the automated benchmark evaluation:
```powershell
python -c "from backend.app.evaluation.runner import EvaluationRunner; print(EvaluationRunner().run_benchmark())"
```
