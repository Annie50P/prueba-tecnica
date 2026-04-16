"""
Router for /clientes endpoints.
"""

from fastapi import APIRouter, HTTPException
from api.services import graphiti_service as svc

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", summary="List all clients with derived metrics")
def list_clientes():
    """
    Return all Cliente nodes with:
    - total_pagado
    - monto_pendiente
    - tasa_cumplimiento
    """
    return svc.get_all_clientes()


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
