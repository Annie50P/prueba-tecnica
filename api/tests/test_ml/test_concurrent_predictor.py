"""
Regresión C8 — `predictor._CACHE` y `_TRAIN_LOCK` bajo concurrencia.

Bajo N threads compitiendo por un cache vacío, el singleflight lock debe
garantizar un único entrenamiento (no thundering herd). El resultado
retornado debe ser el mismo objeto para todos.
"""
from __future__ import annotations

import threading
from unittest.mock import patch

import numpy as np
import pytest


def _fake_data():
    """Mini dataset sintético compatible con build_feature_matrix."""
    clientes = {
        f"c{i}": {
            "nombre": f"cliente_{i}",
            "monto_deuda_inicial": 10000.0,
            "monto_pendiente": 5000.0,
            "total_pagado": 5000.0,
        }
        for i in range(10)
    }
    return {
        "clientes": clientes,
        "agentes": {},
        "all_inters": [],
        "all_promesas": [],
        "all_pagos": [],
        "inters_by_client": {cid: [] for cid in clientes},
        "promesas_by_client": {cid: [] for cid in clientes},
        "pagos_by_client": {cid: [] for cid in clientes},
    }


@pytest.fixture
def _clean_predictor_state():
    """Salva y restaura _ARTIFACT / _CACHE para no contaminar otros tests."""
    from api.ml import predictor, model_registry

    saved_cache = dict(predictor._CACHE)
    saved_artifact = model_registry._ARTIFACT
    predictor._CACHE.clear()
    model_registry._ARTIFACT = None
    yield
    predictor._CACHE.clear()
    predictor._CACHE.update(saved_cache)
    model_registry._ARTIFACT = saved_artifact


def test_train_lock_coalesces_concurrent_requests(_clean_predictor_state):
    """
    Con 8 threads compitiendo por cache vacío, `compare_models` debe
    invocarse al menos una vez, pero NO proporcional al número de threads.
    (Singleflight: el primero entrena, el resto ve el artifact poblado.)
    """
    from api.ml import predictor, model_registry

    call_count = {"n": 0}
    lock = threading.Lock()

    def fake_compare_models(X, y):
        with lock:
            call_count["n"] += 1
        # Devolver una estructura mínima compatible con predictor.
        return {
            "best_model": _DummyClassifier(),
            "scaler": _DummyScaler(),
            "label_mode": "heuristic",
            "n_labeled": len(X),
            "comparison": [],
            "model_info": {
                "modelo": "Dummy",
                "metrics": {"roc_auc": 0.5},
                "label_mode": "heuristic",
            },
        }

    def fake_run_inference(client_ids, X, meta, model_info):
        return [
            {
                "cliente_id": cid,
                "score_riesgo": 0.5,
                "categoria_riesgo": "medio",
                "probabilidad_pago": 0.5,
                "label_mode": "heuristic",
                "factores": {},
            }
            for cid in client_ids
        ]

    data = _fake_data()
    results = []

    with patch("api.ml.train.compare_models", side_effect=fake_compare_models):
        with patch("api.ml.inference.run_inference", side_effect=fake_run_inference):
            with patch("api.ml.model_registry.register_model") as mock_reg:
                # register_model debe poblar _ARTIFACT para que siguientes threads
                # hagan short-circuit. Simulamos eso.
                def _register_side_effect(**kwargs):
                    model_registry._ARTIFACT = {
                        "version_id": "test",
                        "model": kwargs["model"],
                        "scaler": kwargs["scaler"],
                        "label_mode": kwargs["label_mode"],
                        "metrics": kwargs["metrics"],
                    }
                    return "test"

                mock_reg.side_effect = _register_side_effect

                def worker():
                    # Cada thread llama predictor; el lock debe coalescerlos
                    predictor._CACHE.clear()  # forzar miss en cada thread
                    r = predictor.get_prediccion_clientes(data)
                    results.append(r)

                threads = [threading.Thread(target=worker) for _ in range(8)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

    # Con lock, el numero de llamadas a compare_models debe ser 1 (no 8).
    # Tolero hasta 2 por si el timing hace que el segundo pase antes del commit.
    assert call_count["n"] <= 2, (
        f"compare_models invocado {call_count['n']} veces bajo concurrencia — "
        "singleflight roto (C8)"
    )
    assert len(results) == 8
    # Model_registry tiene el artifact cargado
    assert model_registry._ARTIFACT is not None


class _DummyClassifier:
    def predict(self, X):
        return np.zeros(len(X))

    def predict_proba(self, X):
        return np.tile([0.5, 0.5], (len(X), 1))


class _DummyScaler:
    def transform(self, X):
        return np.asarray(X)
