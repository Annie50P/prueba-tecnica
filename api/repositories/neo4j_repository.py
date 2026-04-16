"""
Stub de repositorio Neo4j (B1).

Se activa con GRAPH_BACKEND=neo4j. Requiere `neo4j` driver en requirements.
Los métodos están esqueletizados con la query Cypher lista: para activarlos
en producción solo hay que instalar el driver, descomentar el código y
configurar NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD.

Hoy levanta NotImplementedError con un mensaje claro — jamás pasa
silenciosamente.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from .graph_repository import GraphRepository

logger = logging.getLogger(__name__)


class Neo4jGraphRepository(GraphRepository):
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        # try:
        #     from neo4j import GraphDatabase
        #     self._driver = GraphDatabase.driver(uri, auth=(user, password))
        # except ImportError as exc:
        #     raise RuntimeError(
        #         "GRAPH_BACKEND=neo4j pero el driver no está instalado. "
        #         "pip install neo4j"
        #     ) from exc
        logger.warning(
            "Neo4jGraphRepository: stub. Set GRAPH_BACKEND=sqlite o completar esta clase."
        )

    def _not_ready(self) -> None:
        raise NotImplementedError(
            "Neo4jGraphRepository es un stub. Para producción:\n"
            "  1. pip install neo4j\n"
            "  2. Descomentar self._driver en __init__\n"
            "  3. Implementar cada método con session.run(CYPHER)\n"
            "  4. Alternativamente setear GRAPH_BACKEND=sqlite para usar el fallback."
        )

    def get_nodes_by_label(
        self, label: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        # Cypher de referencia:
        #   MATCH (n:{label}) RETURN n SKIP $offset LIMIT $limit
        self._not_ready()

    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        # MATCH (n {id: $id}) RETURN n, labels(n)
        self._not_ready()

    def get_outgoing(
        self, from_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        # MATCH (a {id: $id})-[r]->(b) [WHERE type(r) = $rel_type] RETURN a,r,b
        self._not_ready()

    def get_incoming(
        self, to_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        # MATCH (a)-[r]->(b {id: $id}) [WHERE type(r) = $rel_type] RETURN a,r,b
        self._not_ready()

    def count_nodes_by_label(self, label: str) -> int:
        # MATCH (n:{label}) RETURN count(n) AS n
        self._not_ready()
