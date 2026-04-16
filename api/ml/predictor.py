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

import threading
import time
import logging
from datetime import datetime, timezone
from typing import Any

from . import model_registry
from .features import build_feature_matrix

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300
_CACHE_LOCK = threading.Lock()
# Singleflight: si hay entrenamiento en curso, el resto espera — no retraining en tormenta.
_TRAIN_LOCK = threading.Lock()


def _cache_get(key: str) -> Any | None:
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and (time.monotonic() - entry["ts"]) < _CACHE_TTL_SECONDS:
            return entry["value"]
    return None


def _cache_set(key: str, value: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = {"ts": time.monotonic(), "value": value}


def _model_info_from_artifact(artifact: dict) -> dict:
    return {
        "best_model": artifact["model"],
        "scaler": artifact["scaler"],
        "label_mode": artifact.get("label_mode", "persisted"),
    }


def get_prediccion_clientes(data: dict) -> list[dict]:
    """
    Retorna predicciones:
      1. Si hay artifact persistido → usar ese (load una vez al startup).
      2. Si no hay artifact → entrenar on-demand bajo lock y registrar.
      3. Cachear el resultado final por TTL para evitar recomputar features.
    """
    cached = _cache_get("prediccion")
    if cached is not None:
        logger.debug("prediccion: cache hit")
        return cached

    from .inference import run_inference

    client_ids, X, meta, y_gt = build_feature_matrix(data)
    if len(client_ids) < 5:
        return []

    artifact = model_registry.get_loaded_artifact()

    if artifact is None:
        # Fallback: entrenar on-demand bajo singleflight lock (C8).
        with _TRAIN_LOCK:
            artifact = model_registry.get_loaded_artifact()
            if artifact is None:
                from .train import compare_models

                logger.warning(
                    "prediccion: sin artifact persistido; entrenando on-demand (considera "
                    "correr `python -m api.ml.train_offline`)"
                )
                comparison = compare_models(X, y_gt)
                model_registry.register_model(
                    model_name=comparison["model_info"]["modelo"],
                    model=comparison["best_model"],
                    scaler=comparison["scaler"],
                    metrics=comparison["model_info"]["metrics"],
                    n_samples=comparison["n_labeled"],
                    label_mode=comparison["label_mode"],
                )
                artifact = model_registry.get_loaded_artifact()

    model_info = _model_info_from_artifact(artifact)
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
        results[0]["_modelo"] = {
            "modelo": artifact.get("version_id", "unknown"),
            "label_mode": artifact.get("label_mode", "unknown"),
            "metrics": artifact.get("metrics", {}),
        }
        results[0]["_timestamp"] = datetime.now(timezone.utc).isoformat()

    _cache_set("prediccion", results)
    return results
