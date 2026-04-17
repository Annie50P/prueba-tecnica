"""
Regresión B1 — capa de repositorios con switch configurable.

- Default backend = SQLite (dev/test sin infra externa).
- Con GRAPH_BACKEND=neo4j resuelve Neo4jGraphRepository y lee de la
  instancia real; si Neo4j no está arriba, el test se skipea (sin
  enmascarar fallos: solo informa).
- Parity check: las mismas queries contra ambos backends deben retornar
  los mismos conteos y los mismos vecindarios de aristas.
"""
from __future__ import annotations

import pytest


def test_default_backend_is_sqlite():
    from api.repositories import get_backend, sqlite_repository

    import api.repositories as repo_mod
    repo_mod._backend = None

    backend = get_backend()
    assert isinstance(backend, sqlite_repository.SqliteGraphRepository)


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


@pytest.fixture
def _live_neo4j_backend(monkeypatch):
    """Factory que devuelve (sqlite_repo, neo4j_repo) o skip si Neo4j no está arriba."""
    from api.config import settings
    import api.repositories as repo_mod

    # Permitir override desde env para local host
    import os
    uri = os.environ.get("NEO4J_URI_TEST", "bolt://localhost:7687")
    monkeypatch.setattr(settings, "neo4j_uri", uri)

    monkeypatch.setattr(settings, "graph_backend", "sqlite")
    repo_mod._backend = None
    sqlite_repo = repo_mod.get_backend()

    monkeypatch.setattr(settings, "graph_backend", "neo4j")
    repo_mod._backend = None
    try:
        neo4j_repo = repo_mod.get_backend()
    except RuntimeError as exc:
        pytest.skip(f"Neo4j no accesible ({exc}); levanta docker compose y corre hydrate_neo4j.")

    yield sqlite_repo, neo4j_repo

    # cleanup
    try:
        neo4j_repo.close()
    except Exception:
        pass
    monkeypatch.setattr(settings, "graph_backend", "sqlite")
    repo_mod._backend = None


def test_neo4j_backend_resolves_and_queries(_live_neo4j_backend):
    """Neo4jGraphRepository debe responder a los 5 métodos del contrato."""
    _, neo4j_repo = _live_neo4j_backend
    from api.repositories.neo4j_repository import Neo4jGraphRepository

    assert isinstance(neo4j_repo, Neo4jGraphRepository)

    n_clientes = neo4j_repo.count_nodes_by_label("Cliente")
    assert n_clientes >= 1

    nodes = neo4j_repo.get_nodes_by_label("Cliente", limit=2)
    assert len(nodes) <= 2
    assert all("id" in n and "properties" in n for n in nodes)

    if nodes:
        cid = nodes[0]["id"]
        node = neo4j_repo.get_node(cid)
        assert node is not None
        assert node["label"] == "Cliente"
        assert node["id"] == cid
        # Outgoing e incoming deben retornar listas (vacías o no)
        assert isinstance(neo4j_repo.get_outgoing(cid), list)
        assert isinstance(neo4j_repo.get_incoming(cid), list)


def test_neo4j_and_sqlite_have_parity(_live_neo4j_backend):
    """
    Conteos por label y vecindario saliente de una muestra de clientes
    deben coincidir — garantiza que hydrate_neo4j.py no dejó nada atrás.
    """
    sqlite_repo, neo4j_repo = _live_neo4j_backend

    labels = ["Cliente", "Agente", "Interaccion", "PromesaPago", "Pago", "PlanPago"]
    sq_counts = {lbl: sqlite_repo.count_nodes_by_label(lbl) for lbl in labels}
    ne_counts = {lbl: neo4j_repo.count_nodes_by_label(lbl) for lbl in labels}
    assert sq_counts == ne_counts, (
        f"Parity roto — SQLite={sq_counts}  Neo4j={ne_counts}. "
        "Re-ejecuta `python -m ingesta.hydrate_neo4j`."
    )

    # Muestra: outgoing edges de los primeros 3 clientes deben matchear
    sample = sqlite_repo.get_nodes_by_label("Cliente", limit=3)
    for n in sample:
        cid = n["id"]
        sq = sorted(
            (e["rel_type"], e["to_id"]) for e in sqlite_repo.get_outgoing(cid)
        )
        ne = sorted(
            (e["rel_type"], e["to_id"]) for e in neo4j_repo.get_outgoing(cid)
        )
        assert sq == ne, f"Aristas de {cid} divergen: sqlite={sq[:3]} neo4j={ne[:3]}"
