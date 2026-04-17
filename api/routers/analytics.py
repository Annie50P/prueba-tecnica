"""
Router for /analytics endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Query
from api.services import graphiti_service as svc

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
