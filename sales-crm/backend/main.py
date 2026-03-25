"""
Sales CRM – FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from database import engine, Base
import models  # noqa: F401 – ensure all models are registered before create_all

from routers import accounts, contacts, leads, projects, stakeholders, emails, sales_cycle

# ── Bootstrap ──────────────────────────────────────────────────────────────────

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sales CRM",
    description=(
        "A full-featured Sales CRM with automatic lead/contact/project management, "
        "email thread mapping, LinkedIn stakeholder profiling, and sales cycle tracking."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(accounts.router,     prefix="/api/v1")
app.include_router(contacts.router,     prefix="/api/v1")
app.include_router(leads.router,        prefix="/api/v1")
app.include_router(projects.router,     prefix="/api/v1")
app.include_router(stakeholders.router, prefix="/api/v1")
app.include_router(emails.router,       prefix="/api/v1")
app.include_router(sales_cycle.router,  prefix="/api/v1")

# ── Serve frontend static files ────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


# ── Entry point (used by Replit / direct python main.py) ───────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
