"""
model_registry.py — Versionado y persistencia de modelos ML.

Funcionalidades:
  - Persistencia de artifact (model + scaler) vía joblib
  - Tracking de versiones en registry.json
  - Carga del modelo más reciente al startup de la API
  - In-memory cache del artifact actual (un único load para todos los requests)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import joblib

from .features import FEATURE_NAMES

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent / "artifacts"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_FILE = MODEL_DIR / "registry.json"

# In-memory cache del artifact cargado (model + scaler + metadata).
# Se popula al startup (main.py:_load_ml_model) y, si no hay artifact,
# tras el primer entrenamiento on-demand.
_ARTIFACT: dict[str, Any] | None = None
_ARTIFACT_LOCK = threading.Lock()


def _load_registry() -> dict[str, Any]:
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {}


def _save_registry(registry: dict[str, Any]) -> None:
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


def register_model(
    model_name: str,
    model: Any,
    scaler: Any,
    metrics: dict[str, float],
    n_samples: int,
    label_mode: str,
) -> str:
    """
    Registra un modelo entrenado y persiste el artifact (model+scaler) a disco.
    Retorna version_id (timestamp-based).
    """
    version_id = f"{model_name}_{int(time.time())}"
    artifact_path = MODEL_DIR / f"{version_id}.joblib"

    joblib.dump(
        {
            "model": model,
            "scaler": scaler,
            "feature_names": FEATURE_NAMES,
            "label_mode": label_mode,
        },
        artifact_path,
    )

    registry = _load_registry()
    registry[version_id] = {
        "model_name": model_name,
        "timestamp": time.time(),
        "metrics": metrics,
        "n_samples": n_samples,
        "label_mode": label_mode,
        "features": FEATURE_NAMES,
        "artifact": str(artifact_path.name),
    }
    _save_registry(registry)

    # Update in-memory cache
    global _ARTIFACT
    with _ARTIFACT_LOCK:
        _ARTIFACT = {
            "version_id": version_id,
            "model": model,
            "scaler": scaler,
            "label_mode": label_mode,
            "metrics": metrics,
        }

    logger.info("model_registry: registrado %s → %s", version_id, artifact_path)
    return version_id


def load_latest() -> str | None:
    """
    Carga el artifact del modelo más reciente a memoria.
    Retorna el version_id cargado, o None si no hay ninguno.
    """
    global _ARTIFACT
    latest = get_latest_model()
    if not latest:
        return None

    artifact_name = latest.get("artifact")
    if not artifact_name:
        return None  # registro antiguo sin artifact persistido

    path = MODEL_DIR / artifact_name
    if not path.exists():
        logger.warning("model_registry: artifact ausente en disco: %s", path)
        return None

    blob = joblib.load(path)
    with _ARTIFACT_LOCK:
        _ARTIFACT = {
            "version_id": latest["version_id"],
            "model": blob["model"],
            "scaler": blob["scaler"],
            "label_mode": blob.get("label_mode", latest.get("label_mode", "unknown")),
            "metrics": latest.get("metrics", {}),
        }
    return latest["version_id"]


def get_loaded_artifact() -> dict[str, Any] | None:
    """Retorna el artifact actualmente cargado en memoria (o None)."""
    with _ARTIFACT_LOCK:
        return dict(_ARTIFACT) if _ARTIFACT is not None else None


def list_models() -> list[dict[str, Any]]:
    """Lista todos los modelos registrados."""
    registry = _load_registry()
    return [
        {**info, "version_id": vid}
        for vid, info in sorted(
            registry.items(), key=lambda x: x[1].get("timestamp", 0), reverse=True
        )
    ]


def get_latest_model() -> dict[str, Any] | None:
    """Obtiene el modelo más reciente."""
    models = list_models()
    return models[0] if models else None


def get_model_info(version_id: str) -> dict[str, Any] | None:
    """Obtiene metadata de un modelo específico."""
    registry = _load_registry()
    return registry.get(version_id)


def validate_label_distribution(y) -> dict[str, Any]:
    """
    Valida distribución de labels para evitar sesgo.
    Retorna dict con validación y advertencias.
    """
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    total = n_pos + n_neg

    if total == 0:
        return {"valid": False, "reason": "sin labels"}

    ratio = n_pos / total

    advertencias = []
    if ratio < 0.2:
        advertencias.append("desbalance severo (pocos positivos)")
    elif ratio > 0.8:
        advertencias.append("desbalance severo (pocos negativos)")

    return {
        "valid": total >= 100 or len(advertencias) == 0,
        "n_positivos": n_pos,
        "n_negativos": n_neg,
        "ratio_positivos": round(ratio, 3),
        "advertencias": advertencias,
    }
