import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.wsgi import WSGIMiddleware

# Import existing Flask app
from backend.app.main import app as flask_app
# Import new Call Simulator router
from backend.app.routers.call_router import router as call_router

app = FastAPI(
    title="KiranaSync Voice & Call AI",
    description="Enterprise Kirana store assistant with voice commands and virtual call simulation",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Mount new WebSocket and Call Simulator endpoints
app.include_router(call_router)

# 2. Mount existing Flask application at root so all existing REST endpoints and dist files remain intact
app.mount("/", WSGIMiddleware(flask_app))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.asgi:app", host="127.0.0.1", port=5000, reload=True)

