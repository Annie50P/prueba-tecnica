"""
analytics_service.py — Orquestador de análisis ML de cobranza.

Delega la lógica de ML a los módulos en api/ml/:
  - api/ml/features.py      : feature engineering (sentiment map corregido,
                              features RFM, ground-truth labels)
  - api/ml/predictor.py     : GradientBoosting calibrado, labels desde
                              outcomes reales, permutation importance
  - api/ml/anomalies.py     : IsolationForest+LOF ensemble, contamination
                              adaptivo, z-score univariado
  - api/ml/segmentation.py  : KMeans con k óptimo vía silhouette score,
                              perfiles de cluster data-driven

Este archivo mantiene la responsabilidad de:
  - Cargar los datos desde SQLite (_load_all_data)
  - Exponer las tres funciones públicas a los routers FastAPI
"""

import json
import logging
import sqlite3
import os

from api.ml import predictor, anomalies, segmentation

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ingesta",
    "local_graph.db",
)


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _props(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# ─────────────────────────────────────────────────────────────────
# Data loader (shared across all 3 analyses)
# ─────────────────────────────────────────────────────────────────

def _load_all_data():
    """Carga todos los datos relevantes del grafo en un solo pass."""
    conn = _conn()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id, properties FROM nodes WHERE label = 'Cliente'")
        clientes = {row["id"]: _props(row["properties"]) for row in cur.fetchall()}

        cur.execute("SELECT id, properties FROM nodes WHERE label = 'Interaccion'")
        all_inters = [_props(row["properties"]) for row in cur.fetchall()]

        cur.execute("SELECT id, properties FROM nodes WHERE label = 'PromesaPago'")
        all_promesas = [_props(row["properties"]) for row in cur.fetchall()]

        cur.execute("SELECT id, properties FROM nodes WHERE label = 'Pago'")
        all_pagos = [_props(row["properties"]) for row in cur.fetchall()]

        cur.execute("SELECT id, properties FROM nodes WHERE label = 'Agente'")
        agentes = {row["id"]: _props(row["properties"]) for row in cur.fetchall()}

        # Group by client
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
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────
# Funciones públicas — delegan a api/ml/
# ─────────────────────────────────────────────────────────────────

def get_prediccion_clientes() -> list[dict]:
    """Predicción de probabilidad de pago via GradientBoosting calibrado."""
    data = _load_all_data()
    return predictor.get_prediccion_clientes(data)


def get_anomalias() -> dict:
    """Anomalías via ensemble IsolationForest+LOF con contamination adaptivo."""
    data = _load_all_data()
    return anomalies.get_anomalias(data)


def get_estrategias() -> dict:
    """Segmentación con k óptimo vía silhouette + análisis de horas y agentes."""
    data = _load_all_data()
    return segmentation.get_estrategias(data)
