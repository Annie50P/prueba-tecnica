"""
Tests para el módulo segmentation.py - Segmentación y estrategias.

Ejecutar con:
    cd api && python -m pytest tests/test_ml/test_segmentation.py -v
"""

import pytest
from api.ml.segmentation import get_estrategias


# Fixture
@pytest.fixture
def data_real():
    """Carga datos reales."""
    from api.services.analytics_service import _load_all_data

    return _load_all_data()


# Tests
class TestGetEstrategias:
    def test_returns_dict(self, data_real):
        """Retorna diccionario."""
        result = get_estrategias(data_real)

        assert isinstance(result, dict)

    def test_mejores_horas(self, data_real):
        """mejores_horas presente."""
        result = get_estrategias(data_real)

        assert "mejores_horas" in result
        assert isinstance(result["mejores_horas"], list)

    def test_mejores_horas_structure(self, data_real):
        """cada hora tiene estructura válida."""
        result = get_estrategias(data_real)

        if result["mejores_horas"]:
            h = result["mejores_horas"][0]
            assert "hora" in h
            assert "tasa_exito" in h
            assert "total" in h

    def test_segmentos(self, data_real):
        """segmentos presente."""
        result = get_estrategias(data_real)

        assert "segmentos" in result
        assert isinstance(result["segmentos"], dict)

    def test_segmentos_sum(self, data_real):
        """segmentos suma correcta."""
        result = get_estrategias(data_real)
        segs = result["segmentos"]

        total = sum(segs.values())
        assert total > 0

    def test_recomendaciones(self, data_real):
        """recomendaciones presente."""
        result = get_estrategias(data_real)

        assert "recomendaciones" in result
        assert isinstance(result["recomendaciones"], list)

    def test_modelo(self, data_real):
        """modelo presente."""
        result = get_estrategias(data_real)

        assert "modelo" in result
        model = result["modelo"]

        assert "tipo" in model
        assert "k_optimo" in model
        assert model["tipo"] == "KMeans"

    def test_k_optimo_range(self, data_real):
        """k_optimo en rango válido."""
        result = get_estrategias(data_real)
        k = result["modelo"]["k_optimo"]

        assert 2 <= k <= 6

    def test_silhouette(self, data_real):
        """silhouette válido."""
        result = get_estrategias(data_real)
        sil = result["modelo"]["silhouette"]

        assert -1 <= sil <= 1

    def test_timestamp(self, data_real):
        """timestamp presente."""
        result = get_estrategias(data_real)

        assert "timestamp" in result
        assert result["timestamp"] is not None

    def test_agentes(self, data_real):
        """agentes presente."""
        result = get_estrategias(data_real)

        assert "agentes" in result
        assert isinstance(result["agentes"], list)

    def test_cluster_profiles(self, data_real):
        """cluster_profiles presente."""
        result = get_estrategias(data_real)

        assert "cluster_profiles" in result
        assert isinstance(result["cluster_profiles"], list)
