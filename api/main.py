"""
Call Pattern Analyzer - FastAPI Application Entry Point.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Or from the project root:
    uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.ml import model_registry
from api.routers import clientes, agentes, analytics, analytics_avanzado, grafo, mcp_query

logger = logging.getLogger(__name__)

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
# CORS — spec-compliant:
#   * allow_credentials=True requires a concrete origins list (no wildcard).
#   * If cors_origins == ["*"] we disable credentials to stay valid.
# ---------------------------------------------------------------------------

_origins = settings.cors_origins or ["*"]
_allow_credentials = _origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup: precargar modelo ML persistido (si existe).
# Si no hay artefacto todavía, el primer request entrena on-demand con un
# lock en predictor.py (C8). Job offline: `python -m api.ml.train_offline`.
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def _startup() -> None:
    # Precargar modelo ML
    try:
        loaded = model_registry.load_latest()
        if loaded:
            logger.info("ml: loaded pre-trained model from %s", loaded)
        else:
            logger.info("ml: no pre-trained artifact; will train on first request")
    except Exception as exc:
        logger.warning("ml: failed to load persisted model: %s", exc)

    # Precalentar catálogo de tools MCP para que la primera consulta no espere
    try:
        from api.services.mcp_service import _build_tool_catalog
        catalog = await _build_tool_catalog()
        logger.info("mcp: tool catalog ready (%d tools)", len(catalog))
    except Exception as exc:
        logger.warning("mcp: tool catalog warmup failed: %s", exc)

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
