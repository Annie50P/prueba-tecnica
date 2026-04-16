"""
Regresión B4 — `_today_utc` es FUNCIÓN, no constante de módulo.

Si alguien reintroduce `_TODAY_UTC = datetime.now(...)` a nivel de módulo,
este test fallará. La invariante: dos llamadas consecutivas a `_today_utc()`
con monkeypatch sobre `datetime.now` deben retornar valores distintos.
"""
from __future__ import annotations

from datetime import date, datetime, timezone


def test_today_is_callable_not_frozen_constant():
    from ingesta import transforms

    assert callable(getattr(transforms, "_today_utc", None)), (
        "_today_utc debe ser función, no constante — B4 regresado"
    )
    assert not hasattr(transforms, "_TODAY_UTC"), (
        "_TODAY_UTC reintroducido como constante de módulo"
    )


def test_today_reflects_current_call():
    """Mock datetime.now y verifico que _today_utc lo respeta (no cacheado)."""
    from unittest.mock import patch
    from ingesta import transforms

    fake1 = datetime(2030, 1, 1, tzinfo=timezone.utc)
    fake2 = datetime(2030, 1, 2, tzinfo=timezone.utc)

    with patch("ingesta.transforms.datetime") as mock_dt:
        mock_dt.now.return_value = fake1
        mock_dt.combine = datetime.combine
        mock_dt.min = datetime.min
        d1 = transforms._today_utc()
        mock_dt.now.return_value = fake2
        d2 = transforms._today_utc()

    assert d1 == date(2030, 1, 1)
    assert d2 == date(2030, 1, 2)
    assert d1 != d2
