"""
GraphitiClient — ingesta de datos vía graphiti-core con fallback SQLite.

Responsabilidades:
  - Conectar al Neo4j que gestiona Graphiti (graphiti-core SDK).
  - write_domain_node() / write_domain_relationship(): escribe nodos/aristas
    estructurados del dominio al Neo4j de Graphiti (mismo grafo que usa MCP).
  - add_episode(): ingesta semántica via Graphiti (extracción LLM opcional).
  - Fallback transparente a SQLite local cuando Graphiti/Neo4j no está disponible.

SQLite schema (fallback):
    nodes         (id TEXT PRIMARY KEY, label TEXT, properties TEXT)
    relationships (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   from_id TEXT, rel_type TEXT, to_id TEXT, properties TEXT)
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_graph.db")
_DEFAULT_NEO4J_URI = "bolt://localhost:7687"
_DEFAULT_NEO4J_USER = "neo4j"
_DEFAULT_NEO4J_PASSWORD = "password123"
_DEFAULT_GROUP_ID = "prueba-tecnica"


def _run_sync(coro):
    """Ejecuta una coroutine desde contexto síncrono."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                return ex.submit(asyncio.run, coro).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)


def _sanitize(props: dict) -> dict:
    """Neo4j solo acepta primitivos o listas de primitivos como propiedades."""
    out = {}
    for k, v in props.items():
        if v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, list) and all(
            isinstance(x, (str, int, float, bool)) for x in v
        ):
            out[k] = v
        else:
            out[k] = json.dumps(v, ensure_ascii=False, default=str)
    return out


class GraphitiClient:
    """
    Cliente de ingesta que escribe en el Neo4j gestionado por Graphiti.

    Cuando graphiti-core no está disponible o Neo4j está caído, cae
    automáticamente a SQLite local con el mismo schema de dominio.
    """

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        db_path: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> None:
        self._neo4j_uri = (
            neo4j_uri
            or os.environ.get("NEO4J_URI", _DEFAULT_NEO4J_URI)
        )
        self._neo4j_user = (
            neo4j_user
            or os.environ.get("NEO4J_USER", _DEFAULT_NEO4J_USER)
        )
        self._neo4j_password = (
            neo4j_password
            or os.environ.get("NEO4J_PASSWORD", _DEFAULT_NEO4J_PASSWORD)
        )
        self.db_path = db_path or os.environ.get("GRAPHITI_DB_PATH", _DEFAULT_DB_PATH)
        self.group_id = group_id or os.environ.get("GRAPHITI_GROUP_ID", _DEFAULT_GROUP_ID)

        self._graphiti = None
        self._graphiti_available: Optional[bool] = None

        # SQLite siempre se inicializa (fallback o primario en dev)
        self._sqlite_conn = self._init_sqlite()

    # ------------------------------------------------------------------
    # SQLite helpers (fallback)
    # ------------------------------------------------------------------

    def _init_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY, label TEXT, properties TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id TEXT, rel_type TEXT, to_id TEXT, properties TEXT
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(rel_type)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rel_from_type ON relationships(from_id, rel_type)"
        )
        conn.commit()
        return conn

    def _sqlite_write_node(self, label: str, props: dict) -> str:
        node_id = props.get("id") or str(uuid.uuid4())
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO nodes (id, label, properties) VALUES (?, ?, ?)",
            (node_id, label, json.dumps(props, ensure_ascii=False, default=str)),
        )
        self._sqlite_conn.commit()
        return node_id

    def _sqlite_write_rel(
        self, from_id: str, rel_type: str, to_id: str, props: dict
    ) -> None:
        self._sqlite_conn.execute(
            "INSERT INTO relationships (from_id, rel_type, to_id, properties) "
            "VALUES (?, ?, ?, ?)",
            (from_id, rel_type, to_id, json.dumps(props, ensure_ascii=False, default=str)),
        )
        self._sqlite_conn.commit()

    # ------------------------------------------------------------------
    # graphiti-core helpers
    # ------------------------------------------------------------------

    def _get_graphiti(self):
        """Devuelve la instancia Graphiti inicializada, o None si no disponible."""
        if self._graphiti is not None:
            return self._graphiti
        try:
            from graphiti_core import Graphiti
            g = Graphiti(
                uri=self._neo4j_uri,
                user=self._neo4j_user,
                password=self._neo4j_password,
            )
            _run_sync(g.driver.verify_connectivity())
            self._graphiti = g
            self._graphiti_available = True
            logger.info(
                "[graphiti-client] Conectado a Neo4j en %s (group=%s)",
                self._neo4j_uri,
                self.group_id,
            )
        except ImportError:
            logger.warning(
                "[graphiti-client] graphiti-core no instalado — usando SQLite fallback."
            )
            self._graphiti_available = False
        except Exception as exc:
            logger.warning(
                "[graphiti-client] Neo4j no accesible en %s: %s — usando SQLite fallback.",
                self._neo4j_uri,
                exc,
            )
            self._graphiti_available = False
        return self._graphiti

    async def _async_write_node(self, label: str, props: dict) -> str:
        """Escribe un nodo de dominio en Neo4j vía Graphiti. MERGE por id."""
        node_id = props.get("id") or str(uuid.uuid4())
        sanitized = _sanitize(props)
        sanitized["id"] = node_id
        cypher = f"MERGE (n:{label} {{id: $node_id}}) SET n += $props"
        g = self._get_graphiti()
        async with g.driver.session() as session:
            await session.run(cypher, node_id=node_id, props=sanitized)
        return node_id

    async def _async_write_rel(
        self, from_id: str, rel_type: str, to_id: str, props: dict
    ) -> None:
        """Escribe una relación de dominio en Neo4j vía Graphiti. MERGE idempotente."""
        sanitized = _sanitize(props)
        cypher = (
            f"MATCH (a {{id: $from_id}}), (b {{id: $to_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r += $props"
        )
        g = self._get_graphiti()
        async with g.driver.session() as session:
            await session.run(cypher, from_id=from_id, to_id=to_id, props=sanitized)

    async def _async_build_constraints(self) -> None:
        """Crea constraints e índices de dominio en Neo4j (idempotente)."""
        g = self._get_graphiti()
        async with g.driver.session() as session:
            for label in ("Cliente", "Agente", "Interaccion", "PromesaPago", "Pago", "PlanPago"):
                await session.run(
                    f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )
            await session.run(
                "CREATE INDEX interaccion_ts IF NOT EXISTS "
                "FOR (i:Interaccion) ON (i.timestamp)"
            )
            await session.run(
                "CREATE INDEX promesa_fecha IF NOT EXISTS "
                "FOR (p:PromesaPago) ON (p.fecha_promesa)"
            )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """True si Neo4j es accesible vía graphiti-core."""
        if self._graphiti_available is not None:
            return self._graphiti_available
        return self._get_graphiti() is not None

    def setup_constraints(self) -> None:
        """Crea constraints e índices de dominio en Neo4j. Solo si disponible."""
        if not self.health_check():
            return
        try:
            _run_sync(self._async_build_constraints())
            logger.info("[graphiti-client] Constraints e índices creados.")
        except Exception as exc:
            logger.warning("[graphiti-client] No se pudieron crear constraints: %s", exc)

    def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """
        Escribe un nodo de dominio.
        Ruta principal → Neo4j vía Graphiti. Fallback → SQLite.
        """
        if self.health_check():
            try:
                return _run_sync(self._async_write_node(label, properties))
            except Exception as exc:
                logger.warning(
                    "[graphiti-client] Error escribiendo nodo %s en Neo4j: %s — "
                    "cayendo a SQLite.",
                    label,
                    exc,
                )
                self._graphiti_available = False
        return self._sqlite_write_node(label, properties)

    def create_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Escribe una relación de dominio.
        Ruta principal → Neo4j vía Graphiti. Fallback → SQLite.
        """
        props = properties or {}
        if self.health_check():
            try:
                _run_sync(self._async_write_rel(from_id, rel_type, to_id, props))
                return True
            except Exception as exc:
                logger.warning(
                    "[graphiti-client] Error escribiendo relación %s en Neo4j: %s — "
                    "cayendo a SQLite.",
                    rel_type,
                    exc,
                )
                self._graphiti_available = False
        self._sqlite_write_rel(from_id, rel_type, to_id, props)
        return True

    def add_episode(
        self,
        name: str,
        body: str,
        reference_time: Optional[datetime] = None,
        source_description: str = "call data",
    ) -> bool:
        """
        Ingesta semántica: añade un episodio a Graphiti para que extraiga
        entidades y relaciones vía LLM. Silencioso si falla (el episodio
        semántico es complementario a los nodos de dominio ya escritos).
        """
        if not self.health_check():
            return False
        try:
            from graphiti_core.nodes import EpisodeType

            ref_time = reference_time or datetime.now(tz=timezone.utc)

            async def _add():
                await self._graphiti.add_episode(
                    name=name,
                    episode_body=body,
                    source=EpisodeType.json,
                    source_description=source_description,
                    reference_time=ref_time,
                    group_id=self.group_id,
                )

            _run_sync(_add())
            return True
        except ImportError:
            logger.debug("[graphiti-client] graphiti_core.nodes no disponible — skip episode.")
            return False
        except Exception as exc:
            logger.debug(
                "[graphiti-client] add_episode '%s' falló (no crítico): %s", name, exc
            )
            return False

    # ------------------------------------------------------------------
    # Introspección (stats para el summary de ingest.py)
    # ------------------------------------------------------------------

    def count_nodes(self) -> int:
        row = self._sqlite_conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
        return row[0] if row else 0

    def count_relationships(self) -> int:
        row = self._sqlite_conn.execute("SELECT COUNT(*) FROM relationships").fetchone()
        return row[0] if row else 0

    def count_nodes_by_label(self) -> Dict[str, int]:
        rows = self._sqlite_conn.execute(
            "SELECT label, COUNT(*) FROM nodes GROUP BY label ORDER BY label"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def count_rels_by_type(self) -> Dict[str, int]:
        rows = self._sqlite_conn.execute(
            "SELECT rel_type, COUNT(*) FROM relationships GROUP BY rel_type ORDER BY rel_type"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def close(self) -> None:
        try:
            self._sqlite_conn.close()
        except Exception:
            pass
        if self._graphiti:
            try:
                _run_sync(self._graphiti.close())
            except Exception:
                pass
