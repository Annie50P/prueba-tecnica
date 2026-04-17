"""
Regresión C4 — `PromesaPago.cumplida` resoluble on-read.

En modo `dynamic`, el flag cumplida no se lee del snapshot — se recalcula
a partir de los pagos del cliente dentro del grace window. Así, un pago
insertado después de la ingesta se refleja inmediatamente.

Tras el refactor B1/C1: los servicios consumen la capa de repositorio,
por lo que el test monta una mini-DB SQLite y fuerza `settings.db_path`
hacia ella, sin tocar conexiones directas.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile


def _build_mini_db(tmpdir: str, include_pago: bool) -> str:
    """
    1 cliente + 1 interacción promesa + 1 promesa vencida (snapshot=False).
    Si include_pago=True, añade un Pago dentro del grace window.
    """
    db_path = os.path.join(tmpdir, "mini.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE nodes (id TEXT PRIMARY KEY, label TEXT, properties TEXT);
        CREATE TABLE relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id TEXT, rel_type TEXT, to_id TEXT, properties TEXT
        );
        """
    )

    cliente = {"id": "cli1", "nombre": "Test", "monto_deuda_inicial": 1000.0}
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?)",
        ("cli1", "Cliente", json.dumps(cliente)),
    )

    inter_promesa = {
        "id": "ix1",
        "cliente_id": "cli1",
        "timestamp": "2026-01-01T10:00:00+00:00",
        "tipo": "llamada_saliente",
        "resultado": "promesa_pago",
    }
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?)",
        ("ix1", "Interaccion", json.dumps(inter_promesa)),
    )

    promesa = {
        "id": "ix1_promesa",
        "cliente_id": "cli1",
        "fecha_promesa": "2026-01-05",
        "monto_prometido": 500.0,
        "cumplida": False,
    }
    conn.execute(
        "INSERT INTO nodes VALUES (?, ?, ?)",
        ("ix1_promesa", "PromesaPago", json.dumps(promesa)),
    )

    conn.execute(
        "INSERT INTO relationships (from_id, rel_type, to_id, properties) VALUES (?, ?, ?, ?)",
        ("cli1", "TIENE_INTERACCION", "ix1", "{}"),
    )
    conn.execute(
        "INSERT INTO relationships (from_id, rel_type, to_id, properties) VALUES (?, ?, ?, ?)",
        ("ix1", "GENERO_PROMESA", "ix1_promesa", "{}"),
    )

    if include_pago:
        ix_pago = {
            "id": "ix2",
            "cliente_id": "cli1",
            "timestamp": "2026-01-06T14:00:00+00:00",
            "tipo": "pago_recibido",
        }
        conn.execute(
            "INSERT INTO nodes VALUES (?, ?, ?)",
            ("ix2", "Interaccion", json.dumps(ix_pago)),
        )
        conn.execute(
            "INSERT INTO relationships (from_id, rel_type, to_id, properties) VALUES (?, ?, ?, ?)",
            ("cli1", "TIENE_INTERACCION", "ix2", "{}"),
        )

    conn.commit()
    conn.close()
    return db_path


def _use_minidb(monkeypatch, db_path: str, mode: str = "dynamic"):
    """
    Monkey-patchea settings.db_path → minidb y fuerza re-resolución del
    backend + modo de cumplida. Garantiza que get_backend() devuelva una
    instancia fresca apuntando al minidb.
    """
    from api.config import settings
    import api.repositories as repo_mod
    from api.services import graphiti_service

    monkeypatch.setattr(settings, "db_path", db_path)
    monkeypatch.setattr(settings, "graph_backend", "sqlite")
    repo_mod._backend = None  # fuerza nueva SqliteGraphRepository
    monkeypatch.setattr(graphiti_service, "_CUMPLIDA_MODE", mode)
    monkeypatch.setattr(graphiti_service, "_GRACE_DAYS", 3)


def test_dynamic_mode_detects_post_ingesta_payment(monkeypatch):
    """Snapshot dice False, pero hay pago en grace window → dynamic retorna True."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _build_mini_db(tmp, include_pago=True)
        _use_minidb(monkeypatch, db_path, mode="dynamic")

        from api.services import graphiti_service

        props = {
            "cliente_id": "cli1",
            "fecha_promesa": "2026-01-05",
            "cumplida": False,
        }
        assert graphiti_service._is_cumplida_dynamic(props) is True


def test_dynamic_mode_no_payment_returns_false(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _build_mini_db(tmp, include_pago=False)
        _use_minidb(monkeypatch, db_path, mode="dynamic")

        from api.services import graphiti_service

        props = {
            "cliente_id": "cli1",
            "fecha_promesa": "2026-01-05",
            "cumplida": False,
        }
        assert graphiti_service._is_cumplida_dynamic(props) is False


def test_snapshot_mode_respects_persisted_flag(monkeypatch):
    """Default mode usa snapshot; no consulta pagos ni el repo."""
    from api.services import graphiti_service

    monkeypatch.setattr(graphiti_service, "_CUMPLIDA_MODE", "snapshot")
    assert graphiti_service._resolve_cumplida({"cumplida": True}) is True
    assert graphiti_service._resolve_cumplida({"cumplida": False}) is False
