"""
Call Pattern Analyzer - FastAPI Application Entry Point.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Or from the project root:
    uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import clientes, agentes, analytics, analytics_avanzado, grafo, mcp_query

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API for the Call Pattern Analyzer. "
        "Reads from a local SQLite graph database and exposes endpoints "
        "for clients, agents, analytics, graph visualization, and MCP queries."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(clientes.router)
app.include_router(agentes.router)
app.include_router(analytics.router)
app.include_router(analytics_avanzado.router)
app.include_router(grafo.router)
app.include_router(mcp_query.router)

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"], summary="Health check")
def health():
    """Simple liveness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


@app.get("/", tags=["Root"], include_in_schema=False)
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
