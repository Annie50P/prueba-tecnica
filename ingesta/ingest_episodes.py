#!/usr/bin/env python3
"""
Ingesta SOLO los episodios semánticos en Graphiti (sin tocar nodos ni relaciones).

Útil cuando el grafo de dominio ya está hidratado en Neo4j pero los episodios
semánticos no se ingirieron (ej: contenedor construido con código viejo).

Usage:
    python ingest_episodes.py

Requiere Neo4j activo y al menos una LLM key (OPENAI_API_KEY).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from dotenv import load_dotenv
    for candidate in [os.path.join(_HERE, ".env"), os.path.join(os.path.dirname(_HERE), ".env")]:
        if os.path.exists(candidate):
            load_dotenv(candidate)
            print(f"[env] Loaded {candidate}")
            break
except ImportError:
    pass

from graphiti_client import GraphitiClient
from validators import validate_dataset

DATA_FILE = os.path.join(os.path.dirname(_HERE), "data", "interacciones_clientes.json")
PROGRESS_INTERVAL = 50


def _build_episode_text(raw_ix, cliente_nombre_map: Dict[str, str]) -> str:
    nombre = cliente_nombre_map.get(raw_ix.cliente_id, raw_ix.cliente_id)
    tipo = raw_ix.tipo
    resultado = raw_ix.resultado or ""
    fecha = raw_ix.timestamp[:10]

    _TIPO_LABEL = {
        "llamada_saliente": "llamada saliente",
        "llamada_entrante": "llamada entrante",
        "pago_recibido": "pago recibido",
        "email": "email",
    }
    _SENT_LABEL = {
        "positivo": "actitud positiva",
        "negativo": "actitud negativa",
        "neutral": "actitud neutral",
    }
    _RESULTADO_LABEL = {
        "promesa_pago": "prometió pagar",
        "pago_inmediato": "realizó pago inmediato",
        "renegociacion": "solicitó renegociación",
        "se_niega": "se negó a pagar",
        "sin_respuesta": "no contestó",
        "sin respuesta": "no contestó",
    }

    parts = [f"El {fecha}"]

    if tipo in ("llamada_saliente", "llamada_entrante"):
        if raw_ix.agente_id:
            parts.append(
                f"el agente {raw_ix.agente_id} realizó una {_TIPO_LABEL[tipo]} "
                f"con el cliente {nombre} (id: {raw_ix.cliente_id})."
            )
        else:
            parts.append(
                f"se registró una {_TIPO_LABEL[tipo]} con el cliente {nombre} "
                f"(id: {raw_ix.cliente_id})."
            )
        if raw_ix.duracion_segundos:
            parts.append(f"La llamada duró {raw_ix.duracion_segundos} segundos.")
        if raw_ix.sentimiento:
            parts.append(f"El cliente mostró {_SENT_LABEL.get(raw_ix.sentimiento, raw_ix.sentimiento)}.")
        if resultado in _RESULTADO_LABEL:
            parts.append(f"El cliente {_RESULTADO_LABEL[resultado]}.")
        if resultado == "promesa_pago" and raw_ix.monto_prometido:
            parts.append(
                f"Prometió pagar ${raw_ix.monto_prometido} antes del {raw_ix.fecha_promesa}."
            )
        if resultado == "renegociacion" and raw_ix.nuevo_plan_pago:
            p = raw_ix.nuevo_plan_pago
            parts.append(
                f"Se acordó un plan de pago de {p.cuotas} cuotas de ${p.monto_mensual} mensuales."
            )

    elif tipo == "pago_recibido":
        monto = raw_ix.monto or 0
        metodo = raw_ix.metodo_pago or "método no especificado"
        completo = "pago total" if raw_ix.pago_completo else "pago parcial"
        parts.append(
            f"el cliente {nombre} (id: {raw_ix.cliente_id}) realizó un {completo} "
            f"de ${monto} mediante {metodo}."
        )

    elif tipo == "email":
        parts.append(f"se envió un email al cliente {nombre} (id: {raw_ix.cliente_id}).")

    return " ".join(parts)


async def main() -> None:
    start = time.time()
    print("=" * 60)
    print("  Ingesta de episodios semánticos (solo episodios)")
    print("=" * 60)

    if not os.path.exists(DATA_FILE):
        print(f"[error] Data file not found: {DATA_FILE}")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    dataset, warnings = validate_dataset(raw)
    print(f"[data] {len(dataset.clientes)} clientes, {len(dataset.interacciones)} interacciones")

    client = GraphitiClient()
    if not await client.health_check():
        print("[error] Neo4j no accesible. Verifica que el contenedor esté corriendo.")
        await client.close()
        sys.exit(1)

    print(f"[neo4j] Conectado OK — group_id: {client.group_id}")

    cliente_nombre_map = {c.id: c.nombre for c in dataset.clientes}

    # Graphiti hace 4-6 llamadas LLM internas por episodio (extracción + deduplicación).
    # 2s entre episodios = ~30 ep/min × 5 llamadas = 150 RPM, bajo el límite de OpenAI paid.
    DELAY_SECONDS = float(os.environ.get("EPISODE_DELAY_SECONDS", "2.0"))
    total = len(dataset.interacciones)
    eta_min = round(total * DELAY_SECONDS / 60, 1)
    print(f"\n[episodes] Ingiriendo {total} episodios semánticos (delay={DELAY_SECONDS}s, ETA ~{eta_min} min) ...")
    n_ok = 0
    n_fail = 0

    for i, raw_ix in enumerate(dataset.interacciones):
        body = _build_episode_text(raw_ix, cliente_nombre_map)
        try:
            ref_time = datetime.fromisoformat(raw_ix.timestamp.rstrip("Z")).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            ref_time = datetime.now(tz=timezone.utc)

        ok = await client.add_episode(
            name=f"interaccion_{raw_ix.id}",
            body=body,
            reference_time=ref_time,
            source_description="cobranza — interaccion cliente",
            episode_type="text",
        )
        if ok:
            n_ok += 1
        else:
            n_fail += 1

        done = n_ok + n_fail
        if done % PROGRESS_INTERVAL == 0:
            print(f"  {done}/{total} — ok={n_ok} fail={n_fail}")

        if i < total - 1:
            await asyncio.sleep(DELAY_SECONDS)

    elapsed = round(time.time() - start, 2)
    print(f"\n[done] {n_ok} episodios ingeridos, {n_fail} fallidos — {elapsed}s")

    if n_ok == 0:
        print("\n[warn] Todos fallaron. Causas comunes:")
        print("  - OPENAI_API_KEY no configurada o inválida")
        print("  - graphiti-core no instalado (pip install graphiti-core)")
        print("  - Neo4j sin APOC plugin")
    else:
        print(f"\n[ok] Búsqueda semántica disponible en /analytics/busqueda-semantica")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
