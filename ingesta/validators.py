"""
Validates the raw JSON dataset for structural correctness and referential integrity.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from models import RawDataset


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_dataset(raw: Dict[str, Any]) -> Tuple[RawDataset, List[str]]:
    """Parse and validate the raw JSON dict.

    Returns:
        (RawDataset, warnings)  — raises ValueError on hard errors.
    """
    warnings: List[str] = []

    # ---- structural parse via Pydantic ----
    try:
        dataset = RawDataset.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"JSON structure validation failed: {exc}") from exc

    # ---- metadata counts ----
    if dataset.metadata.total_clientes != len(dataset.clientes):
        warnings.append(
            f"metadata.total_clientes={dataset.metadata.total_clientes} "
            f"but found {len(dataset.clientes)} clientes"
        )

    if dataset.metadata.total_interacciones != len(dataset.interacciones):
        warnings.append(
            f"metadata.total_interacciones={dataset.metadata.total_interacciones} "
            f"but found {len(dataset.interacciones)} interacciones"
        )

    # ---- referential integrity: every interaction must have a valid cliente_id ----
    cliente_ids = {c.id for c in dataset.clientes}
    missing_clients: List[str] = []
    for ix in dataset.interacciones:
        if ix.cliente_id not in cliente_ids:
            missing_clients.append(f"{ix.id} -> {ix.cliente_id}")

    if missing_clients:
        raise ValueError(
            f"Referential integrity error – {len(missing_clients)} interaction(s) "
            f"reference unknown clientes: {missing_clients[:10]}"
        )

    # ---- duplicate interaction IDs ----
    seen_ix_ids: Dict[str, int] = {}
    for ix in dataset.interacciones:
        seen_ix_ids[ix.id] = seen_ix_ids.get(ix.id, 0) + 1
    dupes = [k for k, v in seen_ix_ids.items() if v > 1]
    if dupes:
        warnings.append(f"Duplicate interaction ids found: {dupes}")

    # ---- duplicate cliente IDs ----
    seen_cl_ids: Dict[str, int] = {}
    for cl in dataset.clientes:
        seen_cl_ids[cl.id] = seen_cl_ids.get(cl.id, 0) + 1
    dupes_cl = [k for k, v in seen_cl_ids.items() if v > 1]
    if dupes_cl:
        warnings.append(f"Duplicate cliente ids found: {dupes_cl}")

    # ---- field-level checks for llamada interactions ----
    llamada_types = {"llamada_saliente", "llamada_entrante"}
    for ix in dataset.interacciones:
        if ix.tipo in llamada_types:
            if ix.agente_id is None:
                warnings.append(f"{ix.id}: llamada missing agente_id")
            if ix.resultado is None:
                warnings.append(f"{ix.id}: llamada missing resultado")
            if ix.duracion_segundos is None:
                warnings.append(f"{ix.id}: llamada missing duracion_segundos")

            if ix.resultado == "promesa_pago":
                if ix.monto_prometido is None:
                    warnings.append(f"{ix.id}: promesa_pago missing monto_prometido")
                if ix.fecha_promesa is None:
                    warnings.append(f"{ix.id}: promesa_pago missing fecha_promesa")

            if ix.resultado == "renegociacion":
                if ix.nuevo_plan_pago is None:
                    warnings.append(f"{ix.id}: renegociacion missing nuevo_plan_pago")

        if ix.tipo == "pago_recibido":
            if ix.monto is None:
                warnings.append(f"{ix.id}: pago_recibido missing monto")
            if ix.metodo_pago is None:
                warnings.append(f"{ix.id}: pago_recibido missing metodo_pago")
            if ix.pago_completo is None:
                warnings.append(f"{ix.id}: pago_recibido missing pago_completo")

    return dataset, warnings
