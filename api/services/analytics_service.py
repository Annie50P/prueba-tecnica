"""
analytics_service.py — Orquestador de análisis ML de cobranza.

Delega la lógica de ML a los módulos en api/ml/:
  - api/ml/features.py      : feature engineering + ground-truth labels
  - api/ml/predictor.py     : GradientBoosting calibrado (artifact persistido)
  - api/ml/anomalies.py     : IsolationForest + LOF ensemble
  - api/ml/segmentation.py  : KMeans con k óptimo via silhouette

Acceso a datos 100 % via `api.repositories.get_backend()` (B1/C1).
"""
from __future__ import annotations

import logging
from typing import Any

from api.ml import predictor, anomalies, segmentation
from api.repositories import get_backend

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Data loader (shared across all 3 analyses)
# ─────────────────────────────────────────────────────────────────

async def _load_all_data() -> dict[str, Any]:
    backend = get_backend()

    clientes = {
        n["id"]: n["properties"] for n in await backend.get_nodes_by_label("Cliente")
    }
    agentes = {
        n["id"]: n["properties"] for n in await backend.get_nodes_by_label("Agente")
    }
    all_inters = [n["properties"] for n in await backend.get_nodes_by_label("Interaccion")]
    all_promesas = [
        n["properties"] for n in await backend.get_nodes_by_label("PromesaPago")
    ]
    all_pagos = [n["properties"] for n in await backend.get_nodes_by_label("Pago")]

    inters_by_client: dict[str, list] = {}
    for i in all_inters:
        cid = i.get("cliente_id", "")
        inters_by_client.setdefault(cid, []).append(i)

    promesas_by_client: dict[str, list] = {}
    for p in all_promesas:
        cid = p.get("cliente_id", "")
        promesas_by_client.setdefault(cid, []).append(p)

    pagos_by_client: dict[str, list] = {}
    for p in all_pagos:
        cid = p.get("cliente_id", "")
        pagos_by_client.setdefault(cid, []).append(p)

    return {
        "clientes": clientes,
        "agentes": agentes,
        "all_inters": all_inters,
        "all_promesas": all_promesas,
        "all_pagos": all_pagos,
        "inters_by_client": inters_by_client,
        "promesas_by_client": promesas_by_client,
        "pagos_by_client": pagos_by_client,
    }


# ─────────────────────────────────────────────────────────────────
# Funciones públicas — delegan a api/ml/
# ─────────────────────────────────────────────────────────────────

async def get_prediccion_clientes() -> list[dict]:
    data = await _load_all_data()
    return predictor.get_prediccion_clientes(data)


async def get_anomalias() -> dict:
    data = await _load_all_data()
    return anomalies.get_anomalias(data)


async def get_estrategias() -> dict:
    data = await _load_all_data()
    return segmentation.get_estrategias(data)
