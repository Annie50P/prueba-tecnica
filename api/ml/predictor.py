"""
predictor.py — Módulo de predicción de pago con comparación de modelos.

Este archivo_delega a:
  - train.py    : entrenamiento y comparación de modelos (GB, XGBoost, LightGBM)
  - inference.py: predicciones con el mejor modelo

Responsabilidades de este archivo:
  - cacheo de resultados
  - exposed función pública get_prediccion_clientes()
"""

from __future__ import annotations

import time
import logging
from datetime import datetime, timezone
from typing import Any

from .features import build_feature_matrix

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300


def _cache_get(key: str) -> Any | None:
    entry = _CACHE.get(key)
    if entry and (time.monotonic() - entry["ts"]) < _CACHE_TTL_SECONDS:
        return entry["value"]
    return None


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = {"ts": time.monotonic(), "value": value}


def get_prediccion_clientes(data: dict) -> list[dict]:
    """
    Retorna predicciones delegando a inference.py.
    Usa cache para evitar re-entrenamiento en cada request.
    """
    cached = _cache_get("prediccion")
    if cached is not None:
        logger.debug("prediccion: cache hit")
        return cached

    from .inference import run_inference
    from .train import compare_models

    client_ids, X, meta, y_gt = build_feature_matrix(data)

    if len(client_ids) < 5:
        return []

    comparison = compare_models(X, y_gt)
    model_info = {
        "best_model": comparison["best_model"],
        "scaler": comparison["scaler"],
        "label_mode": comparison["label_mode"],
    }
    predictions = run_inference(client_ids, X, meta, model_info)

    results = []
    for i, pred in enumerate(predictions):
        results.append(
            {
                "cliente_id": pred["cliente_id"],
                "nombre": meta[i]["nombre"],
                "score_riesgo": pred["score_riesgo"],
                "categoria_riesgo": pred["categoria_riesgo"],
                "probabilidad_pago": pred["probabilidad_pago"],
                "label_mode": pred["label_mode"],
                "label_observado": meta[i].get("label_observado"),
                "factores": pred["factores"],
                "metricas": meta[i],
            }
        )

    if results:
        results[0]["_modelo"] = comparison["model_info"]
        results[0]["_timestamp"] = datetime.now(timezone.utc).isoformat()

    _cache_set("prediccion", results)
    return results
