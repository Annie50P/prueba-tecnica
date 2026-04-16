"""
train.py — Entrenamiento y comparación de modelos (GB, XGBoost, LightGBM).

Funciones expuestas:
  - compare_models(): compara modelos y retorna el mejor
  - build_model(): entrena un modelo específico
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    accuracy_score,
)

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover - opcional
    LGBMClassifier = None  # type: ignore[assignment]

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - opcional
    XGBClassifier = None  # type: ignore[assignment]

from .features import FEATURE_NAMES

logger = logging.getLogger(__name__)

# Por debajo de este n, isotonic calibration es ruidosa — usar sigmoid (Platt).
CALIBRATION_SIGMOID_N_THRESHOLD = 1000

# Modelos base para comparación (XGBoost/LightGBM opcionales)
_MODELS: dict[str, Any] = {
    "GradientBoosting": lambda: GradientBoostingClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    ),
}
if XGBClassifier is not None:
    _MODELS["XGBoost"] = lambda: XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        use_label_encoder=False,
        eval_metric="logloss",
        verbosity=0,
    )
if LGBMClassifier is not None:
    _MODELS["LightGBM"] = lambda: LGBMClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
        verbose=-1,
    )


def _heuristic_labels(X: np.ndarray) -> np.ndarray:
    """Labels heurísticos para fallback."""
    scores = np.zeros(len(X))
    scores += (X[:, 0] >= 0.4).astype(float)
    scores += (X[:, 8] >= 0.5).astype(float)
    scores += (X[:, 6] >= 0.45).astype(float)
    scores += (X[:, 2] < 60).astype(float)
    y = (scores >= 2).astype(int)
    if y.sum() == 0:
        y[np.argmin(X[:, 1])] = 1
    if y.sum() == len(y):
        y[np.argmax(X[:, 1])] = 0
    return y


def _get_cv_splits(y: np.ndarray) -> int:
    """Cantidad de folds para CV estratificado."""
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))
    return min(5, max(2, min(n_pos, n_neg)))


def evaluate_model(
    model,
    X: np.ndarray,
    y: np.ndarray,
) -> dict[str, float]:
    """
    Evalúa un modelo con métricas completas.

    ANTI DATA-LEAKAGE (B2): el StandardScaler se encapsula en un Pipeline
    y entra a cross_val_predict. Así el scaler se ajusta UNICAMENTE sobre
    cada fold de entrenamiento, nunca ve el fold de validación.
    """
    cv = StratifiedKFold(n_splits=_get_cv_splits(y), shuffle=True, random_state=42)
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", model)])

    y_pred = cross_val_predict(pipe, X, y, cv=cv)

    try:
        y_proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")
        if y_proba.ndim == 2 and y_proba.shape[1] > 1:
            y_proba = y_proba[:, 1]
        roc_auc = roc_auc_score(y, y_proba)
    except Exception:
        roc_auc = 0.5

    return {
        "precision": round(precision_score(y, y_pred, zero_division=0), 3),
        "recall": round(recall_score(y, y_pred, zero_division=0), 3),
        "f1": round(f1_score(y, y_pred, zero_division=0), 3),
        "roc_auc": round(roc_auc, 3),
        "accuracy": round(accuracy_score(y, y_pred), 3),
    }


def compare_models(X: np.ndarray, y_gt: np.ndarray | None) -> dict[str, Any]:
    """
    Compara GradientBoosting, XGBoost y LightGBM.
    Selecciona el mejor por ROC-AUC y retorna:
      - best_model: modelo ya entrenado con todos los datos
      - scaler: StandardScaler ajustado
      - comparison: métricas por modelo
      - model_info: metadata para frontend
    """
    # ── Validación de inputs ─────────────────────────────────────
    if X is None or len(X) == 0:
        raise ValueError("X está vacío")
    if X.shape[1] != len(FEATURE_NAMES):
        raise ValueError(
            f"X tiene {X.shape[1]} features, esperado {len(FEATURE_NAMES)}"
        )

    # ── Selección de labels ──────────────────────────────────
    if y_gt is None:
        y_labeled = _heuristic_labels(X)
        label_mode = "heuristic"
        logger.warning("train: sin ground truth, usando labels heurísticos")
    else:
        y_labeled = y_gt
        label_mode = "temporal_split"

        # Logging de distribución de labels
        n_pos = int(np.sum(y_labeled == 1))
        n_neg = int(np.sum(y_labeled == 0))
        logger.info(
            f"train: {n_pos} positivos, {n_neg} negativos (rate={n_pos / len(y_labeled):.2f})"
        )

    X_labeled = X
    n = len(y_labeled)

    results = []

    for name, model_factory in _MODELS.items():
        logger.info(f"train: evaluando {name}...")
        model = model_factory()

        if n >= 10:
            metrics = evaluate_model(model, X_labeled, y_labeled)
        else:
            metrics = {
                "precision": 0,
                "recall": 0,
                "f1": 0,
                "roc_auc": 0,
                "accuracy": 0,
            }

        results.append(
            {
                "name": name,
                "metrics": metrics,
            }
        )

    comparison = sorted(results, key=lambda x: x["metrics"]["roc_auc"], reverse=True)
    best_name = comparison[0]["name"]
    best_metrics = comparison[0]["metrics"]

    logger.info(f"train: mejor modelo={best_name} (roc_auc={best_metrics['roc_auc']})")

    # Entrenar mejor modelo con todos los datos.
    # C7: para n < 1000 isotonic es ruidosa → sigmoid (Platt).
    best_model_factory = _MODELS[best_name]
    calibration_method = (
        "isotonic" if n >= CALIBRATION_SIGMOID_N_THRESHOLD else "sigmoid"
    )

    if n >= 10:
        n_cv = _get_cv_splits(y_labeled)
        model = CalibratedClassifierCV(
            best_model_factory(), method=calibration_method, cv=n_cv
        )
    else:
        model = best_model_factory()

    # Scaler final exclusivo del artifact (no compartido con CV).
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_labeled)
    model.fit(X_scaled, y_labeled)

    # Feature importances (manejar CalibratedClassifierCV wrapper)
    try:
        base = getattr(model, "estimator", model)
        importances = getattr(base, "feature_importances_", None)
        if importances is None:
            importances = np.ones(len(FEATURE_NAMES)) / len(FEATURE_NAMES)
    except Exception:
        importances = np.ones(len(FEATURE_NAMES)) / len(FEATURE_NAMES)

    importance_dict = {
        name: round(float(imp), 4)
        for name, imp in sorted(
            zip(FEATURE_NAMES, importances), key=lambda x: x[1], reverse=True
        )
    }

    # CV fold info — Pipeline garantiza scaler por fold (anti-leakage)
    cv_splits = _get_cv_splits(y_labeled)
    fold_scores = []
    if n >= 10 and cv_splits >= 2:
        cv = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=42)
        fold_pipe = Pipeline(
            [("scaler", StandardScaler()), ("clf", best_model_factory())]
        )
        fold_scores = list(
            cross_val_score(fold_pipe, X_labeled, y_labeled, cv=cv, scoring="roc_auc")
        )

    return {
        "best_model": model,
        "scaler": scaler,
        "label_mode": label_mode,
        "n_labeled": int(n),
        "comparison": comparison,
        "model_info": {
            "modelo": best_name,
            "calibration": calibration_method if n >= 10 else "none",
            "label_mode": label_mode,
            "n_labeled": int(n),
            "features": FEATURE_NAMES,
            "feature_importances": importance_dict,
            "cross_validation": {
                "folds": cv_splits,
                "roc_auc_mean": best_metrics["roc_auc"],
                "roc_auc_std": round(np.std(fold_scores), 3) if fold_scores else 0,
                "scores": [round(float(s), 3) for s in fold_scores],
            }
            if fold_scores
            else None,
            "metrics": {
                "precision": best_metrics["precision"],
                "recall": best_metrics["recall"],
                "f1": best_metrics["f1"],
                "roc_auc": best_metrics["roc_auc"],
                "accuracy": best_metrics["accuracy"],
            },
        },
    }


def build_model(
    model_name: str,
    X: np.ndarray,
    y: np.ndarray,
) -> tuple:
    """
    Entrena un modelo específico por nombre.
    Usado por model_registry para re-entrenamiento.
    """
    if model_name not in _MODELS:
        raise ValueError(f"Modelo desconocido: {model_name}")

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    if len(y) >= 10:
        n_cv = _get_cv_splits(y)
        method = (
            "isotonic" if len(y) >= CALIBRATION_SIGMOID_N_THRESHOLD else "sigmoid"
        )
        model = CalibratedClassifierCV(_MODELS[model_name](), method=method, cv=n_cv)
    else:
        model = _MODELS[model_name]()

    model.fit(X_s, y)
    return model, scaler


def run_cv_scoring(
    model_or_factory,
    X: np.ndarray,
    y: np.ndarray,
    scoring: str = "roc_auc",
) -> list[float]:
    """Cross-val scoring con Pipeline (anti-leakage)."""
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", model_or_factory)])
    cv = StratifiedKFold(n_splits=_get_cv_splits(y), shuffle=True, random_state=42)
    return list(cross_val_score(pipe, X, y, cv=cv, scoring=scoring))
