"""
Regresión B3 — CUTOFF_DATE derivado de los datos, NO hardcodeado.

Si cambia la ventana temporal de los datos, `infer_cutoff_from_data` debe
producir un cutoff nuevo dentro del rango real (nada de 2025-07-16 fijo).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def _dataset_with_range(start: datetime, end: datetime, n: int = 40):
    """Genera un dict-like con interacciones distribuidas en [start, end]."""
    step = (end - start) / (n - 1)
    inters = [
        {
            "id": f"ix{i}",
            "timestamp": (start + step * i).isoformat(),
            "tipo": "llamada_saliente",
            "cliente_id": f"c{i % 5}",
        }
        for i in range(n)
    ]
    clientes = {f"c{i}": {"nombre": f"cli_{i}"} for i in range(5)}
    return {
        "clientes": clientes,
        "agentes": {},
        "all_inters": inters,
        "all_promesas": [],
        "all_pagos": [],
        "inters_by_client": {},
        "promesas_by_client": {},
        "pagos_by_client": {},
    }


def test_cutoff_inside_range_not_hardcoded():
    from api.ml.features import infer_cutoff_from_data

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 3, 1, tzinfo=timezone.utc)
    data = _dataset_with_range(start, end)

    cutoff, data_end = infer_cutoff_from_data(data)

    assert start <= cutoff <= end, f"cutoff {cutoff} fuera de rango"
    assert cutoff != datetime(2025, 7, 16, tzinfo=timezone.utc), (
        "cutoff sigue hardcodeado a 2025-07-16"
    )
    # data_end puede tener microsegundos por la división temporal; comparo al segundo.
    assert abs((data_end - end).total_seconds()) < 1


def test_cutoff_shifts_with_data():
    """Dos datasets distintos → dos cutoffs distintos (determinismo data-driven)."""
    from api.ml.features import infer_cutoff_from_data

    d1 = _dataset_with_range(
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    d2 = _dataset_with_range(
        datetime(2027, 1, 1, tzinfo=timezone.utc),
        datetime(2027, 6, 1, tzinfo=timezone.utc),
    )

    c1, _ = infer_cutoff_from_data(d1)
    c2, _ = infer_cutoff_from_data(d2)

    assert c1.year == 2025
    assert c2.year == 2027


def test_cutoff_fallback_on_empty_data():
    from api.ml.features import infer_cutoff_from_data, _DEFAULT_CUTOFF

    empty = {
        "all_inters": [],
        "all_pagos": [],
        "all_promesas": [],
    }
    cutoff, _ = infer_cutoff_from_data(empty)
    assert cutoff == _DEFAULT_CUTOFF
