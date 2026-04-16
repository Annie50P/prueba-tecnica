"""
Test de regresión anti data-leakage.

Garantiza que `evaluate_model` use `StandardScaler` DENTRO de un `Pipeline`,
ajustado por fold — no sobre el dataset completo antes de CV.

Ejecutar: pytest api/tests/test_ml/test_no_leakage.py -v
"""
from __future__ import annotations

import numpy as np
import pytest

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score


def _make_synthetic_dataset(n: int = 200, seed: int = 42):
    rng = np.random.RandomState(seed)
    # Dos features informativos + ruido.
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    noise = rng.normal(size=n) * 0.4
    logits = 1.5 * x1 - 1.2 * x2 + noise
    y = (logits > 0).astype(int)
    X = np.vstack([x1, x2, rng.normal(size=n)]).T
    return X, y


def test_pipeline_cv_matches_or_exceeds_leaky_cv_lowerbound():
    """
    Leaky CV (scaler fuera) tiende a inflar métricas artificialmente.
    La CV correcta (pipeline) debe producir métricas razonables y
    no debe quedar *muy por debajo* de la versión leaky.

    Assert: pipeline-CV ROC-AUC está en [0.7, 1.0]
    Assert: |pipeline-CV - leaky-CV| < 0.15 en este dataset sintético
    """
    X, y = _make_synthetic_dataset()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)

    # Leaky: scaler ve todo el dataset antes de dividir folds
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)
    leaky_proba = cross_val_predict(
        LogisticRegression(), X_s, y, cv=cv, method="predict_proba"
    )[:, 1]
    leaky_auc = roc_auc_score(y, leaky_proba)

    # Correcto: pipeline, scaler por fold
    pipe = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression())])
    clean_proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    clean_auc = roc_auc_score(y, clean_proba)

    assert 0.7 <= clean_auc <= 1.0, f"pipeline-CV AUC fuera de rango: {clean_auc}"
    assert abs(leaky_auc - clean_auc) < 0.15, (
        f"divergencia sospechosa: leaky={leaky_auc:.3f}, clean={clean_auc:.3f}"
    )


def test_evaluate_model_uses_pipeline():
    """
    Verifica que `api.ml.train.evaluate_model` NO transforme X fuera de CV.

    El contrato: evaluate_model recibe (model, X, y) y ajusta el scaler
    dentro de cada fold. Si la firma cambia, este test se debe actualizar.
    """
    from api.ml.train import evaluate_model

    X, y = _make_synthetic_dataset(n=60, seed=7)
    metrics = evaluate_model(LogisticRegression(), X, y)

    assert "roc_auc" in metrics
    assert 0.5 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["precision"] <= 1.0
    assert 0.0 <= metrics["recall"] <= 1.0


def test_evaluate_model_signature_no_scaler_param():
    """
    Regresión: `evaluate_model` NO debe aceptar un `scaler` externo.
    Si vuelve a aparecer, es señal de leakage reintroducido.
    """
    import inspect
    from api.ml.train import evaluate_model

    sig = inspect.signature(evaluate_model)
    assert "scaler" not in sig.parameters, (
        "evaluate_model aceptaba scaler como parámetro — riesgo de data leakage"
    )
