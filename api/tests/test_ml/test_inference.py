"""
Tests para el módulo inference.py - Predicciones.

Ejecutar con:
    cd api && python -m pytest tests/test_ml/test_inference.py -v
"""

import pytest
import numpy as np
from api.ml.inference import run_inference, explain


# Fixtures
@pytest.fixture
def model_info():
    """model_info de ejemplo."""
    np.random.seed(42)
    X = np.random.rand(10, 10)
    y = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1])

    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.calibration import CalibratedClassifierCV

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    model = GradientBoostingClassifier(n_estimators=5, max_depth=2, random_state=42)
    model.fit(X_s, y)

    return {"best_model": model, "scaler": scaler, "label_mode": "heuristic"}


@pytest.fixture
def client_ids():
    """Client IDs de ejemplo."""
    return [f"cliente_{i:03d}" for i in range(10)]


@pytest.fixture
def meta():
    """Meta de ejemplo."""
    return [{"nombre": f"Cliente {i}"} for i in range(10)]


@pytest.fixture
def X():
    """X de ejemplo."""
    np.random.seed(42)
    return np.random.rand(10, 10)


# Tests - run_inference
class TestRunInference:
    def test_run_inference(self, model_info, client_ids, meta, X):
        """run_inference retorna predicciones."""
        preds = run_inference(client_ids, X, meta, model_info)

        assert len(preds) == 10
        assert "cliente_id" in preds[0]
        assert "score_riesgo" in preds[0]
        assert "categoria_riesgo" in preds[0]
        assert "probabilidad_pago" in preds[0]

    def test_categoria_riesgo_values(self, model_info, client_ids, meta, X):
        """categoria_riesgo es válido."""
        preds = run_inference(client_ids, X, meta, model_info)

        for p in preds:
            assert p["categoria_riesgo"] in ("alto", "medio", "bajo")

    def test_score_riesgo_range(self, model_info, client_ids, meta, X):
        """score_riesgo está en rango 0-100."""
        preds = run_inference(client_ids, X, meta, model_info)

        for p in preds:
            assert 0 <= p["score_riesgo"] <= 100

    def test_probabilidad_pago_range(self, model_info, client_ids, meta, X):
        """probabilidad_pago está en rango 0-100."""
        preds = run_inference(client_ids, X, meta, model_info)

        for p in preds:
            assert 0 <= p["probabilidad_pago"] <= 100

    def test_factores_present(self, model_info, client_ids, meta, X):
        """factores está presente."""
        preds = run_inference(client_ids, X, meta, model_info)

        assert "factores" in preds[0]
        assert isinstance(preds[0]["factores"], list)

    def test_sorted_by_risk(self, model_info, client_ids, meta, X):
        """Predicciones ordenadas por score_riesgo."""
        preds = run_inference(client_ids, X, meta, model_info)

        scores = [p["score_riesgo"] for p in preds]
        assert scores == sorted(scores, reverse=True)

    def test_missing_model_raises(self, client_ids, meta, X):
        """Falta modelo lanza error."""
        with pytest.raises(ValueError, match="best_model"):
            run_inference(client_ids, X, meta, {})

    def test_missing_scaler_raises(self, client_ids, meta, X):
        """Falta scaler lanza error."""
        from sklearn.ensemble import GradientBoostingClassifier

        bad_info = {"best_model": GradientBoostingClassifier()}

        with pytest.raises(ValueError, match="scaler"):
            run_inference(client_ids, X, meta, bad_info)


class TestExplain:
    def test_explain_returns_list(self):
        """explain retorna lista."""
        X = np.array([0.1, 0.9, 30, 2, 100, 0.3, 0.5, 5, 0.5, 0.2])
        result = explain(X)

        assert isinstance(result, list)
        assert len(result) > 0

    def test_explain_strings(self):
        """explain retorna strings."""
        X = np.array([0.1, 0.9, 30, 2, 100, 0.3, 0.5, 5, 0.5, 0.2])
        result = explain(X)

        for r in result:
            assert isinstance(r, str)
