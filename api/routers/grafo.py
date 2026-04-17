"""
Router for /grafo endpoints used by D3.js visualization.
"""

from typing import Optional
from fastapi import APIRouter, Query
from api.services import graphiti_service as svc

router = APIRouter(prefix="/grafo", tags=["Grafo"])

VALID_LABELS = {"Cliente", "Agente", "Interaccion", "PromesaPago", "Pago", "PlanPago"}


@router.get("/nodos", summary="Get graph nodes for D3.js")
async def get_nodos(
    tipos: Optional[list[str]] = Query(
        default=None,
        description="Node type filter — repeat for multiple: ?tipos=Cliente&tipos=Agente",
    ),
    limite: int = Query(default=800, ge=1, le=2000, description="Maximum number of nodes"),
):
    tipos_validos = [t for t in tipos if t in VALID_LABELS] if tipos else None
    return await svc.get_grafo_nodos(tipos=tipos_validos or None, limite=limite)


@router.get("/relaciones", summary="Get graph relationships for D3.js")
async def get_relaciones(
    cliente_id: Optional[str] = Query(
        default=None, description="Filter relationships connected to this client's subgraph"
    ),
    tipos_relacion: Optional[list[str]] = Query(
        default=None,
        description="Filter by relationship types — repeat for multiple: ?tipos_relacion=TIENE_INTERACCION&tipos_relacion=CONDUJO",
    ),
    profundidad: int = Query(
        default=2, ge=1, le=3, description="Subgraph depth (hops) when filtering by client"
    ),
):
    return await svc.get_grafo_relaciones(
        cliente_id=cliente_id,
        tipos_relacion=tipos_relacion or None,
        profundidad=profundidad,
    )
