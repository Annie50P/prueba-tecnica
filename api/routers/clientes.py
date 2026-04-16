"""
Router for /clientes endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from api.services import graphiti_service as svc

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", summary="List all clients with derived metrics")
def list_clientes(
    limite: int = Query(default=100, ge=1, le=1000, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """
    Return Cliente nodes (paginados) con:
    - total_pagado
    - monto_pendiente
    - tasa_cumplimiento
    """
    all_clientes = svc.get_all_clientes()
    total = len(all_clientes)
    page = all_clientes[offset : offset + limite]
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "clientes": page,
    }


@router.get("/{cliente_id}", summary="Get full client detail")
def get_cliente(cliente_id: str):
    """
    Return all data for a single client, including linked interactions,
    promises, and payments.
    """
    cliente = svc.get_cliente_by_id(cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail=f"Cliente '{cliente_id}' not found")
    return cliente


@router.get("/{cliente_id}/timeline", summary="Get chronological interaction history")
def get_timeline(cliente_id: str):
    """
    Return interactions for a client sorted chronologically,
    with linked promises, payments and payment plans.
    """
    timeline = svc.get_cliente_timeline(cliente_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail=f"Cliente '{cliente_id}' not found")
    return {"cliente_id": cliente_id, "timeline": timeline}
