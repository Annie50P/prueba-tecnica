"""
Capa de repositorios (B1).

Objetivo: aislar el backend de lectura detrás de una interfaz estable.
Los services NO deben hablar SQL/Cypher directo; deben resolver `get_backend()`
y llamar métodos del repo.

Switch via GRAPH_BACKEND:
  graphiti  (default con Neo4j) — GraphitiGraphRepository: acceso a Neo4j
             a través de graphiti-core. Graphiti gestiona la conexión, los
             índices y la capa semántica. API y MCP leen el mismo grafo.
  neo4j     — Neo4jGraphRepository: driver neo4j directo (sin Graphiti).
  sqlite    — SqliteGraphRepository: fallback local sin Neo4j.
"""
from __future__ import annotations

from api.config import settings

from .graph_repository import GraphRepository
from .sqlite_repository import SqliteGraphRepository

_backend: GraphRepository | None = None


def get_backend() -> GraphRepository:
    """
    Singleton lazy. Resuelve el repo según settings.graph_backend.

      GRAPH_BACKEND=graphiti  →  GraphitiGraphRepository (fuente única de verdad)
      GRAPH_BACKEND=neo4j     →  Neo4jGraphRepository (driver directo)
      GRAPH_BACKEND=sqlite    →  SqliteGraphRepository (dev/offline)
    """
    global _backend
    if _backend is not None:
        return _backend

    kind = (settings.graph_backend or "graphiti").lower()

    if kind == "graphiti":
        from .graphiti_repository import GraphitiGraphRepository

        _backend = GraphitiGraphRepository(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            group_id=settings.graphiti_group_id,
        )
    elif kind == "neo4j":
        from .neo4j_repository import Neo4jGraphRepository

        _backend = Neo4jGraphRepository(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    else:
        _backend = SqliteGraphRepository(db_path=settings.db_path)

    return _backend


__all__ = ["GraphRepository", "SqliteGraphRepository", "get_backend"]
