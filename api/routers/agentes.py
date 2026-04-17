"""
Router for /agentes endpoints.
"""

from fastapi import APIRouter, HTTPException
from api.services import graphiti_service as svc

router = APIRouter(prefix="/agentes", tags=["Agentes"])


@router.get("", summary="List all agents with aggregate metrics")
async def list_agentes():
    return await svc.get_all_agentes()


@router.get("/{agente_id}/efectividad", summary="Get agent performance metrics")
async def get_efectividad(agente_id: str):
    efectividad = await svc.get_agente_efectividad(agente_id)
    if efectividad is None:
        raise HTTPException(status_code=404, detail=f"Agente '{agente_id}' not found")
    return efectividad
