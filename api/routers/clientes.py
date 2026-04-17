"""
Router for /clientes endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from api.services import graphiti_service as svc

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", summary="List all clients with derived metrics")
async def list_clientes(
    limite: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    all_clientes = await svc.get_all_clientes()
    total = len(all_clientes)
    page = all_clientes[offset : offset + limite]
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "clientes": page,
    }


@router.get("/{cliente_id}", summary="Get full client detail")
async def get_cliente(cliente_id: str):
    cliente = await svc.get_cliente_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail=f"Cliente '{cliente_id}' not found")
    return cliente


@router.get("/{cliente_id}/timeline", summary="Get chronological interaction history")
async def get_timeline(cliente_id: str):
    timeline = await svc.get_cliente_timeline(cliente_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail=f"Cliente '{cliente_id}' not found")
    return {"cliente_id": cliente_id, "timeline": timeline}
