"""
Router for /agentes endpoints.
"""

from fastapi import APIRouter, HTTPException
from api.services import graphiti_service as svc

router = APIRouter(prefix="/agentes", tags=["Agentes"])


@router.get("", summary="List all agents with aggregate metrics")
def list_agentes():
    """
    Return all Agente nodes with:
    - total_llamadas
    - tasa_promesa
    - tasa_pago_inmediato
    """
    return svc.get_all_agentes()


@router.get("/{agente_id}/efectividad", summary="Get agent performance metrics")
def get_efectividad(agente_id: str):
    """
    Return detailed effectiveness metrics for an agent:
    - total_llamadas
    - tasa_promesa
    - tasa_pago_inmediato
    - distribucion_resultados
    - distribucion_sentimientos
    - mejor_horario
    """
    efectividad = svc.get_agente_efectividad(agente_id)
    if efectividad is None:
        raise HTTPException(status_code=404, detail=f"Agente '{agente_id}' not found")
    return efectividad
