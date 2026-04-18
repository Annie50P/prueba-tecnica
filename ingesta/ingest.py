#!/usr/bin/env python3
"""
Main entry point for the data ingestion module.

Usage:
    python ingest.py

Environment variables (optional, loaded from .env):
    GRAPHITI_URL        Base URL for Graphiti API  (default: http://localhost:8000)
    GRAPHITI_TIMEOUT    HTTP timeout in seconds     (default: 5)
    GRAPHITI_DB_PATH    Path to SQLite fallback DB  (default: ./local_graph.db)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Ensure the ingesta/ directory is on sys.path so sibling modules are found
# regardless of where the script is invoked from.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Load .env before importing project modules that read os.environ
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(_HERE, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
        print(f"[env] Loaded environment from {_env_file}")
    else:
        _root_env = os.path.join(os.path.dirname(_HERE), ".env")
        if os.path.exists(_root_env):
            load_dotenv(_root_env)
            print(f"[env] Loaded environment from {_root_env}")
except ImportError:
    print("[warn] python-dotenv not installed; skipping .env loading")

from graphiti_client import GraphitiClient
from models import (
    AgenteNode,
    ClienteNode,
    EstadoDeudaNode,
    InteraccionNode,
    PagoNode,
    PlanPagoNode,
    PromesaPagoNode,
    RelationRecord,
)
from transforms import transform
from validators import validate_dataset

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "interacciones_clientes.json",
)
SUMMARY_FILE = os.path.join(_HERE, "ingesta_completada.json")
PROGRESS_INTERVAL = 50


# ---------------------------------------------------------------------------
# Helpers async
# ---------------------------------------------------------------------------

def _load_json(path: str) -> Dict[str, Any]:
    print(f"[load] Reading data file: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


async def _ingest_nodes(
    client: GraphitiClient,
    label: str,
    nodes: List[Any],
) -> int:
    """Persist a list of Pydantic node models. Returns count ingested."""
    count = 0
    for node in nodes:
        props = node.model_dump()
        await client.create_node(label, props)
        count += 1
        if count % PROGRESS_INTERVAL == 0:
            print(f"  [{label}] {count}/{len(nodes)} nodes ingested ...")
    return count


async def _ingest_relationships(
    client: GraphitiClient,
    relationships: List[RelationRecord],
) -> int:
    """Persist all relationship records. Returns count ingested."""
    count = 0
    for rel in relationships:
        await client.create_relationship(rel.from_id, rel.rel_type, rel.to_id, rel.properties)
        count += 1
        if count % PROGRESS_INTERVAL == 0:
            print(f"  [relationships] {count}/{len(relationships)} ingested ...")
    return count


# ---------------------------------------------------------------------------
# Main async
# ---------------------------------------------------------------------------

async def main() -> None:
    start_time = time.time()
    print("=" * 60)
    print("  Call Pattern Analyzer – Data Ingestion")
    print("=" * 60)

    # 1. Load raw data
    raw = _load_json(DATA_FILE)

    # 2. Validate
    print("[validate] Validating dataset ...")
    dataset, warnings = validate_dataset(raw)
    if warnings:
        for w in warnings:
            print(f"  [warn] {w}")
    print(
        f"[validate] OK – {len(dataset.clientes)} clientes, "
        f"{len(dataset.interacciones)} interacciones"
    )

    # 3. Transform
    print("[transform] Computing graph nodes and relationships ...")
    agentes, clientes, interacciones, promesas, pagos, planes, estados_deuda, relationships = transform(dataset)
    print(
        f"[transform] Nodes: {len(agentes)} Agentes, {len(clientes)} Clientes, "
        f"{len(interacciones)} Interacciones, {len(promesas)} PromesasPago, "
        f"{len(pagos)} Pagos, {len(planes)} PlanesPago, {len(estados_deuda)} EstadosDeuda"
    )
    print(f"[transform] Relationships: {len(relationships)}")

    # 4. Initialise client
    client = GraphitiClient()
    graphiti_online = await client.health_check()
    if graphiti_online:
        print("[client] Neo4j/Graphiti ONLINE – ingesta vía graphiti-core")
        await client.setup_constraints()
    else:
        print(f"[client] Neo4j OFFLINE – usando SQLite fallback: {client.db_path}")

    # 5. Ingest nodes
    print("\n[ingest] Ingesting nodes ...")

    print(f"  Agentes ({len(agentes)}) ...")
    n_agentes = await _ingest_nodes(client, "Agente", agentes)
    print(f"  -> {n_agentes} Agentes done")

    print(f"  Clientes ({len(clientes)}) ...")
    n_clientes = await _ingest_nodes(client, "Cliente", clientes)
    print(f"  -> {n_clientes} Clientes done")

    print(f"  Interacciones ({len(interacciones)}) ...")
    n_interacciones = await _ingest_nodes(client, "Interaccion", interacciones)
    print(f"  -> {n_interacciones} Interacciones done")

    print(f"  PromesasPago ({len(promesas)}) ...")
    n_promesas = await _ingest_nodes(client, "PromesaPago", promesas)
    print(f"  -> {n_promesas} PromesasPago done")

    print(f"  Pagos ({len(pagos)}) ...")
    n_pagos = await _ingest_nodes(client, "Pago", pagos)
    print(f"  -> {n_pagos} Pagos done")

    print(f"  PlanesPago ({len(planes)}) ...")
    n_planes = await _ingest_nodes(client, "PlanPago", planes)
    print(f"  -> {n_planes} PlanesPago done")

    print(f"  EstadosDeuda ({len(estados_deuda)}) ...")
    n_estados = await _ingest_nodes(client, "EstadoDeuda", estados_deuda)
    print(f"  -> {n_estados} EstadosDeuda done")

    # 6. Ingest relationships
    print(f"\n[ingest] Ingesting {len(relationships)} relationships ...")
    n_rels = await _ingest_relationships(client, relationships)
    print(f"  -> {n_rels} relationships done")

    # 6b. Episodios semánticos
    if graphiti_online:
        print(f"\n[ingest] Ingesting {len(dataset.interacciones)} semantic episodes ...")
        n_episodes = 0
        for raw_ix in dataset.interacciones:
            episode_body = json.dumps(
                {
                    "id": raw_ix.id,
                    "cliente_id": raw_ix.cliente_id,
                    "agente_id": raw_ix.agente_id,
                    "tipo": raw_ix.tipo,
                    "resultado": raw_ix.resultado,
                    "timestamp": raw_ix.timestamp,
                    "duracion_segundos": raw_ix.duracion_segundos,
                    "sentimiento": raw_ix.sentimiento,
                    "monto_prometido": raw_ix.monto_prometido,
                    "monto": raw_ix.monto,
                },
                ensure_ascii=False,
                default=str,
            )
            try:
                ref_time = datetime.fromisoformat(
                    raw_ix.timestamp.rstrip("Z")
                ).replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError):
                ref_time = datetime.now(tz=timezone.utc)

            ok = await client.add_episode(
                name=f"interaccion_{raw_ix.id}",
                body=episode_body,
                reference_time=ref_time,
                source_description="cobranza — interaccion cliente",
            )
            if ok:
                n_episodes += 1
            if n_episodes and n_episodes % PROGRESS_INTERVAL == 0:
                print(f"  [episodes] {n_episodes}/{len(dataset.interacciones)} ...")
        print(f"  -> {n_episodes} episodes done (0 = LLM no configurado, no crítico)")

    # 7. Build summary
    elapsed = round(time.time() - start_time, 2)
    nodes_by_label = client.count_nodes_by_label()
    rels_by_type = client.count_rels_by_type()

    n_cumplidas = sum(1 for p in promesas if p.cumplida)

    summary: Dict[str, Any] = {
        "ingesta_completada_en": datetime.now(tz=timezone.utc).isoformat(),
        "duracion_segundos": elapsed,
        "backend": "graphiti" if graphiti_online else "sqlite",
        "db_path": client.db_path if not graphiti_online else None,
        "validacion": {
            "warnings": len(warnings),
            "warning_messages": warnings,
        },
        "nodos": {
            "total": client.count_nodes(),
            "por_etiqueta": nodes_by_label,
        },
        "relaciones": {
            "total": client.count_relationships(),
            "por_tipo": rels_by_type,
        },
        "estadisticas": {
            "total_clientes": len(clientes),
            "total_agentes": len(agentes),
            "total_interacciones": len(interacciones),
            "total_promesas": len(promesas),
            "promesas_cumplidas": n_cumplidas,
            "tasa_cumplimiento_global": (
                round(n_cumplidas / len(promesas), 4) if promesas else 0.0
            ),
            "total_pagos": len(pagos),
            "total_planes_pago": len(planes),
        },
    }

    # 8. Write summary file
    with open(SUMMARY_FILE, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False, default=str)
    print(f"\n[done] Summary written to: {SUMMARY_FILE}")

    # 9. Print final report
    print("\n" + "=" * 60)
    print("  INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Backend      : {summary['backend'].upper()}")
    print(f"  Duration     : {elapsed}s")
    print(f"  Total nodes  : {summary['nodos']['total']}")
    print(f"  Total rels   : {summary['relaciones']['total']}")
    print(f"  Nodes detail : {nodes_by_label}")
    print(f"  Rels detail  : {rels_by_type}")
    print(f"  Warnings     : {len(warnings)}")
    print("=" * 60)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
