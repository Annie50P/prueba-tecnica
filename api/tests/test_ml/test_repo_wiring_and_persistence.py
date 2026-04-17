"""
Regresión B1/C1/C2/C9 — servicios 100 % via repository pattern +
modelo ML persistido en disco.

Garantiza que:
  - `api/services/graphiti_service.py` y `api/services/analytics_service.py`
    NO importan `sqlite3` (todo el acceso va por `get_backend()`).
  - El artifact del modelo se persiste a `api/ml/artifacts/` vía joblib.
  - Simulando un reinicio (borrando `model_registry._ARTIFACT`), el
    predictor carga desde disco sin re-entrenar.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICES = [
    REPO_ROOT / "api" / "services" / "graphiti_service.py",
    REPO_ROOT / "api" / "services" / "analytics_service.py",
]


def _strip_comments_and_strings(source: str) -> str:
    """Quita comentarios de línea y docstrings para que 'sqlite3' en texto
    libre no cuente como import real."""
    # Quitar docstrings triples (muy simple: heurístico suficiente).
    source = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", "", source, flags=re.DOTALL)
    # Quitar comentarios de línea
    source = re.sub(r"(?m)#.*$", "", source)
    return source


def test_services_do_not_import_sqlite3():
    """B1/C1: ningún servicio puede importar sqlite3 (todo via repo)."""
    for path in SERVICES:
        src = _strip_comments_and_strings(path.read_text(encoding="utf-8"))
        assert not re.search(r"^\s*import\s+sqlite3\b", src, flags=re.MULTILINE), (
            f"{path.name} aún importa sqlite3 — debe usar get_backend()"
        )
        assert not re.search(r"^\s*from\s+sqlite3\b", src, flags=re.MULTILINE), (
            f"{path.name} aún importa desde sqlite3"
        )
        assert "sqlite3.connect" not in src, (
            f"{path.name} aún llama sqlite3.connect directamente"
        )


def test_services_reference_get_backend():
    """Verificación positiva: los services sí importan get_backend()."""
    for path in SERVICES:
        src = path.read_text(encoding="utf-8")
        assert "get_backend" in src, (
            f"{path.name} no usa get_backend — repo pattern roto"
        )


def test_artifact_dir_is_api_ml_artifacts():
    """C9: la ruta oficial de artifacts es api/ml/artifacts/."""
    from api.ml import model_registry

    expected = REPO_ROOT / "api" / "ml" / "artifacts"
    assert model_registry.MODEL_DIR.resolve() == expected.resolve()
    assert model_registry.MODEL_DIR.exists()


@pytest.fixture
def _clean_artifact():
    from api.ml import model_registry, predictor

    saved = model_registry._ARTIFACT
    saved_cache = dict(predictor._CACHE)
    model_registry._ARTIFACT = None
    predictor._CACHE.clear()
    yield
    model_registry._ARTIFACT = saved
    predictor._CACHE.clear()
    predictor._CACHE.update(saved_cache)


def test_cold_start_loads_from_disk_without_retraining(_clean_artifact):
    """
    C2/C9: simular un reinicio. Si hay artifact en disco, predictor
    debe cargarlo SIN llamar a `compare_models` (no retrain).
    """
    from unittest.mock import patch
    from api.ml import model_registry, predictor
    import api.repositories as repo_mod

    # Garantizar que hay un artifact en disco.
    latest = model_registry.get_latest_model()
    if latest is None:
        pytest.skip(
            "No hay artifact persistido en api/ml/artifacts/. "
            "Corre `python -m api.ml.train_offline` primero."
        )

    # Estado frío — _ARTIFACT vacío.
    assert model_registry.get_loaded_artifact() is None

    # Datos mínimos para llegar a la inferencia
    repo_mod._backend = None
    from api.services import analytics_service as svc
    data = svc._load_all_data()

    with patch("api.ml.train.compare_models") as mock_compare:
        results = predictor.get_prediccion_clientes(data)

    assert mock_compare.call_count == 0, (
        "predictor llamó compare_models en cold-start — debería haber cargado "
        "el artifact desde disco (C2/C9 roto)"
    )
    assert len(results) > 0
    # Confirmar que el artifact quedó cargado en RAM
    art = model_registry.get_loaded_artifact()
    assert art is not None
    assert art.get("version_id", "").startswith("GradientBoosting_")


def test_register_persists_joblib_to_disk(_clean_artifact, tmp_path, monkeypatch):
    """C9: register_model debe escribir un .joblib real y leer-loopable."""
    from api.ml import model_registry
    import joblib
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    # Redirigir MODEL_DIR a tmp_path para no ensuciar el dir real.
    monkeypatch.setattr(model_registry, "MODEL_DIR", tmp_path)
    monkeypatch.setattr(model_registry, "REGISTRY_FILE", tmp_path / "registry.json")
    monkeypatch.setattr(model_registry, "_ARTIFACT", None)

    X = np.random.rand(20, 10)
    y = (np.random.rand(20) > 0.5).astype(int)
    model = LogisticRegression().fit(X, y)
    scaler = StandardScaler().fit(X)

    version = model_registry.register_model(
        model_name="TestModel",
        model=model,
        scaler=scaler,
        metrics={"roc_auc": 0.5},
        n_samples=20,
        label_mode="test",
    )

    artifact_path = tmp_path / f"{version}.joblib"
    assert artifact_path.exists(), "register_model no persistió .joblib"
    blob = joblib.load(artifact_path)
    assert "model" in blob and "scaler" in blob and "feature_names" in blob

    # load_latest debe reproducir el artifact en RAM
    model_registry._ARTIFACT = None
    loaded_version = model_registry.load_latest()
    assert loaded_version == version
    reloaded = model_registry.get_loaded_artifact()
    assert reloaded["version_id"] == version
