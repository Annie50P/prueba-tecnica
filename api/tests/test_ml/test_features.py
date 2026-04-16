"""
Tests para el módulo features.py - Feature engineering.

Ejecutar con:
    cd api && python -m pytest tests/test_ml/test_features.py -v
"""

import pytest
import numpy as np
from api.ml.features import (
    build_feature_matrix,
    FEATURE_NAMES,
    label_stats,
)


# Fixtures - datos de prueba
@pytest.fixture
def data_minima():
    """Data con 5 clientes mínimos."""
    return {
        "clientes": {
            f"c{i}": {
                "nombre": f"Cliente {i}",
                "monto_deuda_inicial": 1000,
                "monto_pendiente": 500,
                "total_pagado": 500,
            }
            for i in range(5)
        },
        "inters_by_client": {f"c{i}": [] for i in range(5)},
        "promesas_by_client": {},
        "pagos_by_client": {},
    }


@pytest.fixture
def data_vacia():
    """Data vacía."""
    return {}


@pytest.fixture
def data_sin_claves():
    """Data sin ключ clients."""
    return {
        "inters_by_client": {},
        "promesas_by_client": {},
        "pagos_by_client": {},
    }


# Tests - build_feature_matrix
class TestBuildFeatureMatrix:
    def test_data_vacia(self, data_vacia):
        """Debe fallar con data vacío."""
        with pytest.raises(ValueError, match="data está vacío"):
            build_feature_matrix(data_vacia)

    def test_sin_claves(self, data_sin_claves):
        """Debe fallar sin clientes."""
        with pytest.raises(ValueError, match="no hay clientes"):
            build_feature_matrix(data_sin_claves)

    def test_features_construidas(self, data_minima):
        """Retorna X, meta, y correctamente."""
        client_ids, X, meta, y = build_feature_matrix(data_minima)

        assert len(client_ids) == 5
        assert X.shape == (5, len(FEATURE_NAMES))
        assert len(meta) == 5
        # y puede ser None o array con labels

    def test_features_nombres(self):
        """FEATURE_NAMES tiene 10 features."""
        assert len(FEATURE_NAMES) == 10
        assert "tasa_cumplimiento" in FEATURE_NAMES
        assert "rfm_recency" in FEATURE_NAMES

    def test_x_es_numpy_array(self, data_minima):
        """X es numpy array de floats."""
        client_ids, X, meta, y = build_feature_matrix(data_minima)

        assert isinstance(X, np.ndarray)
        assert X.dtype == np.float64
        assert X.shape[1] == len(FEATURE_NAMES)

    def test_meta_tiene_campos(self, data_minima):
        """meta incluye campos requeridos."""
        client_ids, X, meta, y = build_feature_matrix(data_minima)

        for m in meta:
            assert "nombre" in m
            assert "deuda_inicial" in m
            assert "deuda_pendiente" in m


class TestLabelStats:
    def test_label_stats_sin_labels(self):
        """Sin labels retorna modo heuristic."""
        stats = label_stats(None, [])

        assert stats["mode"] == "heuristic"
        assert stats["n_labeled"] == 0

    def test_label_stats_con_labels(self):
        """Con labels retorna estadísticas."""
        y = np.array([1, 1, 0, -1, -1])
        raw = [1, 1, 0, None, None]
        stats = label_stats(y, raw)

        assert stats["mode"] == "ground_truth"
        assert stats["n_labeled"] == 3
        assert stats["n_positive"] == 2
        assert stats["n_negative"] == 1

    def test_positive_rate(self):
        """Calcula positive_rate correctamente."""
        y = np.array([1, 1, 1, 0])
        raw = [1, 1, 1, 0]
        stats = label_stats(y, raw)

        assert stats["positive_rate"] == 0.75
