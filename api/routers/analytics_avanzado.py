"""
Router for bonus analytics endpoints:
  - /analytics/prediccion    — Risk scoring per client
  - /analytics/anomalias     — Anomaly detection
  - /analytics/estrategias   — Strategy optimization recommendations
"""

from fastapi import APIRouter
from api.services import analytics_service as svc

router = APIRouter(prefix="/analytics", tags=["Analytics Avanzado"])


@router.get("/prediccion", summary="Predictive risk analysis per client")
async def prediccion():
    return await svc.get_prediccion_clientes()


@router.get("/anomalias", summary="Anomaly detection across all data")
async def anomalias():
    return await svc.get_anomalias()


@router.get("/estrategias", summary="Strategy optimization recommendations")
async def estrategias():
    return await svc.get_estrategias()
