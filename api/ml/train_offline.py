"""
train_offline.py — Job de entrenamiento fuera del request path.

Uso:
    python -m api.ml.train_offline

Este script:
  1. Carga datos via api.services.analytics_service._load_all_data (por ahora
     SQLite; cuando se cablee Graphiti real, mismo path).
  2. Construye features con cutoff temporal derivado de los datos.
  3. Compara GB / XGBoost / LightGBM con CV anti-leakage (Pipeline).
  4. Persiste el mejor artifact (model + scaler) via model_registry.
  5. Deja el modelo listo para ser load_latest() al startup de la API.

En producción conectar a cron/Airflow/Celery beat (diario o semanal).
"""
from __future__ import annotations

import logging
import sys

from api.ml import model_registry
from api.ml.features import build_feature_matrix, infer_cutoff_from_data
from api.ml.train import compare_models
from api.services.analytics_service import _load_all_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("train_offline")


def main() -> int:
    logger.info("train_offline: cargando datos ...")
    data = _load_all_data()

    cutoff, data_end = infer_cutoff_from_data(data)
    logger.info(
        "train_offline: cutoff=%s, data_end=%s",
        cutoff.date().isoformat(),
        data_end.date().isoformat(),
    )

    client_ids, X, meta, y_gt = build_feature_matrix(data, cutoff_date=cutoff)
    if len(client_ids) < 5:
        logger.error("train_offline: insuficientes clientes (%d)", len(client_ids))
        return 2

    logger.info("train_offline: X=%s, y=%s", X.shape, None if y_gt is None else y_gt.shape)

    result = compare_models(X, y_gt)

    version_id = model_registry.register_model(
        model_name=result["model_info"]["modelo"],
        model=result["best_model"],
        scaler=result["scaler"],
        metrics=result["model_info"]["metrics"],
        n_samples=result["n_labeled"],
        label_mode=result["label_mode"],
    )

    logger.info("train_offline: OK → %s", version_id)
    logger.info("train_offline: métricas %s", result["model_info"]["metrics"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
