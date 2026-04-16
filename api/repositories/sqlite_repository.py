"""
Implementación SQLite del GraphRepository (B1).

Lee de `ingesta/local_graph.db`. Usa connection pool trivial (una conexión
por request vía `_conn()`), con los índices creados en `_ensure_indexes`
para evitar full-scan (C1).
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Optional

from .graph_repository import GraphRepository

logger = logging.getLogger(__name__)

_INDEXES_ENSURED_PATHS: set[str] = set()


def _ensure_indexes(conn: sqlite3.Connection, db_path: str) -> None:
    if db_path in _INDEXES_ENSURED_PATHS:
        return
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(rel_type)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rel_from_type ON relationships(from_id, rel_type)"
        )
        conn.commit()
        _INDEXES_ENSURED_PATHS.add(db_path)
    except sqlite3.OperationalError as exc:
        logger.warning("sqlite_repository: índices no creados: %s", exc)


def _parse_props(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


class SqliteGraphRepository(GraphRepository):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        _ensure_indexes(c, self.db_path)
        return c

    def get_nodes_by_label(
        self, label: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            if limit is not None:
                cur.execute(
                    "SELECT id, properties FROM nodes WHERE label = ? LIMIT ? OFFSET ?",
                    (label, limit, offset),
                )
            else:
                cur.execute(
                    "SELECT id, properties FROM nodes WHERE label = ?", (label,)
                )
            return [
                {"id": r["id"], "properties": _parse_props(r["properties"])}
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, label, properties FROM nodes WHERE id = ?", (node_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "label": row["label"],
                "properties": _parse_props(row["properties"]),
            }
        finally:
            conn.close()

    def get_outgoing(
        self, from_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            if rel_type:
                cur.execute(
                    "SELECT from_id, rel_type, to_id, properties FROM relationships "
                    "WHERE from_id = ? AND rel_type = ?",
                    (from_id, rel_type),
                )
            else:
                cur.execute(
                    "SELECT from_id, rel_type, to_id, properties FROM relationships "
                    "WHERE from_id = ?",
                    (from_id,),
                )
            return [
                {
                    "from_id": r["from_id"],
                    "rel_type": r["rel_type"],
                    "to_id": r["to_id"],
                    "properties": _parse_props(r["properties"]),
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def get_incoming(
        self, to_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            if rel_type:
                cur.execute(
                    "SELECT from_id, rel_type, to_id, properties FROM relationships "
                    "WHERE to_id = ? AND rel_type = ?",
                    (to_id, rel_type),
                )
            else:
                cur.execute(
                    "SELECT from_id, rel_type, to_id, properties FROM relationships "
                    "WHERE to_id = ?",
                    (to_id,),
                )
            return [
                {
                    "from_id": r["from_id"],
                    "rel_type": r["rel_type"],
                    "to_id": r["to_id"],
                    "properties": _parse_props(r["properties"]),
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def count_nodes_by_label(self, label: str) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM nodes WHERE label = ?", (label,))
            return int(cur.fetchone()["n"])
        finally:
            conn.close()
