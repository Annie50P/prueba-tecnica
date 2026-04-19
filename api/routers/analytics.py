"""
Router for /analytics endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Query
from api.services import graphiti_service as svc
from api.services import graphiti_search_service as search_svc

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/promesas-incumplidas", summary="List unfulfilled promises")
async def promesas_incumplidas(
    fecha: Optional[str] = Query(
        default=None,
        description="Filter promises with fecha_promesa <= this date (YYYY-MM-DD)",
    )
):
    return await svc.get_promesas_incumplidas(fecha=fecha)


@router.get("/mejores-horarios", summary="Best call time analysis")
async def mejores_horarios(
    resultado: Optional[str] = Query(
        default="promesa_pago",
        description="Filter by interaction result type (e.g. promesa_pago)",
    )
):
    return await svc.get_mejores_horarios(resultado=resultado)


@router.get("/dashboard", summary="High-level KPI dashboard")
async def dashboard():
    return await svc.get_dashboard()


@router.get(
    "/busqueda-semantica",
    summary="Búsqueda semántica en el knowledge graph de Graphiti",
    description=(
        "Busca hechos extraídos por Graphiti mediante LLM de los episodios de interacción. "
        "Requiere Neo4j activo y LLM configurado (ANTHROPIC_API_KEY / OPENAI_API_KEY) "
        "durante la ingesta. Permite filtrado temporal con `fecha`."
    ),
)
async def busqueda_semantica(
    q: str = Query(..., min_length=3, max_length=300, description="Consulta en lenguaje natural"),
    n: int = Query(default=10, ge=1, le=50, description="Número máximo de resultados"),
    fecha: Optional[str] = Query(
        default=None,
        description="Fecha de referencia temporal (YYYY-MM-DD) para filtrar hechos válidos",
    ),
):
    return await search_svc.busqueda_semantica(query=q, num_results=n, fecha_ref=fecha)
