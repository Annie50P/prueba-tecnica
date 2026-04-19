"""
GraphitiService — toda la lógica de consulta del grafo para la API.

Acceso a datos 100 % via `api.repositories.get_backend()` (B1).
El servicio es agnóstico al backend: funciona tanto con SQLite local
como con Neo4j+Graphiti real (GRAPH_BACKEND=graphiti).

Schema semántico (compartido entre ambos backends):
  - Cliente, Agente, Interaccion, PromesaPago, Pago, PlanPago (labels)
  - TIENE_INTERACCION, CONDUJO, GENERO_PAGO, GENERO_PROMESA, GENERO_PLAN,
    SIGUIENTE, CUMPLE_PROMESA (rel_types)
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from typing import Any, Optional

from api.repositories import get_backend

logger = logging.getLogger(__name__)

try:
    from api.config import settings as _settings  # type: ignore
    _CUMPLIDA_MODE = (
        getattr(_settings, "promesa_cumplida_mode", "snapshot") or "snapshot"
    ).lower()
    _GRACE_DAYS = int(getattr(_settings, "promesa_grace_days", 3) or 3)
except Exception:  # pragma: no cover
    _CUMPLIDA_MODE = os.environ.get("PROMESA_CUMPLIDA_MODE", "snapshot").lower()
    try:
        _GRACE_DAYS = int(os.environ.get("PROMESA_GRACE_DAYS", "3"))
    except (TypeError, ValueError):
        _GRACE_DAYS = 3


# ---------------------------------------------------------------------------
# Helpers — tiempo + resolución dinámica de cumplida (C4)
# ---------------------------------------------------------------------------

def _parse_ts_safe(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, AttributeError):
        return None


async def _is_cumplida_dynamic(promesa_props: dict) -> bool:
    """
    C4 — compute-on-read: existe un pago del mismo cliente en la ventana
    [fecha_promesa, fecha_promesa + grace_days].
    """
    cliente_id = promesa_props.get("cliente_id")
    fecha_promesa_raw = (
        promesa_props.get("fecha_promesa") or promesa_props.get("fecha")
    )
    if not cliente_id or not fecha_promesa_raw:
        return bool(promesa_props.get("cumplida"))

    try:
        fecha_promesa_date = date.fromisoformat(str(fecha_promesa_raw))
    except ValueError:
        return bool(promesa_props.get("cumplida"))

    start = datetime.combine(fecha_promesa_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    deadline = datetime.combine(
        fecha_promesa_date + timedelta(days=_GRACE_DAYS), datetime.min.time()
    ).replace(tzinfo=timezone.utc)

    backend = get_backend()
    interacciones = await backend.get_outgoing_nodes(
        cliente_id, "TIENE_INTERACCION", "Interaccion"
    )
    for inter in interacciones:
        p = inter["properties"]
        if p.get("tipo") != "pago_recibido":
            continue
        ts = _parse_ts_safe(p.get("timestamp") or p.get("fecha"))
        if ts is None:
            continue
        if start <= ts <= deadline:
            return True
    return False


async def _resolve_cumplida(promesa_props: dict) -> bool:
    """Usa snapshot o dynamic según settings.promesa_cumplida_mode (C4)."""
    if _CUMPLIDA_MODE == "dynamic":
        return await _is_cumplida_dynamic(promesa_props)
    return bool(promesa_props.get("cumplida"))


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

_LLAMADA_TIPOS = {"llamada_saliente", "llamada_entrante"}


async def get_all_clientes() -> list[dict]:
    """
    Bulk load: 4 queries totales.
    Pago, PromesaPago e Interaccion tienen cliente_id en sus propiedades,
    por lo que se agrupan en memoria sin traversal por cliente.
    """
    backend = get_backend()

    clientes, all_pagos, all_promesas, all_inters = await asyncio.gather(
        backend.get_nodes_by_label("Cliente"),
        backend.get_nodes_by_label("Pago"),
        backend.get_nodes_by_label("PromesaPago"),
        backend.get_nodes_by_label("Interaccion"),
    )

    pagos_by_client: dict[str, list] = defaultdict(list)
    for p in all_pagos:
        cid = p["properties"].get("cliente_id")
        if cid:
            pagos_by_client[cid].append(p)

    promesas_by_client: dict[str, list] = defaultdict(list)
    for p in all_promesas:
        if p["properties"].get("numero_cuota") is not None:
            continue
        cid = p["properties"].get("cliente_id")
        if cid:
            promesas_by_client[cid].append(p)

    inters_by_client: dict[str, list] = defaultdict(list)
    for i in all_inters:
        cid = i["properties"].get("cliente_id")
        if cid:
            inters_by_client[cid].append(i)

    fecha_referencia = datetime.now(timezone.utc)

    result = []
    for c in clientes:
        cliente_id = c["id"]
        props = c["properties"]

        pagos = pagos_by_client.get(cliente_id, [])
        total_pagado = sum((p["properties"].get("monto", 0) or 0) for p in pagos)

        promesas = promesas_by_client.get(cliente_id, [])
        total_promesas = len(promesas)

        # Pre-calcular cumplida por promesa respetando el modo configurado
        if _CUMPLIDA_MODE == "dynamic":
            cumplida_status = []
            for p in promesas:
                is_c = await _resolve_cumplida({**p["properties"], "cliente_id": cliente_id})
                cumplida_status.append(is_c)
        else:
            cumplida_status = [bool(p["properties"].get("cumplida")) for p in promesas]

        promesas_cumplidas = sum(cumplida_status)

        # None cuando no hay promesas — distinto de 0 (hubo promesas y no se cumplieron)
        tasa_cumplimiento: Optional[float] = (
            round(promesas_cumplidas / total_promesas, 4) if total_promesas > 0 else None
        )
        monto_deuda = props.get("monto_deuda_inicial", 0) or 0

        # Tasa de recuperación real (pagado / deuda inicial)
        tasa_recuperacion = (
            round(total_pagado / monto_deuda, 4) if monto_deuda > 0 else 0.0
        )

        # Monto prometido pendiente (promesas no cumplidas) — usa mismo cumplida_status
        monto_prometido_pendiente = sum(
            float(p["properties"].get("monto_prometido", 0) or 0)
            for p, is_c in zip(promesas, cumplida_status)
            if not is_c
        )

        # Métricas derivadas de interacciones
        inters = inters_by_client.get(cliente_id, [])
        total_llamadas = len(inters)
        ultima_interaccion: Optional[str] = None
        dias_sin_contacto: Optional[int] = None
        ultimo_agente_id: Optional[str] = None
        # Sentimiento solo de llamadas, excluyendo 'n/a'
        sent_counts: dict[str, int] = {}
        last_ts_raw: Optional[str] = None

        for i in inters:
            ip = i["properties"]
            ts_raw = ip.get("timestamp") or ip.get("fecha")
            tipo = (ip.get("tipo") or "").lower()

            # Sentimiento: solo llamadas y solo valores reales (no n/a)
            if tipo in _LLAMADA_TIPOS:
                sent = ip.get("sentimiento_cliente") or ip.get("sentimiento")
                if sent and sent.lower() not in ("n/a", "na", ""):
                    sent_counts[sent] = sent_counts.get(sent, 0) + 1

            if ts_raw:
                if last_ts_raw is None or str(ts_raw) > str(last_ts_raw):
                    last_ts_raw = str(ts_raw)
                    if ip.get("agente_id"):
                        ultimo_agente_id = ip["agente_id"]

        if last_ts_raw:
            ultima_interaccion = last_ts_raw
            dt = _parse_ts_safe(last_ts_raw)
            if dt:
                dias_sin_contacto = (fecha_referencia - dt).days

        # None = sin datos de llamadas; distinto de tener llamadas sin sentimiento capturado
        sentimiento_predominante = (
            max(sent_counts, key=lambda k: sent_counts[k]) if sent_counts else None
        )

        result.append(
            {
                "id": cliente_id,
                "label": "Cliente",
                **props,
                "total_pagado": round(total_pagado, 2),
                "monto_pendiente": round(max(0, monto_deuda - total_pagado), 2),
                "tasa_recuperacion": tasa_recuperacion,
                "tasa_cumplimiento": tasa_cumplimiento,
                "monto_prometido_pendiente": round(monto_prometido_pendiente, 2),
                "total_llamadas": total_llamadas,
                "ultima_interaccion": ultima_interaccion,
                "dias_sin_contacto": dias_sin_contacto,
                "ultimo_agente_id": ultimo_agente_id,
                "sentimiento_predominante": sentimiento_predominante,
            }
        )
    return result


async def get_cliente_by_id(cliente_id: str) -> Optional[dict]:
    backend = get_backend()
    node = await backend.get_node(cliente_id)
    if not node or node["label"] != "Cliente":
        return None

    props = node["properties"]

    interacciones_nodes, promesas_nodes, pagos_nodes, planes_nodes = await asyncio.gather(
        backend.get_outgoing_nodes(cliente_id, "TIENE_INTERACCION", "Interaccion"),
        backend.get_two_hop_nodes(
            cliente_id, "TIENE_INTERACCION", "Interaccion", "GENERO_PROMESA", "PromesaPago"
        ),
        backend.get_two_hop_nodes(
            cliente_id, "TIENE_INTERACCION", "Interaccion", "GENERO_PAGO", "Pago"
        ),
        backend.get_two_hop_nodes(
            cliente_id, "TIENE_INTERACCION", "Interaccion", "GENERO_PLAN", "PlanPago"
        ),
    )

    interacciones = [{"id": i["id"], **i["properties"]} for i in interacciones_nodes]
    promesas = [
        {"id": p["id"], **p["properties"]} for p in promesas_nodes
        if p["properties"].get("numero_cuota") is None
    ]
    pagos = [{"id": p["id"], **p["properties"]} for p in pagos_nodes]
    planes = [{"id": p["id"], **p["properties"]} for p in planes_nodes]

    total_pagado = sum((p.get("monto", 0) or 0) for p in pagos)
    monto_deuda = props.get("monto_deuda_inicial", 0) or 0

    tasa_recuperacion = round(total_pagado / monto_deuda, 4) if monto_deuda > 0 else 0.0

    total_promesas = len(promesas)
    promesas_cumplidas_count = sum(1 for p in promesas if p.get("cumplida"))
    tasa_cumplimiento: Optional[float] = (
        round(promesas_cumplidas_count / total_promesas, 4) if total_promesas > 0 else None
    )

    monto_prometido_pendiente = sum(
        float(p.get("monto_prometido", 0) or 0)
        for p in promesas
        if not p.get("cumplida")
    )

    # Fecha referencia = max timestamp del propio cliente (relativo al dataset)
    ts_list = [
        str(i.get("timestamp") or i.get("fecha"))
        for i in interacciones
        if i.get("timestamp") or i.get("fecha")
    ]
    ultima_interaccion = max(ts_list, default=None)
    fecha_ref_cliente = _parse_ts_safe(ultima_interaccion) if ultima_interaccion else None

    # Para el detalle usamos el max global del cliente como referencia,
    # pero necesitamos una referencia del dataset — usamos la fecha más reciente del cliente
    # comparada contra sus propias interacciones para calcular días relativos.
    # Si solo hay un cliente, la referencia es su propia última interacción (días = 0).
    # En la práctica, el analista ve la fecha absoluta también.
    dias_sin_contacto: Optional[int] = None
    if ultima_interaccion:
        dt = _parse_ts_safe(ultima_interaccion)
        if dt and fecha_ref_cliente:
            # Usamos datetime.now solo como fallback; en detalle se muestra fecha absoluta
            dias_sin_contacto = (datetime.now(timezone.utc) - dt).days

    # Último agente, sentimiento (solo llamadas, sin n/a) y mejor horario
    ultimo_agente_id: Optional[str] = None
    sent_counts: dict[str, int] = {}
    last_ts: Optional[str] = None
    hora_counts: dict[int, int] = {}

    for i in interacciones:
        ts = str(i.get("timestamp") or i.get("fecha") or "")
        tipo = (i.get("tipo") or "").lower()
        if ts and (last_ts is None or ts > last_ts):
            last_ts = ts
            if i.get("agente_id"):
                ultimo_agente_id = i["agente_id"]
        # Sentimiento solo de llamadas, excluyendo n/a
        if tipo in _LLAMADA_TIPOS:
            sent = i.get("sentimiento_cliente") or i.get("sentimiento")
            if sent and sent.lower() not in ("n/a", "na", ""):
                sent_counts[sent] = sent_counts.get(sent, 0) + 1
        h = _extract_hour(i.get("timestamp") or i.get("fecha"))
        if h is not None:
            hora_counts[h] = hora_counts.get(h, 0) + 1

    sentimiento_predominante = (
        max(sent_counts, key=lambda k: sent_counts[k]) if sent_counts else None
    )
    mejor_horario_contacto: Optional[str] = None
    if hora_counts:
        bh = max(hora_counts, key=lambda h: hora_counts[h])
        mejor_horario_contacto = f"{bh:02d}:00 - {(bh + 1) % 24:02d}:00"

    return {
        "id": cliente_id,
        "label": "Cliente",
        **props,
        "interacciones": interacciones,
        "promesas": promesas,
        "pagos": pagos,
        "planes": planes,
        "total_pagado": round(total_pagado, 2),
        "monto_pendiente": round(max(0, monto_deuda - total_pagado), 2),
        "tasa_recuperacion": tasa_recuperacion,
        "tasa_cumplimiento": tasa_cumplimiento,
        "monto_prometido_pendiente": round(monto_prometido_pendiente, 2),
        "ultima_interaccion": ultima_interaccion,
        "dias_sin_contacto": dias_sin_contacto,
        "ultimo_agente_id": ultimo_agente_id,
        "sentimiento_predominante": sentimiento_predominante,
        "mejor_horario_contacto": mejor_horario_contacto,
    }


async def get_cliente_timeline(cliente_id: str) -> Optional[list[dict]]:
    backend = get_backend()
    node = await backend.get_node(cliente_id)
    if not node or node["label"] != "Cliente":
        return None

    interacciones = await backend.get_outgoing_nodes(
        cliente_id, "TIENE_INTERACCION", "Interaccion"
    )

    timeline = []
    for i in interacciones:
        inter_id = i["id"]
        props = i["properties"]

        promesas = [
            {"id": p["id"], **p["properties"]}
            for p in await backend.get_outgoing_nodes(inter_id, "GENERO_PROMESA", "PromesaPago")
        ]
        pagos = [
            {"id": p["id"], **p["properties"]}
            for p in await backend.get_outgoing_nodes(inter_id, "GENERO_PAGO", "Pago")
        ]
        planes = [
            {"id": p["id"], **p["properties"]}
            for p in await backend.get_outgoing_nodes(inter_id, "GENERO_PLAN", "PlanPago")
        ]

        timeline.append(
            {
                "interaccion_id": inter_id,
                **props,
                "promesas": promesas,
                "pagos": pagos,
                "planes": planes,
            }
        )

    def _sort_key(item: dict):
        return item.get("timestamp") or item.get("fecha") or ""

    timeline.sort(key=_sort_key)
    return timeline


# ---------------------------------------------------------------------------
# Agentes
# ---------------------------------------------------------------------------

def _extract_hour(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        return dt.hour
    except (ValueError, AttributeError):
        try:
            parts = str(timestamp).split("T")
            if len(parts) == 2:
                return int(parts[1][:2])
        except Exception:
            return None
    return None


async def get_all_agentes() -> list[dict]:
    backend = get_backend()
    agentes = await backend.get_nodes_by_label("Agente")

    # Bulk: una query para todas las interacciones, agrupadas por agente_id en memoria.
    all_interacciones = await backend.get_nodes_by_label("Interaccion")
    inters_by_agente: dict[str, list] = defaultdict(list)
    for i in all_interacciones:
        aid = i["properties"].get("agente_id")
        if aid:
            inters_by_agente[aid].append(i)

    result = []
    for a in agentes:
        agente_id = a["id"]
        props = a["properties"]

        interacciones = inters_by_agente.get(agente_id, [])
        total_llamadas = len(interacciones)
        promesas = 0
        pagos_inmediatos = 0
        for i in interacciones:
            res = (i["properties"].get("resultado") or "").lower()
            if "promesa" in res:
                promesas += 1
            if "pago_inmediato" in res or "pago inmediato" in res:
                pagos_inmediatos += 1

        tasa_promesa = round(promesas / total_llamadas, 4) if total_llamadas > 0 else 0.0
        tasa_pago_inmediato = (
            round(pagos_inmediatos / total_llamadas, 4) if total_llamadas > 0 else 0.0
        )

        result.append(
            {
                "id": agente_id,
                "label": "Agente",
                **props,
                "total_llamadas": total_llamadas,
                "tasa_promesa": tasa_promesa,
                "tasa_pago_inmediato": tasa_pago_inmediato,
            }
        )
    return result


async def get_agente_efectividad(agente_id: str) -> Optional[dict]:
    backend = get_backend()
    node = await backend.get_node(agente_id)
    if not node or node["label"] != "Agente":
        return None

    props = node["properties"]
    interacciones = await backend.get_outgoing_nodes(agente_id, "CONDUJO", "Interaccion")
    total_llamadas = len(interacciones)

    distribucion_resultados: dict[str, int] = {}
    distribucion_sentimientos: dict[str, int] = {}
    hour_results: dict[int, dict[str, int]] = {}
    # week_key → {"total": int, "exitos": int}
    semana_results: dict[str, dict] = {}

    promesas = 0
    pagos_inmediatos = 0
    negaciones = 0
    sin_respuesta = 0

    inter_ids: list[str] = []

    for i in interacciones:
        ip = i["properties"]
        resultado = ip.get("resultado") or "desconocido"
        sentimiento = (
            ip.get("sentimiento_cliente") or ip.get("sentimiento") or "desconocido"
        )

        distribucion_resultados[resultado] = (
            distribucion_resultados.get(resultado, 0) + 1
        )
        distribucion_sentimientos[sentimiento] = (
            distribucion_sentimientos.get(sentimiento, 0) + 1
        )

        resultado_lower = resultado.lower()
        es_exito = False
        if "promesa" in resultado_lower:
            promesas += 1
            es_exito = True
        if "pago_inmediato" in resultado_lower or "pago inmediato" in resultado_lower:
            pagos_inmediatos += 1
            es_exito = True
        if "niega" in resultado_lower or "se_niega" in resultado_lower:
            negaciones += 1
        if "sin_respuesta" in resultado_lower or "sin respuesta" in resultado_lower:
            sin_respuesta += 1

        ts_raw = ip.get("timestamp") or ip.get("fecha")
        hour = _extract_hour(ts_raw)
        if hour is not None:
            hour_results.setdefault(hour, {})
            hour_results[hour][resultado] = hour_results[hour].get(resultado, 0) + 1

        # Agrupar por semana ISO (YYYY-Www)
        if ts_raw:
            try:
                dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                week_key = dt.strftime("%Y-W%W")
                semana_results.setdefault(week_key, {"total": 0, "exitos": 0})
                semana_results[week_key]["total"] += 1
                if es_exito:
                    semana_results[week_key]["exitos"] += 1
            except (ValueError, AttributeError):
                pass

        inter_ids.append(i["id"])

    mejor_horario = None
    if hour_results:
        best_hour = max(
            hour_results.keys(),
            key=lambda h: sum(
                v
                for k, v in hour_results[h].items()
                if "promesa" in k.lower() or "pago" in k.lower()
            ),
        )
        mejor_horario = f"{best_hour:02d}:00 - {(best_hour + 1) % 24:02d}:00"

    tasa_promesa = (
        round(promesas / total_llamadas, 4) if total_llamadas > 0 else 0.0
    )
    tasa_pago_inmediato = (
        round(pagos_inmediatos / total_llamadas, 4) if total_llamadas > 0 else 0.0
    )
    tasa_exito = (
        round((promesas + pagos_inmediatos) / total_llamadas, 4)
        if total_llamadas > 0
        else 0.0
    )
    tasa_fracaso = (
        round((negaciones + sin_respuesta) / total_llamadas, 4)
        if total_llamadas > 0
        else 0.0
    )

    # Monto prometido total + cumplimiento: Interaccion -GENERO_PROMESA-> PromesaPago
    # (Los pagos no se pueden atribuir a agentes — pago_recibido no lleva agente_id)
    monto_prometido_total = 0.0
    promesas_generadas = 0
    promesas_cumplidas_agente = 0
    for inter_id in inter_ids:
        promesas_inter = await backend.get_outgoing_nodes(
            inter_id, "GENERO_PROMESA", "PromesaPago"
        )
        for p in promesas_inter:
            promesas_generadas += 1
            monto_prometido_total += float(p["properties"].get("monto_prometido", 0) or 0)
            if await _resolve_cumplida(p["properties"]):
                promesas_cumplidas_agente += 1

    tasa_cumplimiento_promesas = (
        round(promesas_cumplidas_agente / promesas_generadas, 4)
        if promesas_generadas > 0
        else None
    )

    # Actividad horaria serializable: lista ordenada por hora
    actividad_por_hora = [
        {
            "hora": f"{h:02d}:00",
            "total": sum(v for v in hr.values()),
            "exitos": sum(
                v for k, v in hr.items()
                if "promesa" in k.lower() or "pago" in k.lower()
            ),
            "distribucion": hr,
        }
        for h, hr in sorted(hour_results.items())
    ]

    # Tendencia semanal ordenada
    tendencia_semanal = [
        {
            "semana": wk,
            "total": d["total"],
            "exitos": d["exitos"],
            "tasa_exito": round(d["exitos"] / d["total"], 4) if d["total"] > 0 else 0.0,
        }
        for wk, d in sorted(semana_results.items())
    ]

    return {
        "id": agente_id,
        **props,
        "total_llamadas": total_llamadas,
        "tasa_promesa": tasa_promesa,
        "tasa_pago_inmediato": tasa_pago_inmediato,
        "tasa_exito": tasa_exito,
        "tasa_fracaso": tasa_fracaso,
        "monto_prometido_total": round(monto_prometido_total, 2),
        "promesas_generadas": promesas_generadas,
        "tasa_cumplimiento_promesas": tasa_cumplimiento_promesas,
        "distribucion_resultados": distribucion_resultados,
        "distribucion_sentimientos": distribucion_sentimientos,
        "mejor_horario": mejor_horario,
        "actividad_por_hora": actividad_por_hora,
        "tendencia_semanal": tendencia_semanal,
    }


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

async def _cliente_de_promesa(promesa_id: str) -> str | None:
    """
    Resuelve el cliente_id asociado a una promesa haciendo dos saltos inversos:
    PromesaPago <-GENERO_PROMESA- Interaccion <-TIENE_INTERACCION- Cliente.
    """
    backend = get_backend()
    incoming_promesa = await backend.get_incoming(promesa_id, "GENERO_PROMESA")
    if not incoming_promesa:
        return None
    interaccion_id = incoming_promesa[0]["from_id"]
    incoming_inter = await backend.get_incoming(interaccion_id, "TIENE_INTERACCION")
    if not incoming_inter:
        return None
    return incoming_inter[0]["from_id"]


async def get_promesas_incumplidas(fecha: Optional[str] = None) -> list[dict]:
    ref_date = date.fromisoformat(fecha) if fecha else date.today()

    backend = get_backend()
    promesas = await backend.get_nodes_by_label("PromesaPago")

    result = []
    for p in promesas:
        props = dict(p["properties"])
        promesa_id = p["id"]

        # Excluir cuotas automáticas de PlanPago
        if props.get("numero_cuota") is not None:
            continue

        if "cliente_id" not in props:
            cid = await _cliente_de_promesa(promesa_id)
            if cid:
                props["cliente_id"] = cid

        if await _resolve_cumplida(props):
            continue

        fecha_promesa_str = props.get("fecha_promesa") or props.get("fecha") or ""

        if fecha and fecha_promesa_str and fecha_promesa_str > fecha:
            continue

        dias_hasta: int | None = None
        if fecha_promesa_str:
            try:
                dias_hasta = (date.fromisoformat(fecha_promesa_str) - ref_date).days
            except ValueError:
                dias_hasta = None

        result.append(
            {
                "id": promesa_id,
                **{k: v for k, v in props.items() if k != "cliente_id"},
                "cliente_id": props.get("cliente_id"),
                "dias_hasta_vencimiento": dias_hasta,
                "dias_vencida": (
                    -dias_hasta
                    if dias_hasta is not None and dias_hasta < 0
                    else 0
                ),
            }
        )
    return result


async def get_mejores_horarios(resultado: Optional[str] = None) -> dict:
    backend = get_backend()
    interacciones = await backend.get_nodes_by_label("Interaccion")

    hour_stats: dict[int, dict] = {}

    for i in interacciones:
        props = i["properties"]
        res = props.get("resultado") or ""
        if resultado and resultado.lower() not in res.lower():
            continue

        hour = _extract_hour(props.get("timestamp") or props.get("fecha"))
        if hour is None:
            continue

        hour_stats.setdefault(hour, {"total": 0, "resultados": {}})
        hour_stats[hour]["total"] += 1
        hour_stats[hour]["resultados"][res] = (
            hour_stats[hour]["resultados"].get(res, 0) + 1
        )

    horarios = [
        {
            "hora": f"{h:02d}:00",
            "total_llamadas": s["total"],
            "distribucion_resultados": s["resultados"],
        }
        for h, s in sorted(hour_stats.items())
    ]

    mejor_hora = (
        max(horarios, key=lambda h: h["total_llamadas"])["hora"] if horarios else None
    )

    return {
        "filtro_resultado": resultado,
        "mejor_hora": mejor_hora,
        "detalle_por_hora": horarios,
    }


async def get_dashboard() -> dict:
    backend = get_backend()

    clientes, pagos, promesas, interacciones = await asyncio.gather(
        backend.get_nodes_by_label("Cliente"),
        backend.get_nodes_by_label("Pago"),
        backend.get_nodes_by_label("PromesaPago"),
        backend.get_nodes_by_label("Interaccion"),
    )

    total_deuda_inicial = sum(
        (c["properties"].get("monto_deuda_inicial", 0) or 0) for c in clientes
    )
    distribucion_tipos_deuda: dict[str, int] = {}
    for c in clientes:
        tipo = c["properties"].get("tipo_deuda") or "desconocido"
        distribucion_tipos_deuda[tipo] = distribucion_tipos_deuda.get(tipo, 0) + 1

    total_recuperado = sum((p["properties"].get("monto", 0) or 0) for p in pagos)
    tasa_recuperacion = (
        round(total_recuperado / total_deuda_inicial, 4)
        if total_deuda_inicial > 0
        else 0.0
    )

    # Solo contar promesas directas (excluir cuotas de PlanPago generadas automáticamente)
    promesas_directas = [
        p for p in promesas
        if p["properties"].get("numero_cuota") is None
    ]
    promesas_cumplidas = sum(
        1 for p in promesas_directas if p["properties"].get("cumplida") is True
    )
    promesas_incumplidas = len(promesas_directas) - promesas_cumplidas

    actividad_por_dia: dict[str, dict] = defaultdict(
        lambda: {"llamadas": 0, "pagos": 0}
    )
    for i in interacciones:
        ts = i["properties"].get("timestamp") or i["properties"].get("fecha") or ""
        day = ts[:10] if ts else "sin_fecha"
        actividad_por_dia[day]["llamadas"] += 1
    for p in pagos:
        ts = p["properties"].get("fecha") or p["properties"].get("timestamp") or ""
        day = ts[:10] if ts else "sin_fecha"
        actividad_por_dia[day]["pagos"] += 1

    actividad_lista = [
        {"fecha": d, **v} for d, v in sorted(actividad_por_dia.items())
    ]

    return {
        "total_deuda_inicial": round(total_deuda_inicial, 2),
        "total_recuperado": round(total_recuperado, 2),
        "tasa_recuperacion": tasa_recuperacion,
        "promesas_cumplidas": promesas_cumplidas,
        "promesas_incumplidas": promesas_incumplidas,
        "distribucion_tipos_deuda": distribucion_tipos_deuda,
        "actividad_por_dia": actividad_lista,
    }


# ---------------------------------------------------------------------------
# Evolución de deuda
# ---------------------------------------------------------------------------

async def get_evolucion_deuda(cliente_id: str) -> Optional[list[dict]]:
    backend = get_backend()
    node = await backend.get_node(cliente_id)
    if not node or node["label"] != "Cliente":
        return None

    estados = await backend.get_outgoing_nodes(cliente_id, "ESTADO_DEUDA_EN", "EstadoDeuda")
    if not estados:
        return []

    return sorted(
        [{"id": e["id"], **e["properties"]} for e in estados],
        key=lambda e: e.get("fecha") or "",
    )


# ---------------------------------------------------------------------------
# Grafo (visualización D3.js)
# ---------------------------------------------------------------------------

async def get_grafo_nodos(
    tipos: Optional[list[str]] = None, limite: int = 200
) -> dict:
    backend = get_backend()

    if tipos:
        per_label = max(1, limite // max(1, len(tipos)))
        nodos_raw = []
        total = 0
        for label in tipos:
            if total >= limite:
                break
            remaining = limite - total
            chunk = await backend.get_nodes_by_label(label, limit=min(per_label, remaining))
            for n in chunk:
                nodos_raw.append((n, label))
                total += 1
                if total >= limite:
                    break
    else:
        nodos_raw = []
        for label in ("Cliente", "Agente", "Interaccion", "PromesaPago", "Pago", "PlanPago", "EstadoDeuda"):
            if len(nodos_raw) >= limite:
                break
            remaining = limite - len(nodos_raw)
            chunk = await backend.get_nodes_by_label(label, limit=remaining)
            for n in chunk:
                nodos_raw.append((n, label))
                if len(nodos_raw) >= limite:
                    break

    nodos = [
        {
            "id": n["id"],
            "tipo": label,
            "label": (
                n["properties"].get("nombre")
                or n["properties"].get("id_cliente")
                or n["id"]
            ),
            "propiedades": n["properties"],
        }
        for n, label in nodos_raw
    ]
    return {"nodos": nodos}


async def get_grafo_relaciones(
    cliente_id: Optional[str] = None,
    tipos_relacion: Optional[list[str]] = None,
    profundidad: int = 2,
) -> dict:
    backend = get_backend()

    if cliente_id:
        connected_ids: set[str] = {cliente_id}
        frontier: set[str] = {cliente_id}

        for _ in range(profundidad):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for nid in frontier:
                for e in await backend.get_outgoing(nid):
                    if e["to_id"] not in connected_ids:
                        next_frontier.add(e["to_id"])
                for e in await backend.get_incoming(nid):
                    if e["from_id"] not in connected_ids:
                        next_frontier.add(e["from_id"])
            connected_ids.update(next_frontier)
            frontier = next_frontier

        all_rels = await backend.get_all_relationships(tipos_relacion)
        enlaces = [
            {"source": r["from_id"], "target": r["to_id"], "tipo": r["rel_type"]}
            for r in all_rels
            if r["from_id"] in connected_ids and r["to_id"] in connected_ids
        ]
    else:
        all_rels = await backend.get_all_relationships(tipos_relacion)
        enlaces = [
            {"source": r["from_id"], "target": r["to_id"], "tipo": r["rel_type"]}
            for r in all_rels
        ]

    return {"enlaces": enlaces}
