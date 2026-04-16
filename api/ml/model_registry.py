"""
model_registry.py — Versionado de modelos para producción.

Funcionalidades:
  - Registro de modelos entrenados con metadata
  - Tracking de versiones
  - Carga/descarga de modelos
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from .features import FEATURE_NAMES

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.path.dirname(__file__)).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

REGISTRY_FILE = MODEL_DIR / "registry.json"


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
    Registra un modelo entrenado.
    Retorna version_id (timestamp-based).
    """
    version_id = f"{model_name}_{int(time.time())}"
    registry = _load_registry()

    registry[version_id] = {
        "model_name": model_name,
        "timestamp": time.time(),
        "metrics": metrics,
        "n_samples": n_samples,
        "label_mode": label_mode,
        "features": FEATURE_NAMES,
    }

    _save_registry(registry)
    logger.info(f"model_registry: registrado {version_id}")
    return version_id


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
