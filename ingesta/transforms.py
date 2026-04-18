"""
Transforms a validated RawDataset into graph nodes and relationships.

Derived properties computed here:
- Interaccion : hora_del_dia, dia_semana
- PromesaPago : cumplida   (dias_hasta_vencimiento se calcula on-read en la API)
- PlanPago    : monto_total_plan, fecha_inicio
- Cliente     : total_pagado, monto_pendiente, tasa_cumplimiento
- Agente      : total_llamadas, tasa_promesa, tasa_pago_inmediato
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

try:
    # Cuando `ingesta/` está en sys.path (ingest.py como script).
    from models import (
        AgenteNode,
        ClienteNode,
        EstadoDeudaNode,
        InteraccionNode,
        PagoNode,
        PlanPagoNode,
        PromesaPagoNode,
        RawDataset,
        RelationRecord,
    )
except ImportError:
    # Cuando se importa como `from ingesta import transforms` (tests).
    from ingesta.models import (  # type: ignore[no-redef]
        AgenteNode,
        ClienteNode,
        EstadoDeudaNode,
        InteraccionNode,
        PagoNode,
        PlanPagoNode,
        PromesaPagoNode,
        RawDataset,
        RelationRecord,
    )

LLAMADA_TIPOS = {"llamada_saliente", "llamada_entrante"}

# Días de gracia para considerar un pago como cumplimiento de una promesa vencida.
# Parametrizable via env var: negocio puede mover esta política sin redeploy.
GRACE_DAYS_DEFAULT = 3


def _get_grace_days() -> int:
    try:
        return int(os.environ.get("PROMESA_GRACE_DAYS", GRACE_DAYS_DEFAULT))
    except (TypeError, ValueError):
        return GRACE_DAYS_DEFAULT


def _today_utc():
    """Fecha actual UTC. Función (no constante de módulo) para evitar drift."""
    return datetime.now(tz=timezone.utc).date()


def _parse_ts(ts_str: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a timezone-aware datetime."""
    ts_str = ts_str.rstrip("Z")
    dt = datetime.fromisoformat(ts_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_date(date_str: str):
    """Parse a YYYY-MM-DD date string."""
    return date.fromisoformat(date_str)


# ---------------------------------------------------------------------------
# Main transform entry-point
# ---------------------------------------------------------------------------

def transform(
    dataset: RawDataset,
) -> Tuple[
    List[AgenteNode],
    List[ClienteNode],
    List[InteraccionNode],
    List[PromesaPagoNode],
    List[PagoNode],
    List[PlanPagoNode],
    List[EstadoDeudaNode],
    List[RelationRecord],
]:
    """Return all nodes and relationships derived from *dataset*."""

    # ------------------------------------------------------------------
    # Pass 1 – build Interaccion nodes and collect secondary nodes
    # ------------------------------------------------------------------
    today_utc = _today_utc()
    grace_days = _get_grace_days()

    interacciones: List[InteraccionNode] = []
    promesas: List[PromesaPagoNode] = []
    pagos: List[PagoNode] = []
    planes: List[PlanPagoNode] = []

    # Accumulator maps
    agente_calls: Dict[str, List[str]] = defaultdict(list)   # agente_id -> [resultado]
    cliente_pagos: Dict[str, List[PagoNode]] = defaultdict(list)
    cliente_promesas: Dict[str, List[PromesaPagoNode]] = defaultdict(list)

    # Map interaccion_id -> parsed timestamp (needed later for SIGUIENTE)
    ix_ts_map: Dict[str, datetime] = {}
    # Map interaccion_id -> RawInteraccion (needed for CUMPLE_PROMESA lookup)
    ix_raw_map = {ix.id: ix for ix in dataset.interacciones}

    for raw_ix in dataset.interacciones:
        dt = _parse_ts(raw_ix.timestamp)
        ix_ts_map[raw_ix.id] = dt

        hora = dt.hour            # 0-23 UTC
        dia = dt.weekday()        # 0=Monday

        ix_node = InteraccionNode(
            id=raw_ix.id,
            cliente_id=raw_ix.cliente_id,
            timestamp=raw_ix.timestamp,
            tipo=raw_ix.tipo,
            duracion_segundos=raw_ix.duracion_segundos,
            agente_id=raw_ix.agente_id,
            resultado=raw_ix.resultado,
            sentimiento=raw_ix.sentimiento,
            hora_del_dia=hora,
            dia_semana=dia,
        )
        interacciones.append(ix_node)

        # ---- PromesaPago ----
        if raw_ix.tipo in LLAMADA_TIPOS and raw_ix.resultado == "promesa_pago":
            # dias_hasta_vencimiento NO se precomputa: es función de la fecha actual.
            # La API lo calcula on-read desde fecha_promesa.
            promesa = PromesaPagoNode(
                id=f"{raw_ix.id}_promesa",
                interaccion_id=raw_ix.id,
                cliente_id=raw_ix.cliente_id,
                monto_prometido=raw_ix.monto_prometido or 0.0,
                fecha_promesa=raw_ix.fecha_promesa,
                cumplida=False,          # resolved in pass 2
            )
            promesas.append(promesa)
            cliente_promesas[raw_ix.cliente_id].append(promesa)

        # ---- Pago ----
        if raw_ix.tipo == "pago_recibido":
            pago = PagoNode(
                id=f"{raw_ix.id}_pago",
                interaccion_id=raw_ix.id,
                cliente_id=raw_ix.cliente_id,
                monto=raw_ix.monto or 0.0,
                metodo_pago=raw_ix.metodo_pago or "",
                pago_completo=raw_ix.pago_completo or False,
                timestamp=raw_ix.timestamp,
            )
            pagos.append(pago)
            cliente_pagos[raw_ix.cliente_id].append(pago)

        # ---- PlanPago ----
        if raw_ix.tipo in LLAMADA_TIPOS and raw_ix.resultado == "renegociacion":
            plan_pago = raw_ix.nuevo_plan_pago
            if plan_pago:
                plan = PlanPagoNode(
                    id=f"{raw_ix.id}_plan",
                    interaccion_id=raw_ix.id,
                    cliente_id=raw_ix.cliente_id,
                    cuotas=plan_pago.cuotas,
                    monto_mensual=plan_pago.monto_mensual,
                    monto_total_plan=round(plan_pago.cuotas * plan_pago.monto_mensual, 2),
                    fecha_inicio=raw_ix.timestamp,
                )
                planes.append(plan)

                # Generar una PromesaPago por cuota del plan (rastreabilidad individual)
                try:
                    fecha_inicio_date = date.fromisoformat(raw_ix.timestamp[:10])
                except ValueError:
                    fecha_inicio_date = _today_utc()

                for n in range(1, plan_pago.cuotas + 1):
                    fecha_cuota = fecha_inicio_date + timedelta(days=30 * n)
                    cuota = PromesaPagoNode(
                        id=f"{plan.id}_cuota_{n}",
                        interaccion_id=raw_ix.id,
                        cliente_id=raw_ix.cliente_id,
                        monto_prometido=plan_pago.monto_mensual,
                        fecha_promesa=fecha_cuota.isoformat(),
                        cumplida=False,
                        numero_cuota=n,
                        plan_pago_id=plan.id,
                    )
                    promesas.append(cuota)
                    cliente_promesas[raw_ix.cliente_id].append(cuota)

        # ---- Agente call accumulation ----
        if raw_ix.tipo in LLAMADA_TIPOS and raw_ix.agente_id:
            agente_calls[raw_ix.agente_id].append(raw_ix.resultado or "")

    # ------------------------------------------------------------------
    # Pass 2 – resolve PromesaPago.cumplida via CUMPLE_PROMESA logic
    # ------------------------------------------------------------------
    for promesa in promesas:
        promesa_ix = ix_raw_map[promesa.interaccion_id]
        promesa_dt = ix_ts_map[promesa.interaccion_id]
        fecha_promesa_date = _parse_date(promesa.fecha_promesa)
        deadline = datetime.combine(
            fecha_promesa_date + timedelta(days=grace_days), datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        # Find any payment from same client after promesa timestamp and within deadline
        for pago in cliente_pagos.get(promesa.cliente_id, []):
            pago_dt = _parse_ts(pago.timestamp)
            if promesa_dt < pago_dt <= deadline:
                promesa.cumplida = True
                break

    # ------------------------------------------------------------------
    # Pass 3 – build Agente nodes
    # ------------------------------------------------------------------
    # Collect all agente ids (even those with 0 calls from dataset)
    all_agente_ids: set = set()
    for raw_ix in dataset.interacciones:
        if raw_ix.agente_id:
            all_agente_ids.add(raw_ix.agente_id)

    agentes: List[AgenteNode] = []
    for agente_id in sorted(all_agente_ids):
        resultados = agente_calls.get(agente_id, [])
        total = len(resultados)
        n_promesa = sum(1 for r in resultados if r == "promesa_pago")
        n_pago_inmediato = sum(1 for r in resultados if r == "pago_inmediato")
        agentes.append(
            AgenteNode(
                id=agente_id,
                total_llamadas=total,
                tasa_promesa=round(n_promesa / total, 4) if total else 0.0,
                tasa_pago_inmediato=round(n_pago_inmediato / total, 4) if total else 0.0,
            )
        )

    # ------------------------------------------------------------------
    # Pass 4 – build Cliente nodes with derived aggregates
    # ------------------------------------------------------------------
    cliente_raw_map = {c.id: c for c in dataset.clientes}
    clientes: List[ClienteNode] = []

    for raw_cl in dataset.clientes:
        total_pagado = round(
            sum(p.monto for p in cliente_pagos.get(raw_cl.id, [])), 2
        )
        monto_pendiente = round(
            max(raw_cl.monto_deuda_inicial - total_pagado, 0.0), 2
        )
        promesas_cliente = cliente_promesas.get(raw_cl.id, [])
        n_promesas = len(promesas_cliente)
        n_cumplidas = sum(1 for p in promesas_cliente if p.cumplida)
        tasa_cumplimiento = round(n_cumplidas / n_promesas, 4) if n_promesas else 0.0

        clientes.append(
            ClienteNode(
                id=raw_cl.id,
                nombre=raw_cl.nombre,
                telefono=raw_cl.telefono,
                monto_deuda_inicial=raw_cl.monto_deuda_inicial,
                fecha_prestamo=raw_cl.fecha_prestamo,
                tipo_deuda=raw_cl.tipo_deuda,
                total_pagado=total_pagado,
                monto_pendiente=monto_pendiente,
                tasa_cumplimiento=tasa_cumplimiento,
            )
        )

    # ------------------------------------------------------------------
    # Pass 4.5 – build EstadoDeuda nodes (evolución temporal de la deuda)
    # ------------------------------------------------------------------
    # Eventos que cambian la deuda: pagos y renegociaciones, ordenados por ts.
    estados_deuda: List[EstadoDeudaNode] = []

    for raw_cl in dataset.clientes:
        cid = raw_cl.id
        saldo = raw_cl.monto_deuda_inicial

        # Estado inicial
        estados: List[EstadoDeudaNode] = [
            EstadoDeudaNode(
                id=f"{cid}_deuda_0",
                cliente_id=cid,
                fecha=raw_cl.fecha_prestamo + "T00:00:00+00:00",
                monto_pendiente=round(saldo, 2),
                tipo="inicial",
                evento_id="inicial",
            )
        ]

        # Eventos que mutan la deuda, ordenados cronológicamente
        eventos = sorted(
            (
                ix for ix in dataset.interacciones
                if ix.cliente_id == cid
                and ix.tipo in ("pago_recibido", *LLAMADA_TIPOS)
                and (
                    ix.tipo == "pago_recibido"
                    or ix.resultado == "renegociacion"
                )
            ),
            key=lambda x: x.timestamp,
        )

        for n, ev in enumerate(eventos, start=1):
            if ev.tipo == "pago_recibido":
                saldo = max(saldo - (ev.monto or 0.0), 0.0)
                tipo_estado = "pago"
            else:
                tipo_estado = "renegociacion"

            estados.append(
                EstadoDeudaNode(
                    id=f"{cid}_deuda_{n}",
                    cliente_id=cid,
                    fecha=ev.timestamp,
                    monto_pendiente=round(saldo, 2),
                    tipo=tipo_estado,
                    evento_id=ev.id,
                )
            )

        estados_deuda.extend(estados)

    # ------------------------------------------------------------------
    # Pass 5 – build relationships
    # ------------------------------------------------------------------
    relationships: List[RelationRecord] = []

    # Map node id sets for quick lookup
    interaccion_id_set = {ix.id for ix in interacciones}
    agente_id_set = {a.id for a in agentes}
    cliente_id_set = {c.id for c in clientes}

    for ix in interacciones:
        # TIENE_INTERACCION: Cliente -> Interaccion
        relationships.append(RelationRecord(
            from_id=ix.cliente_id,
            rel_type="TIENE_INTERACCION",
            to_id=ix.id,
        ))

        # CONDUJO: Agente -> Interaccion  (llamadas only)
        if ix.agente_id and ix.agente_id in agente_id_set:
            relationships.append(RelationRecord(
                from_id=ix.agente_id,
                rel_type="CONDUJO",
                to_id=ix.id,
            ))

    # GENERO_PROMESA: Interaccion -> PromesaPago
    for promesa in promesas:
        relationships.append(RelationRecord(
            from_id=promesa.interaccion_id,
            rel_type="GENERO_PROMESA",
            to_id=promesa.id,
        ))

    # GENERO_PAGO: Interaccion -> Pago
    for pago in pagos:
        relationships.append(RelationRecord(
            from_id=pago.interaccion_id,
            rel_type="GENERO_PAGO",
            to_id=pago.id,
        ))

    # GENERO_PLAN: Interaccion -> PlanPago
    # Build cuota lookup once for O(plans) instead of O(plans * promesas)
    cuotas_by_plan: Dict[str, List[PromesaPagoNode]] = defaultdict(list)
    for promesa in promesas:
        if promesa.plan_pago_id is not None:
            cuotas_by_plan[promesa.plan_pago_id].append(promesa)

    for plan in planes:
        relationships.append(RelationRecord(
            from_id=plan.interaccion_id,
            rel_type="GENERO_PLAN",
            to_id=plan.id,
        ))
        # GENERA_CUOTA: PlanPago -> PromesaPago (una por cuota)
        for cuota in cuotas_by_plan.get(plan.id, []):
            relationships.append(RelationRecord(
                from_id=plan.id,
                rel_type="GENERA_CUOTA",
                to_id=cuota.id,
            ))

    # CUMPLE_PROMESA: Pago -> PromesaPago  (for fulfilled promises)
    pago_by_ix: Dict[str, PagoNode] = {p.interaccion_id: p for p in pagos}
    for promesa in promesas:
        if promesa.cumplida:
            promesa_dt = ix_ts_map[promesa.interaccion_id]
            fecha_promesa_date = _parse_date(promesa.fecha_promesa)
            deadline = datetime.combine(
                fecha_promesa_date + timedelta(days=grace_days), datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            for pago in cliente_pagos.get(promesa.cliente_id, []):
                pago_dt = _parse_ts(pago.timestamp)
                if promesa_dt < pago_dt <= deadline:
                    relationships.append(RelationRecord(
                        from_id=pago.id,
                        rel_type="CUMPLE_PROMESA",
                        to_id=promesa.id,
                    ))
                    break

    # SIGUIENTE: chain interactions per client (chronological order).
    # C5: aristas N-1 por cliente ≈ 10M a 1M clientes. Por default se emiten
    # (comportamiento histórico); a gran escala esta relación es redundante
    # — ORDER BY timestamp + índice da el mismo resultado sin materializar la
    # cadena. Para desactivarla: export CREATE_SIGUIENTE=0
    if os.environ.get("CREATE_SIGUIENTE", "1") != "0":
        cliente_ix_map: Dict[str, List[InteraccionNode]] = defaultdict(list)
        for ix in interacciones:
            cliente_ix_map[ix.cliente_id].append(ix)

        for cliente_id, ix_list in cliente_ix_map.items():
            sorted_ixs = sorted(ix_list, key=lambda x: ix_ts_map[x.id])
            for i in range(len(sorted_ixs) - 1):
                relationships.append(RelationRecord(
                    from_id=sorted_ixs[i].id,
                    rel_type="SIGUIENTE",
                    to_id=sorted_ixs[i + 1].id,
                    properties={"orden": i + 1},
                ))

    # ESTADO_DEUDA_EN: Cliente -> EstadoDeuda
    # SIGUIENTE_ESTADO: EstadoDeuda -> EstadoDeuda (cadena temporal por cliente)
    estados_by_cliente: Dict[str, List[EstadoDeudaNode]] = defaultdict(list)
    for ed in estados_deuda:
        estados_by_cliente[ed.cliente_id].append(ed)

    for cid, estados in estados_by_cliente.items():
        for ed in estados:
            relationships.append(RelationRecord(
                from_id=cid,
                rel_type="ESTADO_DEUDA_EN",
                to_id=ed.id,
            ))
        sorted_ed = sorted(estados, key=lambda e: e.fecha)
        for i in range(len(sorted_ed) - 1):
            relationships.append(RelationRecord(
                from_id=sorted_ed[i].id,
                rel_type="SIGUIENTE_ESTADO",
                to_id=sorted_ed[i + 1].id,
            ))

    return agentes, clientes, interacciones, promesas, pagos, planes, estados_deuda, relationships
