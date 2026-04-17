"""
Implementación Neo4j del GraphRepository (B1).

Se activa con GRAPH_BACKEND=neo4j. Requiere `neo4j` driver + una instancia
hidratada vía `python -m ingesta.hydrate_neo4j`.

Las operaciones sync del driver neo4j se delegan a un thread pool via
`asyncio.to_thread()` para no bloquear el event loop de FastAPI.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from .graph_repository import GraphRepository

logger = logging.getLogger(__name__)


class Neo4jGraphRepository(GraphRepository):
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError(
                "GRAPH_BACKEND=neo4j pero el driver no está instalado. "
                "pip install neo4j"
            ) from exc
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self._driver.verify_connectivity()
        except Exception as exc:
            raise RuntimeError(
                f"Neo4j no accesible en {uri}: {exc}. "
                "Levanta la instancia (docker compose up neo4j) y corre "
                "`python -m ingesta.hydrate_neo4j` para hidratar."
            ) from exc
        logger.info("Neo4jGraphRepository conectado a %s", uri)

    def close(self) -> None:
        if getattr(self, "_driver", None) is not None:
            self._driver.close()

    # ---- helper interno ----

    def _run_cypher(self, cypher: str, **params) -> list[dict]:
        with self._driver.session() as s:
            return [dict(r) for r in s.run(cypher, **params)]

    # ---- primitivas ----

    async def get_nodes_by_label(
        self, label: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        def _sync():
            if limit is not None:
                cypher = (
                    f"MATCH (n:{label}) RETURN n.id AS id, properties(n) AS props "
                    f"SKIP $offset LIMIT $limit"
                )
                rows = self._run_cypher(cypher, offset=int(offset), limit=int(limit))
            else:
                cypher = f"MATCH (n:{label}) RETURN n.id AS id, properties(n) AS props"
                rows = self._run_cypher(cypher)
            return [
                {"id": r["id"], "properties": dict(r["props"] or {})}
                for r in rows
            ]

        return await asyncio.to_thread(_sync)

    async def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        def _sync():
            cypher = (
                "MATCH (n {id: $id}) "
                "RETURN n.id AS id, labels(n) AS labels, properties(n) AS props LIMIT 1"
            )
            with self._driver.session() as s:
                record = s.run(cypher, id=node_id).single()
            if record is None:
                return None
            labels = list(record["labels"] or [])
            return {
                "id": record["id"],
                "label": labels[0] if labels else "",
                "properties": dict(record["props"] or {}),
            }

        return await asyncio.to_thread(_sync)

    async def get_outgoing(
        self, from_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        def _sync():
            if rel_type:
                cypher = (
                    f"MATCH (a {{id: $id}})-[r:{rel_type}]->(b) "
                    "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                    "properties(r) AS props"
                )
            else:
                cypher = (
                    "MATCH (a {id: $id})-[r]->(b) "
                    "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                    "properties(r) AS props"
                )
            return [
                {
                    "from_id": r["from_id"],
                    "rel_type": r["rel_type"],
                    "to_id": r["to_id"],
                    "properties": dict(r["props"] or {}),
                }
                for r in self._run_cypher(cypher, id=from_id)
            ]

        return await asyncio.to_thread(_sync)

    async def get_incoming(
        self, to_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        def _sync():
            if rel_type:
                cypher = (
                    f"MATCH (a)-[r:{rel_type}]->(b {{id: $id}}) "
                    "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                    "properties(r) AS props"
                )
            else:
                cypher = (
                    "MATCH (a)-[r]->(b {id: $id}) "
                    "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                    "properties(r) AS props"
                )
            return [
                {
                    "from_id": r["from_id"],
                    "rel_type": r["rel_type"],
                    "to_id": r["to_id"],
                    "properties": dict(r["props"] or {}),
                }
                for r in self._run_cypher(cypher, id=to_id)
            ]

        return await asyncio.to_thread(_sync)

    async def count_nodes_by_label(self, label: str) -> int:
        def _sync():
            cypher = f"MATCH (n:{label}) RETURN count(n) AS n"
            with self._driver.session() as s:
                rec = s.run(cypher).single()
            return int(rec["n"]) if rec else 0

        return await asyncio.to_thread(_sync)

    # ---- helpers semánticos ----

    async def get_outgoing_nodes(
        self,
        from_id: str,
        rel_type: str,
        target_label: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        def _sync():
            if target_label:
                cypher = (
                    f"MATCH (a {{id: $id}})-[:{rel_type}]->(b:{target_label}) "
                    "RETURN b.id AS id, labels(b) AS labels, properties(b) AS props"
                )
            else:
                cypher = (
                    f"MATCH (a {{id: $id}})-[:{rel_type}]->(b) "
                    "RETURN b.id AS id, labels(b) AS labels, properties(b) AS props"
                )
            out = []
            for r in self._run_cypher(cypher, id=from_id):
                labels = list(r["labels"] or [])
                out.append(
                    {
                        "id": r["id"],
                        "label": labels[0] if labels else "",
                        "properties": dict(r["props"] or {}),
                    }
                )
            return out

        return await asyncio.to_thread(_sync)

    async def get_two_hop_nodes(
        self,
        from_id: str,
        rel1: str,
        intermediate_label: str,
        rel2: str,
        target_label: str,
    ) -> list[dict[str, Any]]:
        def _sync():
            cypher = (
                f"MATCH (a {{id: $id}})-[:{rel1}]->(m:{intermediate_label})"
                f"-[:{rel2}]->(b:{target_label}) "
                "RETURN b.id AS id, labels(b) AS labels, properties(b) AS props"
            )
            out = []
            for r in self._run_cypher(cypher, id=from_id):
                labels = list(r["labels"] or [])
                out.append(
                    {
                        "id": r["id"],
                        "label": labels[0] if labels else "",
                        "properties": dict(r["props"] or {}),
                    }
                )
            return out

        return await asyncio.to_thread(_sync)

    async def get_all_relationships(
        self, rel_types: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        def _sync():
            if rel_types:
                cypher = (
                    "MATCH (a)-[r]->(b) WHERE type(r) IN $rel_types "
                    "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                    "properties(r) AS props"
                )
                rows = self._run_cypher(cypher, rel_types=list(rel_types))
            else:
                cypher = (
                    "MATCH (a)-[r]->(b) "
                    "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                    "properties(r) AS props"
                )
                rows = self._run_cypher(cypher)
            return [
                {
                    "from_id": r["from_id"],
                    "rel_type": r["rel_type"],
                    "to_id": r["to_id"],
                    "properties": dict(r["props"] or {}),
                }
                for r in rows
            ]

        return await asyncio.to_thread(_sync)
