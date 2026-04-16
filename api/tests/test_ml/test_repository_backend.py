"""
Regresión B1 — capa de repositorios con switch configurable.

Verifica que el factory `get_backend()` retorna el backend correcto según
settings.graph_backend y que Neo4j queda explícitamente como stub
(NotImplementedError) — nunca pasa silenciosamente.
"""
from __future__ import annotations

import pytest


def test_default_backend_is_sqlite():
    from api.repositories import get_backend, sqlite_repository

    # Forzar resolver limpio
    import api.repositories as repo_mod
    repo_mod._backend = None

    backend = get_backend()
    assert isinstance(backend, sqlite_repository.SqliteGraphRepository)


def test_neo4j_backend_is_wired_but_stubbed(monkeypatch):
    from api.config import settings
    import api.repositories as repo_mod

    monkeypatch.setattr(settings, "graph_backend", "neo4j")
    repo_mod._backend = None

    backend = repo_mod.get_backend()
    from api.repositories.neo4j_repository import Neo4jGraphRepository
    assert isinstance(backend, Neo4jGraphRepository)

    # Cualquier método debe levantar NotImplementedError con mensaje orientativo.
    with pytest.raises(NotImplementedError, match="stub"):
        backend.get_nodes_by_label("Cliente")

    # Limpieza
    monkeypatch.setattr(settings, "graph_backend", "sqlite")
    repo_mod._backend = None


def test_sqlite_repository_roundtrip():
    """SqliteGraphRepository lee de local_graph.db y responde."""
    from api.repositories import get_backend
    import api.repositories as repo_mod

    repo_mod._backend = None
    backend = get_backend()

    n_clientes = backend.count_nodes_by_label("Cliente")
    assert n_clientes >= 1

    nodes = backend.get_nodes_by_label("Cliente", limit=3)
    assert len(nodes) <= 3
    assert all("id" in n and "properties" in n for n in nodes)
