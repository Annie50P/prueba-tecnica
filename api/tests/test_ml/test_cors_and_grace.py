"""
Regresión B5 (CORS spec) y C6 (grace days configurable).
"""
from __future__ import annotations

import importlib
import os

import pytest


def test_cors_does_not_combine_wildcard_with_credentials(monkeypatch):
    """
    Si origins == ["*"], allow_credentials DEBE ser False.
    Caso contrario los browsers rechazan los preflight — combinación inválida
    por spec CORS.
    """
    from api import config

    monkeypatch.setattr(config.settings, "cors_origins", ["*"])
    # Reimport main para re-evaluar la lógica de middleware.
    import api.main as main_mod
    importlib.reload(main_mod)

    assert main_mod._origins == ["*"]
    assert main_mod._allow_credentials is False, (
        "CORS: allow_credentials=True + origins=['*'] es spec-invalid (B5)"
    )


def test_cors_allows_credentials_with_explicit_origins(monkeypatch):
    from api import config

    monkeypatch.setattr(
        config.settings, "cors_origins", ["http://localhost:5173"]
    )
    import api.main as main_mod
    importlib.reload(main_mod)

    assert main_mod._allow_credentials is True


def test_grace_days_reads_from_env(monkeypatch):
    """C6: la ventana de gracia se lee de env, no se hardcodea."""
    from ingesta import transforms

    monkeypatch.setenv("PROMESA_GRACE_DAYS", "7")
    assert transforms._get_grace_days() == 7

    monkeypatch.setenv("PROMESA_GRACE_DAYS", "0")
    assert transforms._get_grace_days() == 0

    # Valor inválido → fallback al default (3).
    monkeypatch.setenv("PROMESA_GRACE_DAYS", "foo")
    assert transforms._get_grace_days() == transforms.GRACE_DAYS_DEFAULT


def test_grace_days_not_hardcoded_in_transforms():
    """
    C6 regresión de auditoría: en `transform()` el cálculo de CUMPLE_PROMESA
    (Pass 5) usaba `timedelta(days=3)` literal. Ahora debe usar grace_days.
    """
    import inspect
    from ingesta import transforms

    src = inspect.getsource(transforms.transform)
    # No debe quedar ningún literal "days=3" (la constante DEFAULT vive fuera
    # del body de transform).
    assert "days=3)" not in src, (
        "timedelta(days=3) hardcoded vuelve a estar dentro de transform() — "
        "C6 regresado"
    )
    assert "grace_days" in src, "transform() ya no parametriza grace_days"
