"""
GraphitiGraphRepository — implementación async de GraphRepository usando graphiti-core.

Graphiti actúa como capa de acceso al grafo: gestiona la conexión a Neo4j,
mantiene los índices/constraints del knowledge graph y provee el contexto
semántico. La API no instancia neo4j.GraphDatabase directamente — toda
conexión va a través del cliente Graphiti.

Los nodos de dominio (Cliente, Agente, Interaccion, …) y los episodios/entidades
semánticos de Graphiti conviven en el mismo Neo4j. Las queries estructuradas
usan el driver async que graphiti-core inicializa y gestiona.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from .graph_repository import GraphRepository

logger = logging.getLogger(__name__)

_GRAPHITI_INTERNAL_LABELS = frozenset(
    {"Entity", "EpisodicNode", "EntityEdge", "Community", "EpisodicEdge"}
)


def _domain_label(labels: list[str]) -> str:
    for lbl in labels:
        if lbl not in _GRAPHITI_INTERNAL_LABELS:
            return lbl
    return labels[0] if labels else ""


class GraphitiGraphRepository(GraphRepository):
    """
    Lee el grafo de dominio usando la conexión Neo4j que gestiona graphiti-core.
    Todos los métodos son async nativos — sin ThreadPoolExecutor ni asyncio.run().
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        group_id: str = "prueba-tecnica",
    ) -> None:
        try:
            from graphiti_core import Graphiti
        except ImportError as exc:
            raise RuntimeError(
                "GRAPH_BACKEND=graphiti pero graphiti-core no está instalado. "
                "pip install graphiti-core"
            ) from exc

        self.uri = uri
        self.user = user
        self.password = password
        self.group_id = group_id
        self._graphiti = Graphiti(uri=uri, user=user, password=password)
        logger.info(
            "GraphitiGraphRepository inicializado para %s (group=%s)",
            uri,
            group_id,
        )

    async def close(self) -> None:
        if self._graphiti:
            try:
                await self._graphiti.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Helper interno: ejecuta Cypher vía el driver async de Graphiti
    # ------------------------------------------------------------------

    async def _q(self, cypher: str, **params) -> list[dict]:
        async with self._graphiti.driver.session() as session:
            result = await session.run(cypher, **params)
            return await result.data()

    # ------------------------------------------------------------------
    # Primitivas
    # ------------------------------------------------------------------

    async def get_nodes_by_label(
        self, label: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        if limit is not None:
            cypher = (
                f"MATCH (n:{label}) WHERE n.id IS NOT NULL "
                "RETURN n.id AS id, properties(n) AS props "
                "SKIP $offset LIMIT $limit"
            )
            rows = await self._q(cypher, offset=int(offset), limit=int(limit))
        else:
            cypher = (
                f"MATCH (n:{label}) WHERE n.id IS NOT NULL "
                "RETURN n.id AS id, properties(n) AS props"
            )
            rows = await self._q(cypher)
        return [{"id": r["id"], "properties": dict(r["props"] or {})} for r in rows]

    async def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        cypher = (
            "MATCH (n {id: $id}) "
            "RETURN n.id AS id, labels(n) AS lbls, properties(n) AS props LIMIT 1"
        )
        rows = await self._q(cypher, id=node_id)
        if not rows:
            return None
        r = rows[0]
        lbls = list(r.get("lbls") or [])
        return {
            "id": r["id"],
            "label": _domain_label(lbls),
            "properties": dict(r.get("props") or {}),
        }

    async def get_outgoing(
        self, from_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if rel_type:
            cypher = (
                f"MATCH (a {{id: $id}})-[r:{rel_type}]->(b) "
                "WHERE b.id IS NOT NULL "
                "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                "properties(r) AS props"
            )
        else:
            cypher = (
                "MATCH (a {id: $id})-[r]->(b) WHERE b.id IS NOT NULL "
                "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                "properties(r) AS props"
            )
        rows = await self._q(cypher, id=from_id)
        return [
            {
                "from_id": r["from_id"],
                "rel_type": r["rel_type"],
                "to_id": r["to_id"],
                "properties": dict(r.get("props") or {}),
            }
            for r in rows
            if r.get("to_id")
        ]

    async def get_incoming(
        self, to_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if rel_type:
            cypher = (
                f"MATCH (a)-[r:{rel_type}]->(b {{id: $id}}) "
                "WHERE a.id IS NOT NULL "
                "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                "properties(r) AS props"
            )
        else:
            cypher = (
                "MATCH (a)-[r]->(b {id: $id}) WHERE a.id IS NOT NULL "
                "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                "properties(r) AS props"
            )
        rows = await self._q(cypher, id=to_id)
        return [
            {
                "from_id": r["from_id"],
                "rel_type": r["rel_type"],
                "to_id": r["to_id"],
                "properties": dict(r.get("props") or {}),
            }
            for r in rows
            if r.get("from_id")
        ]

    async def count_nodes_by_label(self, label: str) -> int:
        rows = await self._q(
            f"MATCH (n:{label}) WHERE n.id IS NOT NULL RETURN count(n) AS n"
        )
        return int(rows[0]["n"]) if rows else 0

    # ------------------------------------------------------------------
    # Helpers semánticos (anti N+1)
    # ------------------------------------------------------------------

    async def get_outgoing_nodes(
        self,
        from_id: str,
        rel_type: str,
        target_label: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if target_label:
            cypher = (
                f"MATCH (a {{id: $id}})-[:{rel_type}]->(b:{target_label}) "
                "WHERE b.id IS NOT NULL "
                "RETURN b.id AS id, labels(b) AS lbls, properties(b) AS props"
            )
        else:
            cypher = (
                f"MATCH (a {{id: $id}})-[:{rel_type}]->(b) WHERE b.id IS NOT NULL "
                "RETURN b.id AS id, labels(b) AS lbls, properties(b) AS props"
            )
        rows = await self._q(cypher, id=from_id)
        out = []
        for r in rows:
            if not r.get("id"):
                continue
            lbls = list(r.get("lbls") or [])
            out.append(
                {
                    "id": r["id"],
                    "label": _domain_label(lbls),
                    "properties": dict(r.get("props") or {}),
                }
            )
        return out

    async def get_two_hop_nodes(
        self,
        from_id: str,
        rel1: str,
        intermediate_label: str,
        rel2: str,
        target_label: str,
    ) -> list[dict[str, Any]]:
        cypher = (
            f"MATCH (a {{id: $id}})-[:{rel1}]->(m:{intermediate_label})"
            f"-[:{rel2}]->(b:{target_label}) "
            "WHERE b.id IS NOT NULL "
            "RETURN b.id AS id, labels(b) AS lbls, properties(b) AS props"
        )
        rows = await self._q(cypher, id=from_id)
        out = []
        for r in rows:
            if not r.get("id"):
                continue
            lbls = list(r.get("lbls") or [])
            out.append(
                {
                    "id": r["id"],
                    "label": _domain_label(lbls),
                    "properties": dict(r.get("props") or {}),
                }
            )
        return out

    async def get_all_relationships(
        self, rel_types: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        if rel_types:
            cypher = (
                "MATCH (a)-[r]->(b) "
                "WHERE type(r) IN $rel_types "
                "  AND a.id IS NOT NULL AND b.id IS NOT NULL "
                "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                "properties(r) AS props"
            )
            rows = await self._q(cypher, rel_types=list(rel_types))
        else:
            cypher = (
                "MATCH (a)-[r]->(b) "
                "WHERE a.id IS NOT NULL AND b.id IS NOT NULL "
                "RETURN a.id AS from_id, type(r) AS rel_type, b.id AS to_id, "
                "properties(r) AS props"
            )
            rows = await self._q(cypher)
        return [
            {
                "from_id": r["from_id"],
                "rel_type": r["rel_type"],
                "to_id": r["to_id"],
                "properties": dict(r.get("props") or {}),
            }
            for r in rows
            if r.get("from_id") and r.get("to_id")
        ]
