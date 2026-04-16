"""
Tests para el módulo train.py - Entrenamiento y comparación de modelos.

Ejecutar con:
    cd api && python -m pytest tests/test_ml/test_train.py -v
"""

import pytest
import numpy as np
from api.ml.train import (
    compare_models,
    build_model,
)


# Fixtures
@pytest.fixture
def X_blanco():
    """X vacío."""
    return np.array([])


@pytest.fixture
def X_few_rows():
    """X con pocas filas."""
    return np.random.rand(3, 10)


@pytest.fixture
def X_normal():
    """X normal para testing."""
    np.random.seed(42)
    return np.random.rand(50, 10)


@pytest.fixture
def y_none():
    """y None (sin labels)."""
    return None


@pytest.fixture
def y_ground_truth():
    """y con ground truth."""
    return np.array(
        [
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            -1,
            -1,
            -1,
            -1,
            -1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            0,
            0,
            0,
            -1,
            -1,
            -1,
            -1,
            -1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
            1,
        ]
    )


# Tests - compare_models
class TestCompareModels:
    def test_X_vacio(self, X_blanco):
        """Debe fallar con X vacío."""
        with pytest.raises(ValueError, match="X está vacío"):
            compare_models(X_blanco, None)

    def test_X_wrong_features(self, X_few_rows):
        """Debe fallar con número incorrecto de features."""
        with pytest.raises(ValueError, match="features"):
            compare_models(X_few_rows, None)

    def test_retorna_dict(self, X_normal, y_none):
        """Retorna diccionario con fields requeridos."""
        result = compare_models(X_normal, y_none)

        assert "best_model" in result
        assert "scaler" in result
        assert "label_mode" in result
        assert "model_info" in result
        assert "comparison" in result

    def test_comparison_3_models(self, X_normal, y_none):
        """comparison tiene 3 modelos."""
        result = compare_models(X_normal, y_none)

        assert len(result["comparison"]) == 3
        names = [m["name"] for m in result["comparison"]]
        assert "GradientBoosting" in names
        assert "XGBoost" in names
        assert "LightGBM" in names

    def test_ground_truth_mode(self, X_normal, y_ground_truth):
        """Con ground truth usa label_mode=ground_truth."""
        result = compare_models(X_normal, y_ground_truth)

        assert result["label_mode"] in ("ground_truth", "heuristic")

    def test_model_info_complete(self, X_normal, y_none):
        """model_info tiene todos los campos."""
        result = compare_models(X_normal, y_none)
        info = result["model_info"]

        assert "modelo" in info
        assert "calibration" in info
        assert "features" in info
        assert "metrics" in info

    def test_metrics_presence(self, X_normal, y_none):
        """metrics tiene métricas completas."""
        result = compare_models(X_normal, y_none)
        metrics = result["model_info"]["metrics"]

        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "roc_auc" in metrics
        assert "accuracy" in metrics

    def test_metrics_in_range(self, X_normal, y_none):
        """Métricas están en rango válido."""
        result = compare_models(X_normal, y_none)
        metrics = result["model_info"]["metrics"]

        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1"] <= 1
        assert 0 <= metrics["roc_auc"] <= 1
        assert 0 <= metrics["accuracy"] <= 1


class TestBuildModel:
    def test_unknown_model(self, X_normal):
        """Debe fallar con modelo desconocido."""
        with pytest.raises(ValueError, match="Modelo desconocido"):
            build_model("UnknownModel", X_normal, np.array([1, 0, 1, 0, 1]))

    def test_build_gradient(self, X_normal):
        """build_model funciona para GradientBoosting."""
        y = np.array([1, 0, 1, 0, 1] * 10)
        model, scaler = build_model("GradientBoosting", X_normal[:50], y)

        assert model is not None
        assert scaler is not None

    def test_build_xgboost(self, X_normal):
        """build_model funciona para XGBoost."""
        y = np.array([1, 0, 1, 0, 1] * 10)
        model, scaler = build_model("XGBoost", X_normal[:50], y)

        assert model is not None
        assert scaler is not None

    def test_build_lightgbm(self, X_normal):
        """build_model funciona para LightGBM."""
        y = np.array([1, 0, 1, 0, 1] * 10)
        model, scaler = build_model("LightGBM", X_normal[:50], y)

        assert model is not None
        assert scaler is not None
