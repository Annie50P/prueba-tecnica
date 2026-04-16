"""
Pydantic models for all graph entities in the call pattern analyzer.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Raw JSON models (mirror the JSON schema for validation)
# ---------------------------------------------------------------------------

class RawNuevoPlanPago(BaseModel):
    cuotas: int
    monto_mensual: float


class RawInteraccion(BaseModel):
    id: str
    cliente_id: str
    timestamp: str  # ISO-8601 string; keep as str for flexible parsing
    tipo: str

    # Llamada fields (optional)
    duracion_segundos: Optional[int] = None
    agente_id: Optional[str] = None
    resultado: Optional[str] = None
    sentimiento: Optional[str] = None

    # promesa_pago extras
    monto_prometido: Optional[float] = None
    fecha_promesa: Optional[str] = None  # YYYY-MM-DD

    # renegociacion extras
    nuevo_plan_pago: Optional[RawNuevoPlanPago] = None

    # pago_recibido extras
    monto: Optional[float] = None
    metodo_pago: Optional[str] = None
    pago_completo: Optional[bool] = None


class RawCliente(BaseModel):
    id: str
    nombre: str
    telefono: str
    monto_deuda_inicial: float
    fecha_prestamo: str  # YYYY-MM-DD
    tipo_deuda: str


class RawMetadata(BaseModel):
    fecha_generacion: str
    total_clientes: int
    total_interacciones: int
    periodo: str


class RawDataset(BaseModel):
    metadata: RawMetadata
    clientes: List[RawCliente]
    interacciones: List[RawInteraccion]


# ---------------------------------------------------------------------------
# Graph node models
# ---------------------------------------------------------------------------

class ClienteNode(BaseModel):
    """Graph node: Cliente"""
    id: str
    nombre: str
    telefono: str
    monto_deuda_inicial: float
    fecha_prestamo: str
    tipo_deuda: str
    # Derived
    total_pagado: float = 0.0
    monto_pendiente: float = 0.0
    tasa_cumplimiento: float = 0.0  # fraction 0-1


class AgenteNode(BaseModel):
    """Graph node: Agente"""
    id: str
    # Derived stats
    total_llamadas: int = 0
    tasa_promesa: float = 0.0        # fraction of calls that resulted in promesa_pago
    tasa_pago_inmediato: float = 0.0  # fraction of calls that resulted in pago_inmediato


class InteraccionNode(BaseModel):
    """Graph node: Interaccion"""
    id: str
    cliente_id: str
    timestamp: str
    tipo: str

    # Llamada fields
    duracion_segundos: Optional[int] = None
    agente_id: Optional[str] = None
    resultado: Optional[str] = None
    sentimiento: Optional[str] = None

    # Derived
    hora_del_dia: Optional[int] = None   # 0-23 UTC
    dia_semana: Optional[int] = None     # 0=Monday


class PromesaPagoNode(BaseModel):
    """Graph node: PromesaPago  (id = {interaccion_id}_promesa)

    Nota: `dias_hasta_vencimiento` NO se persiste (es función de la fecha actual).
    La API lo calcula on-read desde `fecha_promesa`.
    """
    id: str
    interaccion_id: str
    cliente_id: str
    monto_prometido: float
    fecha_promesa: str       # YYYY-MM-DD
    # Derived
    cumplida: bool = False


class PagoNode(BaseModel):
    """Graph node: Pago  (id = {interaccion_id}_pago)"""
    id: str
    interaccion_id: str
    cliente_id: str
    monto: float
    metodo_pago: str
    pago_completo: bool
    timestamp: str


class PlanPagoNode(BaseModel):
    """Graph node: PlanPago  (id = {interaccion_id}_plan)"""
    id: str
    interaccion_id: str
    cliente_id: str
    cuotas: int
    monto_mensual: float
    # Derived
    monto_total_plan: float = 0.0
    fecha_inicio: str = ""  # ISO timestamp of the parent interaction


# ---------------------------------------------------------------------------
# Relationship record
# ---------------------------------------------------------------------------

class RelationRecord(BaseModel):
    """Represents a directed relationship between two graph nodes."""
    from_id: str
    rel_type: str
    to_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
