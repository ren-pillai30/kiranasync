# KiranaSync Frontend

The React/Vite frontend provides the dashboard, voice controls, inventory and customer forms, transaction ledger, confirmation flows, selective TTS playback, and removal **Archives** page. The Flask API and application setup are documented in the [repository contributor guide](../CONTRIBUTING.md).

## Development

From this directory, install dependencies and start the Vite server:

```powershell
npm ci
npm run dev -- --host 127.0.0.1
```

Run the Flask backend separately from the repository root with `python -m backend.app.main`. Vite uses the local API at `http://127.0.0.1:5000`.

## Verification

```powershell
npm run build
npm run lint
```

The desktop overlay serves the compiled frontend from `frontend/dist`; rebuild after frontend changes before validating the overlay.
