"""
Tests para el módulo anomalies.py - Detección de anomalías.

Ejecutar con:
    cd api && python -m pytest tests/test_ml/test_anomalies.py -v
"""

import pytest
from api.ml.anomalies import get_anomalias


# Fixture - datos reales
@pytest.fixture
def data_real():
    """Carga datos reales para tests."""
    from api.services.analytics_service import _load_all_data

    return _load_all_data()


# Tests
class TestGetAnomalias:
    def test_returns_dict(self, data_real):
        """Retorna diccionario."""
        result = get_anomalias(data_real)

        assert isinstance(result, dict)

    def test_total_anomalias(self, data_real):
        """total_anomalias es entero."""
        result = get_anomalias(data_real)

        assert "total_anomalias" in result
        assert isinstance(result["total_anomalias"], int)
        assert result["total_anomalias"] >= 0

    def test_por_severidad(self, data_real):
        """por_severidad tiene campos válidos."""
        result = get_anomalias(data_real)

        assert "por_severidad" in result
        sev = result["por_severidad"]

        assert "alta" in sev
        assert "media" in sev
        assert "baja" in sev
        # Suma debe igualar total
        assert sum(sev.values()) == result["total_anomalias"]

    def test_severidad_values(self, data_real):
        """severidad tiene valores válidos."""
        result = get_anomalias(data_real)

        for a in result["anomalias"]:
            assert a["severidad"] in ("alta", "media", "baja")

    def test_modelos_utilizados(self, data_real):
        """modelos_utilizados es lista."""
        result = get_anomalias(data_real)

        assert "modelos_utilizados" in result
        assert isinstance(result["modelos_utilizados"], list)
        assert len(result["modelos_utilizados"]) > 0

    def test_anomalias_list(self, data_real):
        """anomalias es lista."""
        result = get_anomalias(data_real)

        assert "anomalias" in result
        assert isinstance(result["anomalias"], list)

    def test_anomaly_has_fields(self, data_real):
        """Cada anomalía tiene campos requeridos."""
        result = get_anomalias(data_real)

        if result["anomalias"]:
            a = result["anomalias"][0]
            assert "tipo" in a
            assert "severidad" in a
            assert "descripcion" in a
            assert "entidad_id" in a
            assert "entidad_tipo" in a

    def test_timestamp(self, data_real):
        """timestamp está presente."""
        result = get_anomalias(data_real)

        assert "timestamp" in result
        assert result["timestamp"] is not None

    def test_contamination_estimada(self, data_real):
        """contamination_estimada es number o None."""
        result = get_anomalias(data_real)

        assert "contamination_estimada" in result
        cont = result["contamination_estimada"]
        assert cont is None or (isinstance(cont, (int, float)) and 0 < cont < 1)
