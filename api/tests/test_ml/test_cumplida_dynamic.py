"""
Regresión C4 — `PromesaPago.cumplida` resoluble on-read.

En modo `dynamic`, el flag cumplida no se lee del snapshot — se recalcula
a partir de los pagos del cliente dentro del grace window. Así, un pago
insertado después de la ingesta se refleja inmediatamente.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone


def _build_mini_db(tmpdir: str, include_pago: bool) -> str:
    """
    Crea una DB SQLite con 1 cliente, 1 interacción y 1 promesa vencida.
    Si include_pago=True, añade también un Pago dentro del grace window.
    El snapshot de `cumplida` se setea en False a propósito.
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

    # Promesa: vence el 2026-01-05. SNAPSHOT=False deliberado.
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
        # Pago el 2026-01-06 (dentro de grace=3 days → deadline 2026-01-08).
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


def test_dynamic_mode_detects_post_ingesta_payment(monkeypatch):
    """
    Escenario: snapshot dice cumplida=False, pero hay un pago dentro del
    grace window. En modo `dynamic` debe retornar True.
    """
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _build_mini_db(tmp, include_pago=True)

        # Forzar modo dynamic + grace=3
        import importlib
        from api.services import graphiti_service

        monkeypatch.setattr(graphiti_service, "DB_PATH", db_path)
        monkeypatch.setattr(graphiti_service, "_CUMPLIDA_MODE", "dynamic")
        monkeypatch.setattr(graphiti_service, "_GRACE_DAYS", 3)
        monkeypatch.setattr(graphiti_service, "_INDEXES_ENSURED", False)

        conn = graphiti_service._get_connection()
        try:
            props = {
                "cliente_id": "cli1",
                "fecha_promesa": "2026-01-05",
                "cumplida": False,  # snapshot miente
            }
            cumplida = graphiti_service._is_cumplida_dynamic(
                conn, props, "ix1_promesa"
            )
        finally:
            conn.close()

        assert cumplida is True, (
            "Modo dynamic no detectó pago post-ingesta dentro de grace window"
        )


def test_dynamic_mode_no_payment_returns_false(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _build_mini_db(tmp, include_pago=False)

        from api.services import graphiti_service

        monkeypatch.setattr(graphiti_service, "DB_PATH", db_path)
        monkeypatch.setattr(graphiti_service, "_CUMPLIDA_MODE", "dynamic")
        monkeypatch.setattr(graphiti_service, "_GRACE_DAYS", 3)
        monkeypatch.setattr(graphiti_service, "_INDEXES_ENSURED", False)

        conn = graphiti_service._get_connection()
        try:
            props = {
                "cliente_id": "cli1",
                "fecha_promesa": "2026-01-05",
                "cumplida": False,
            }
            cumplida = graphiti_service._is_cumplida_dynamic(
                conn, props, "ix1_promesa"
            )
        finally:
            conn.close()

        assert cumplida is False


def test_snapshot_mode_respects_persisted_flag(monkeypatch):
    """Default mode usa snapshot; no consulta pagos."""
    from api.services import graphiti_service

    monkeypatch.setattr(graphiti_service, "_CUMPLIDA_MODE", "snapshot")
    # Sin DB real — _resolve_cumplida(snapshot) no lee la conexión.
    result_true = graphiti_service._resolve_cumplida(
        None, {"cumplida": True}, "p1"
    )
    result_false = graphiti_service._resolve_cumplida(
        None, {"cumplida": False}, "p2"
    )
    assert result_true is True
    assert result_false is False
