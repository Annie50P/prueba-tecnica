"""
Router for /analytics endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Query
from api.services import graphiti_service as svc

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/promesas-incumplidas", summary="List unfulfilled promises")
def promesas_incumplidas(
    fecha: Optional[str] = Query(
        default=None,
        description="Filter promises with fecha_promesa <= this date (YYYY-MM-DD)",
    )
):
    """
    Return PromesaPago nodes where cumplida is False.
    Optionally filter by a cutoff date.
    """
    return svc.get_promesas_incumplidas(fecha=fecha)


@router.get("/mejores-horarios", summary="Best call time analysis")
def mejores_horarios(
    resultado: Optional[str] = Query(
        default="promesa_pago",
        description="Filter by interaction result type (e.g. promesa_pago)",
    )
):
    """
    Analyze which hours of the day yield the best call outcomes.
    """
    return svc.get_mejores_horarios(resultado=resultado)


@router.get("/dashboard", summary="High-level KPI dashboard")
def dashboard():
    """
    Return aggregated KPIs:
    - total_deuda_inicial
    - total_recuperado
    - tasa_recuperacion
    - promesas_cumplidas / promesas_incumplidas
    - distribucion_tipos_deuda
    - actividad_por_dia
    """
    return svc.get_dashboard()
