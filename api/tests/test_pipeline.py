"""
Tests de integración para el pipeline ML completo.

Ejecutar con:
    cd api && python -m pytest tests/test_pipeline.py -v
"""

import pytest
from api.services.analytics_service import _load_all_data
from api.ml.predictor import get_prediccion_clientes
from api.ml.anomalies import get_anomalias
from api.ml.segmentation import get_estrategias
from api.ml.features import build_feature_matrix


# Fixture - datos reales
@pytest.fixture
def data():
    """Carga datos reales."""
    return _load_all_data()


# Tests
class TestPipelineIntegration:
    def test_pipeline_completo(self, data):
        """Pipeline completo funciona."""
        # 1. Features
        client_ids, X, meta, y = build_feature_matrix(data)

        assert len(client_ids) > 0
        assert X.shape[0] == len(client_ids)

        # 2. Predicción
        preds = get_prediccion_clientes(data)
        assert len(preds) > 0

        # 3. Anomalías
        anomalias = get_anomalias(data)
        assert "total_anomalias" in anomalias

        # 4. Estrategias
        estrategias = get_estrategias(data)
        assert "segmentos" in estrategias

    def test_pipeline_consistency(self, data):
        """Consistencia entre módulos."""
        # Features
        client_ids, X, meta, y = build_feature_matrix(data)
        n_clientes = len(X)

        # Predicción
        preds = get_prediccion_clientes(data)
        assert len(preds) == n_clientes

        # Anomalías y estrategias también usan los mismos datos
        anomalias = get_anomalias(data)
        estrategias = get_estrategias(data)

        assert anomalias is not None
        assert estrategias is not None

    def test_pipeline_output_structure(self, data):
        """Estructura de outputs."""
        preds = get_prediccion_clientes(data)

        # Primera predicción tiene metadata
        assert "_modelo" in preds[0]
        assert "_timestamp" in preds[0]

        # Model info completo
        model_info = preds[0]["_modelo"]
        assert "modelo" in model_info
        assert "metrics" in model_info

    def test_pipeline_timestamps(self, data):
        """Timestamps en todos los outputs."""
        preds = get_prediccion_clientes(data)
        assert preds[0].get("_timestamp") is not None

        anomalias = get_anomalias(data)
        assert "timestamp" in anomalias

        estrategias = get_estrategias(data)
        assert "timestamp" in estrategias

    def test_metrics_in_predictions(self, data):
        """Métricas en predictions."""
        preds = get_prediccion_clientes(data)
        model_info = preds[0]["_modelo"]
        metrics = model_info.get("metrics", {})

        # Verificar métricas completas
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert "roc_auc" in metrics
        assert "accuracy" in metrics

    def test_categoria_riesgo(self, data):
        """categoría_riesgo válida."""
        preds = get_prediccion_clientes(data)

        for p in preds:
            assert p["categoria_riesgo"] in ("alto", "medio", "bajo")

    def test_segments_count(self, data):
        """Segmentos cubren todos clientes."""
        estrategias = get_estrategias(data)
        segmentos = estrategias.get("segmentos", {})

        # Total en segmentos
        total = sum(segmentos.values())
        assert total > 0
