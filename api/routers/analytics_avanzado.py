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
def prediccion():
    """
    Returns a risk score (0-100) for each client based on:
    payment compliance, pending debt ratio, payment trends,
    sentiment analysis, and contact frequency.
    """
    return svc.get_prediccion_clientes()


@router.get("/anomalias", summary="Anomaly detection across all data")
def anomalias():
    """
    Detects unusual patterns: atypical payment amounts, promises exceeding
    debt, unusual contact hours, agents with atypical performance, and
    sudden sentiment changes.
    """
    return svc.get_anomalias()


@router.get("/estrategias", summary="Strategy optimization recommendations")
def estrategias():
    """
    Generates collection strategy recommendations: optimal contact hours,
    client segmentation (quick wins, high potential, critical cases),
    best agent assignments, and prioritization suggestions.
    """
    return svc.get_estrategias()
