"""
hydrate_neo4j.py — Carga bulk desde SQLite → Neo4j (B1).

Uso:
    python -m ingesta.hydrate_neo4j
    # o con credenciales custom:
    NEO4J_URI=bolt://localhost:7687 NEO4J_USER=neo4j NEO4J_PASSWORD=password123 python -m ingesta.hydrate_neo4j

Lee `ingesta/local_graph.db` (fuente de verdad de la ingesta) y vuelca:
  - Todos los nodos con su label y properties (como map en Cypher)
  - Todas las relaciones tipadas (dinámicas via apoc.create.relationship
    NO se usa — se generan N queries específicas, compatible sin APOC)

Idempotente: MERGE por id, sobreescribe properties.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys

from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_graph.db")


def _parse_props(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _sanitize(props: dict) -> dict:
    """Neo4j solo acepta primitivos o listas de primitivos como props."""
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


def main() -> int:
    if not os.path.exists(DB_PATH):
        logger.error("SQLite no encontrada en %s — corre `python ingesta/ingest.py` primero.", DB_PATH)
        return 1

    sql = sqlite3.connect(DB_PATH)
    sql.row_factory = sqlite3.Row

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as exc:
        logger.error("No se pudo conectar a Neo4j en %s: %s", NEO4J_URI, exc)
        return 2

    with driver.session() as session:
        # Clean slate (idempotencia fuerte para bootstrap).
        logger.info("Limpiando grafo existente...")
        session.run("MATCH (n) DETACH DELETE n")

        # Índices por label (equivalente a lo que hicimos en SQLite: label scan fast).
        logger.info("Creando constraints + índices...")
        for label in ("Cliente", "Agente", "Interaccion", "PromesaPago", "Pago", "PlanPago", "EstadoDeuda"):
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )
        session.run(
            "CREATE INDEX interaccion_ts IF NOT EXISTS "
            "FOR (i:Interaccion) ON (i.timestamp)"
        )
        session.run(
            "CREATE INDEX interaccion_cliente_ts IF NOT EXISTS "
            "FOR (i:Interaccion) ON (i.cliente_id, i.timestamp)"
        )
        session.run(
            "CREATE INDEX interaccion_agente IF NOT EXISTS "
            "FOR (i:Interaccion) ON (i.agente_id)"
        )
        session.run(
            "CREATE INDEX interaccion_tipo_resultado IF NOT EXISTS "
            "FOR (i:Interaccion) ON (i.tipo, i.resultado)"
        )
        session.run(
            "CREATE INDEX promesa_fecha IF NOT EXISTS "
            "FOR (p:PromesaPago) ON (p.fecha_promesa)"
        )
        session.run(
            "CREATE INDEX promesa_cumplida IF NOT EXISTS "
            "FOR (p:PromesaPago) ON (p.cumplida)"
        )
        session.run(
            "CREATE INDEX estadodeuda_cliente_fecha IF NOT EXISTS "
            "FOR (e:EstadoDeuda) ON (e.cliente_id, e.fecha)"
        )

        # Bulk load de nodos, agrupado por label.
        nodos_por_label: dict[str, list[dict]] = {}
        for row in sql.execute("SELECT id, label, properties FROM nodes"):
            props = _sanitize(_parse_props(row["properties"]))
            props["id"] = row["id"]
            nodos_por_label.setdefault(row["label"], []).append(props)

        for label, items in nodos_por_label.items():
            session.run(
                f"UNWIND $items AS p MERGE (n:{label} {{id: p.id}}) SET n += p",
                items=items,
            )
            logger.info("  %s → %d nodos", label, len(items))

        # Relaciones: una query por rel_type (evita APOC).
        rels_por_tipo: dict[str, list[dict]] = {}
        for row in sql.execute(
            "SELECT from_id, rel_type, to_id, properties FROM relationships"
        ):
            rels_por_tipo.setdefault(row["rel_type"], []).append(
                {
                    "from_id": row["from_id"],
                    "to_id": row["to_id"],
                    "props": _sanitize(_parse_props(row["properties"])),
                }
            )

        for rel_type, items in rels_por_tipo.items():
            session.run(
                f"""
                UNWIND $items AS r
                MATCH (a {{id: r.from_id}}), (b {{id: r.to_id}})
                MERGE (a)-[rel:{rel_type}]->(b)
                SET rel += r.props
                """,
                items=items,
            )
            logger.info("  %s → %d aristas", rel_type, len(items))

        # Verificación
        total_n = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        total_r = session.run("MATCH ()-[r]->() RETURN count(r) AS r").single()["r"]
        logger.info("OK — Neo4j: %d nodos, %d relaciones", total_n, total_r)

    driver.close()
    sql.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
