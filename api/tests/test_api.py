"""
Tests automatizados para la API del Analizador de Patrones de Llamadas.

Ejecutar con:
    cd api && python -m pytest tests/ -v

Requiere: pip install pytest httpx
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


# ─────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_root_returns_app_info(self):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "app" in data
        assert "version" in data


# ─────────────────────────────────────────────────────────
# Clientes
# ─────────────────────────────────────────────────────────

class TestClientes:
    def test_list_clientes(self):
        r = client.get("/clientes")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_cliente_has_required_fields(self):
        r = client.get("/clientes")
        c = r.json()[0]
        assert "id" in c
        assert "nombre" in c or "id" in c
        assert "monto_deuda_inicial" in c

    def test_cliente_detalle(self):
        # Get first client id
        clientes = client.get("/clientes").json()
        cid = clientes[0]["id"]
        r = client.get(f"/clientes/{cid}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == cid

    def test_cliente_detalle_not_found(self):
        r = client.get("/clientes/NONEXISTENT_ID")
        assert r.status_code == 404

    def test_cliente_timeline(self):
        clientes = client.get("/clientes").json()
        cid = clientes[0]["id"]
        r = client.get(f"/clientes/{cid}/timeline")
        assert r.status_code == 200
        data = r.json()
        assert "timeline" in data or isinstance(data, list)


# ─────────────────────────────────────────────────────────
# Agentes
# ─────────────────────────────────────────────────────────

class TestAgentes:
    def test_list_agentes(self):
        r = client.get("/agentes")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_agente_has_required_fields(self):
        agentes = client.get("/agentes").json()
        a = agentes[0]
        assert "id" in a
        assert "total_llamadas" in a

    def test_agente_efectividad(self):
        agentes = client.get("/agentes").json()
        aid = agentes[0]["id"]
        r = client.get(f"/agentes/{aid}/efectividad")
        assert r.status_code == 200
        data = r.json()
        assert "distribucion_resultados" in data or "total_llamadas" in data

    def test_agente_not_found(self):
        r = client.get("/agentes/NONEXISTENT_AGENT/efectividad")
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────

class TestAnalytics:
    def test_dashboard(self):
        r = client.get("/analytics/dashboard")
        assert r.status_code == 200
        data = r.json()
        assert "total_deuda_inicial" in data
        assert "total_recuperado" in data
        assert "tasa_recuperacion" in data
        assert "promesas_cumplidas" in data
        assert "promesas_incumplidas" in data
        assert "distribucion_tipos_deuda" in data
        assert "actividad_por_dia" in data

    def test_dashboard_values_are_numeric(self):
        data = client.get("/analytics/dashboard").json()
        assert isinstance(data["total_deuda_inicial"], (int, float))
        assert isinstance(data["total_recuperado"], (int, float))
        assert 0 <= data["tasa_recuperacion"] <= 1

    def test_promesas_incumplidas(self):
        r = client.get("/analytics/promesas-incumplidas")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_mejores_horarios(self):
        r = client.get("/analytics/mejores-horarios")
        assert r.status_code == 200
        data = r.json()
        assert "mejor_hora" in data
        assert "detalle_por_hora" in data


# ─────────────────────────────────────────────────────────
# Analytics Avanzado (Bonus)
# ─────────────────────────────────────────────────────────

class TestAnalyticsAvanzado:
    def test_prediccion(self):
        r = client.get("/analytics/prediccion")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check structure
        c = data[0]
        assert "cliente_id" in c
        assert "score_riesgo" in c
        assert "categoria_riesgo" in c
        assert "probabilidad_pago" in c
        assert "factores" in c
        assert 0 <= c["score_riesgo"] <= 100
        assert c["categoria_riesgo"] in ("alto", "medio", "bajo")

    def test_prediccion_sorted_by_risk(self):
        data = client.get("/analytics/prediccion").json()
        scores = [c["score_riesgo"] for c in data]
        assert scores == sorted(scores, reverse=True)

    def test_anomalias(self):
        r = client.get("/analytics/anomalias")
        assert r.status_code == 200
        data = r.json()
        assert "total_anomalias" in data
        assert "por_severidad" in data
        assert "anomalias" in data
        assert isinstance(data["anomalias"], list)

    def test_anomalias_severity_valid(self):
        data = client.get("/analytics/anomalias").json()
        for a in data["anomalias"]:
            assert a["severidad"] in ("alta", "media", "baja")
            assert "descripcion" in a
            assert "tipo" in a

    def test_estrategias(self):
        r = client.get("/analytics/estrategias")
        assert r.status_code == 200
        data = r.json()
        assert "mejores_horas" in data
        assert "segmentos" in data
        assert "recomendaciones" in data
        assert isinstance(data["recomendaciones"], list)

    def test_estrategias_segmentos(self):
        data = client.get("/analytics/estrategias").json()
        seg = data["segmentos"]
        assert "quick_wins" in seg
        assert "casos_criticos" in seg
        total = sum(seg.values())
        assert total > 0  # At least some clients are segmented


# ─────────────────────────────────────────────────────────
# Grafo
# ─────────────────────────────────────────────────────────

class TestGrafo:
    def test_nodos(self):
        r = client.get("/grafo/nodos")
        assert r.status_code == 200
        data = r.json()
        assert "nodos" in data
        assert len(data["nodos"]) > 0

    def test_nodos_filter_by_type(self):
        r = client.get("/grafo/nodos?tipos=Cliente&tipos=Agente")
        assert r.status_code == 200
        nodos = r.json()["nodos"]
        for n in nodos:
            assert n["tipo"] in ("Cliente", "Agente")

    def test_relaciones(self):
        r = client.get("/grafo/relaciones")
        assert r.status_code == 200
        data = r.json()
        assert "enlaces" in data

    def test_relaciones_filter_by_client(self):
        clientes_list = client.get("/clientes").json()
        cid = clientes_list[0]["id"]
        r = client.get(f"/grafo/relaciones?cliente_id={cid}&profundidad=1")
        assert r.status_code == 200
        data = r.json()
        assert "enlaces" in data

    def test_relaciones_filter_by_type(self):
        r = client.get("/grafo/relaciones?tipos_relacion=TIENE_INTERACCION")
        assert r.status_code == 200
        data = r.json()
        for e in data["enlaces"]:
            assert e["tipo"] == "TIENE_INTERACCION"


# ─────────────────────────────────────────────────────────
# MCP
# ─────────────────────────────────────────────────────────

class TestMCP:
    def test_mcp_endpoint_exists(self):
        r = client.post("/mcp/query", json={"query": "test"})
        # Should return 200 (even if LLM not configured, returns error payload)
        assert r.status_code == 200

    def test_mcp_returns_structure(self):
        r = client.post("/mcp/query", json={"query": "test"})
        data = r.json()
        # Response always includes respuesta (may be empty) or message
        assert "respuesta" in data or "message" in data
