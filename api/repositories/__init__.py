"""
Capa de repositorios (B1).

Objetivo: aislar el backend de lectura (SQLite vs Neo4j+Graphiti) detrás de una
interfaz estable. Los services NO deben hablar SQL directo; deben resolver
`get_backend()` y llamar métodos del repo.

Estado actual (prueba técnica, sin Neo4j corriendo):
  - SqliteGraphRepository es la implementación activa por defecto.
  - Neo4jGraphRepository es un stub que levanta NotImplementedError con
    instrucciones claras de cableado (wiring point para producción real).

Switch:  GRAPH_BACKEND=sqlite  (default)  |  GRAPH_BACKEND=neo4j
"""
from __future__ import annotations

from api.config import settings

from .graph_repository import GraphRepository
from .sqlite_repository import SqliteGraphRepository

_backend: GraphRepository | None = None


def get_backend() -> GraphRepository:
    """
    Singleton lazy. Resuelve el repo según settings.graph_backend.

    Para producción con Neo4j, setear GRAPH_BACKEND=neo4j y proveer
    NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD. La implementación neo4j es un
    stub — completar queries Cypher en neo4j_repository.py.
    """
    global _backend
    if _backend is not None:
        return _backend

    kind = (settings.graph_backend or "sqlite").lower()
    if kind == "neo4j":
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
