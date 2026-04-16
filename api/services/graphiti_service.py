"""
GraphitiService: All database query logic for the Call Pattern Analyzer API.
Reads from a local SQLite database at ingesta/local_graph.db.

Schema:
    nodes (id TEXT PRIMARY KEY, label TEXT, properties TEXT)   -- properties is JSON string
    relationships (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   from_id TEXT, rel_type TEXT, to_id TEXT, properties TEXT)
"""

import sqlite3
import json
import os
from typing import Any, Optional
from datetime import datetime, date


# Resolve DB path relative to this file: ../../../ingesta/local_graph.db
# File is at api/services/graphiti_service.py → go up 3 levels to project root
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ingesta",
    "local_graph.db",
)


def _get_connection() -> sqlite3.Connection:
    """Open and return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_props(raw: Optional[str]) -> dict:
    """Safely parse a JSON properties string into a dict."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

def get_all_clientes() -> list[dict]:
    """
    Return all Cliente nodes enriched with derived metrics:
    - total_pagado: sum of amounts in Pago nodes linked to this client
    - monto_pendiente: monto_deuda_inicial - total_pagado
    - tasa_cumplimiento: promesas_cumplidas / total_promesas
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # Fetch all Cliente nodes
        cursor.execute("SELECT id, label, properties FROM nodes WHERE label = 'Cliente'")
        clientes_rows = cursor.fetchall()

        result = []
        for row in clientes_rows:
            cliente_id = row["id"]
            props = _parse_props(row["properties"])

            # --- total_pagado ---
            # Path: Cliente -TIENE_INTERACCION-> Interaccion -GENERO_PAGO-> Pago
            cursor.execute(
                """
                SELECT n.properties
                FROM relationships r1
                JOIN relationships r2 ON r1.to_id = r2.from_id
                JOIN nodes n ON r2.to_id = n.id
                WHERE r1.from_id = ?
                  AND r1.rel_type = 'TIENE_INTERACCION'
                  AND r2.rel_type = 'GENERO_PAGO'
                  AND n.label = 'Pago'
                """,
                (cliente_id,),
            )
            pago_rows = cursor.fetchall()
            total_pagado = sum(
                _parse_props(p["properties"]).get("monto", 0) or 0 for p in pago_rows
            )

            # --- promesas ---
            cursor.execute(
                """
                SELECT n.properties
                FROM relationships r1
                JOIN relationships r2 ON r1.to_id = r2.from_id
                JOIN nodes n ON r2.to_id = n.id
                WHERE r1.from_id = ?
                  AND r1.rel_type = 'TIENE_INTERACCION'
                  AND r2.rel_type = 'GENERO_PROMESA'
                  AND n.label = 'PromesaPago'
                """,
                (cliente_id,),
            )
            promesa_rows = cursor.fetchall()
            total_promesas = len(promesa_rows)
            promesas_cumplidas = sum(
                1
                for p in promesa_rows
                if _parse_props(p["properties"]).get("cumplida") is True
            )
            tasa_cumplimiento = (
                round(promesas_cumplidas / total_promesas, 4) if total_promesas > 0 else 0.0
            )

            monto_deuda = props.get("monto_deuda_inicial", 0) or 0
            monto_pendiente = max(0, monto_deuda - total_pagado)

            result.append(
                {
                    "id": cliente_id,
                    "label": row["label"],
                    **props,
                    "total_pagado": round(total_pagado, 2),
                    "monto_pendiente": round(monto_pendiente, 2),
                    "tasa_cumplimiento": tasa_cumplimiento,
                }
            )

        return result
    finally:
        conn.close()


def get_cliente_by_id(cliente_id: str) -> Optional[dict]:
    """Return full detail for a single client, including linked entities."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, label, properties FROM nodes WHERE id = ? AND label = 'Cliente'",
            (cliente_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        props = _parse_props(row["properties"])

        # Interactions
        cursor.execute(
            """
            SELECT n.id, n.label, n.properties
            FROM relationships r JOIN nodes n ON r.to_id = n.id
            WHERE r.from_id = ? AND r.rel_type = 'TIENE_INTERACCION' AND n.label = 'Interaccion'
            """,
            (cliente_id,),
        )
        interacciones = [
            {"id": r["id"], **_parse_props(r["properties"])} for r in cursor.fetchall()
        ]

        # Promises
        cursor.execute(
            """
            SELECT n.id, n.label, n.properties
            FROM relationships r1
            JOIN relationships r2 ON r1.to_id = r2.from_id
            JOIN nodes n ON r2.to_id = n.id
            WHERE r1.from_id = ?
              AND r1.rel_type = 'TIENE_INTERACCION'
              AND r2.rel_type = 'GENERO_PROMESA'
              AND n.label = 'PromesaPago'
            """,
            (cliente_id,),
        )
        promesas = [
            {"id": r["id"], **_parse_props(r["properties"])} for r in cursor.fetchall()
        ]

        # Payments
        cursor.execute(
            """
            SELECT n.id, n.label, n.properties
            FROM relationships r1
            JOIN relationships r2 ON r1.to_id = r2.from_id
            JOIN nodes n ON r2.to_id = n.id
            WHERE r1.from_id = ?
              AND r1.rel_type = 'TIENE_INTERACCION'
              AND r2.rel_type = 'GENERO_PAGO'
              AND n.label = 'Pago'
            """,
            (cliente_id,),
        )
        pagos = [
            {"id": r["id"], **_parse_props(r["properties"])} for r in cursor.fetchall()
        ]

        total_pagado = sum(p.get("monto", 0) or 0 for p in pagos)
        monto_deuda = props.get("monto_deuda_inicial", 0) or 0

        return {
            "id": cliente_id,
            "label": row["label"],
            **props,
            "interacciones": interacciones,
            "promesas": promesas,
            "pagos": pagos,
            "total_pagado": round(total_pagado, 2),
            "monto_pendiente": round(max(0, monto_deuda - total_pagado), 2),
        }
    finally:
        conn.close()


def get_cliente_timeline(cliente_id: str) -> Optional[list[dict]]:
    """
    Return chronological interaction history for a client.
    Returns None if the client does not exist.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # Verify client exists
        cursor.execute(
            "SELECT id FROM nodes WHERE id = ? AND label = 'Cliente'", (cliente_id,)
        )
        if not cursor.fetchone():
            return None

        # Fetch interactions
        cursor.execute(
            """
            SELECT n.id, n.properties
            FROM relationships r JOIN nodes n ON r.to_id = n.id
            WHERE r.from_id = ? AND r.rel_type = 'TIENE_INTERACCION' AND n.label = 'Interaccion'
            """,
            (cliente_id,),
        )
        interacciones_rows = cursor.fetchall()

        timeline = []
        for row in interacciones_rows:
            interaccion_id = row["id"]
            props = _parse_props(row["properties"])

            # Promises from this interaction
            cursor.execute(
                """
                SELECT n.id, n.properties
                FROM relationships r JOIN nodes n ON r.to_id = n.id
                WHERE r.from_id = ? AND r.rel_type = 'GENERO_PROMESA' AND n.label = 'PromesaPago'
                """,
                (interaccion_id,),
            )
            promesas = [
                {"id": r["id"], **_parse_props(r["properties"])} for r in cursor.fetchall()
            ]

            # Payments from this interaction
            cursor.execute(
                """
                SELECT n.id, n.properties
                FROM relationships r JOIN nodes n ON r.to_id = n.id
                WHERE r.from_id = ? AND r.rel_type = 'GENERO_PAGO' AND n.label = 'Pago'
                """,
                (interaccion_id,),
            )
            pagos = [
                {"id": r["id"], **_parse_props(r["properties"])} for r in cursor.fetchall()
            ]

            # Plans from this interaction
            cursor.execute(
                """
                SELECT n.id, n.properties
                FROM relationships r JOIN nodes n ON r.to_id = n.id
                WHERE r.from_id = ? AND r.rel_type = 'GENERO_PLAN' AND n.label = 'PlanPago'
                """,
                (interaccion_id,),
            )
            planes = [
                {"id": r["id"], **_parse_props(r["properties"])} for r in cursor.fetchall()
            ]

            timeline.append(
                {
                    "interaccion_id": interaccion_id,
                    **props,
                    "promesas": promesas,
                    "pagos": pagos,
                    "planes": planes,
                }
            )

        # Sort by timestamp ascending (None timestamps go last)
        def _sort_key(item: dict):
            ts = item.get("timestamp") or item.get("fecha") or ""
            return ts

        timeline.sort(key=_sort_key)
        return timeline
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Agentes
# ---------------------------------------------------------------------------

def get_all_agentes() -> list[dict]:
    """Return all Agente nodes with aggregate metrics."""
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, label, properties FROM nodes WHERE label = 'Agente'")
        agente_rows = cursor.fetchall()

        result = []
        for row in agente_rows:
            agente_id = row["id"]
            props = _parse_props(row["properties"])

            # Interactions conducted by this agent
            cursor.execute(
                """
                SELECT n.id, n.properties
                FROM relationships r JOIN nodes n ON r.to_id = n.id
                WHERE r.from_id = ? AND r.rel_type = 'CONDUJO' AND n.label = 'Interaccion'
                """,
                (agente_id,),
            )
            interaccion_rows = cursor.fetchall()
            total_llamadas = len(interaccion_rows)

            # Aggregate promise and payment rates
            promesas = 0
            pagos_inmediatos = 0
            for ir in interaccion_rows:
                ip = _parse_props(ir["properties"])
                resultado = (ip.get("resultado") or "").lower()
                if "promesa" in resultado:
                    promesas += 1
                if "pago_inmediato" in resultado or "pago inmediato" in resultado:
                    pagos_inmediatos += 1

            tasa_promesa = round(promesas / total_llamadas, 4) if total_llamadas > 0 else 0.0
            tasa_pago_inmediato = (
                round(pagos_inmediatos / total_llamadas, 4) if total_llamadas > 0 else 0.0
            )

            result.append(
                {
                    "id": agente_id,
                    "label": row["label"],
                    **props,
                    "total_llamadas": total_llamadas,
                    "tasa_promesa": tasa_promesa,
                    "tasa_pago_inmediato": tasa_pago_inmediato,
                }
            )

        return result
    finally:
        conn.close()


def get_agente_efectividad(agente_id: str) -> Optional[dict]:
    """
    Return detailed performance metrics for a single agent:
    total_llamadas, tasa_promesa, tasa_pago_inmediato,
    distribucion_resultados, distribucion_sentimientos, mejor_horario.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, label, properties FROM nodes WHERE id = ? AND label = 'Agente'",
            (agente_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        props = _parse_props(row["properties"])

        # Interactions conducted by this agent
        cursor.execute(
            """
            SELECT n.id, n.properties
            FROM relationships r JOIN nodes n ON r.to_id = n.id
            WHERE r.from_id = ? AND r.rel_type = 'CONDUJO' AND n.label = 'Interaccion'
            """,
            (agente_id,),
        )
        interaccion_rows = cursor.fetchall()
        total_llamadas = len(interaccion_rows)

        distribucion_resultados: dict[str, int] = {}
        distribucion_sentimientos: dict[str, int] = {}
        hour_results: dict[int, dict[str, int]] = {}  # hour -> {resultado: count}

        promesas = 0
        pagos_inmediatos = 0

        for ir in interaccion_rows:
            ip = _parse_props(ir["properties"])

            resultado = ip.get("resultado") or "desconocido"
            sentimiento = ip.get("sentimiento_cliente") or ip.get("sentimiento") or "desconocido"
            timestamp = ip.get("timestamp") or ip.get("fecha") or ""

            distribucion_resultados[resultado] = distribucion_resultados.get(resultado, 0) + 1
            distribucion_sentimientos[sentimiento] = (
                distribucion_sentimientos.get(sentimiento, 0) + 1
            )

            resultado_lower = resultado.lower()
            if "promesa" in resultado_lower:
                promesas += 1
            if "pago_inmediato" in resultado_lower or "pago inmediato" in resultado_lower:
                pagos_inmediatos += 1

            # Extract hour from timestamp
            hour = None
            if timestamp:
                try:
                    # Try ISO format first
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    hour = dt.hour
                except (ValueError, AttributeError):
                    try:
                        # Try parsing just time portion HH:MM
                        parts = timestamp.split("T")
                        if len(parts) == 2:
                            hour = int(parts[1][:2])
                    except Exception:
                        pass

            if hour is not None:
                if hour not in hour_results:
                    hour_results[hour] = {}
                hour_results[hour][resultado] = hour_results[hour].get(resultado, 0) + 1

        # Determine best hour (highest promise/payment rate)
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

        tasa_promesa = round(promesas / total_llamadas, 4) if total_llamadas > 0 else 0.0
        tasa_pago_inmediato = (
            round(pagos_inmediatos / total_llamadas, 4) if total_llamadas > 0 else 0.0
        )

        return {
            "id": agente_id,
            **props,
            "total_llamadas": total_llamadas,
            "tasa_promesa": tasa_promesa,
            "tasa_pago_inmediato": tasa_pago_inmediato,
            "distribucion_resultados": distribucion_resultados,
            "distribucion_sentimientos": distribucion_sentimientos,
            "mejor_horario": mejor_horario,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def get_promesas_incumplidas(fecha: Optional[str] = None) -> list[dict]:
    """
    Return PromesaPago nodes where cumplida is False.
    Optionally filter by fecha_promesa <= fecha parameter.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, label, properties FROM nodes WHERE label = 'PromesaPago'"
        )
        rows = cursor.fetchall()

        result = []
        for row in rows:
            props = _parse_props(row["properties"])
            cumplida = props.get("cumplida")

            # Only unfulfilled promises
            if cumplida is True:
                continue

            if fecha:
                fecha_promesa = props.get("fecha_promesa") or props.get("fecha") or ""
                if fecha_promesa and fecha_promesa > fecha:
                    continue

            # Find client associated with this promise
            # Path: Cliente -TIENE_INTERACCION-> Interaccion -GENERO_PROMESA-> PromesaPago
            cursor.execute(
                """
                SELECT r1.from_id AS cliente_id
                FROM relationships r2
                JOIN relationships r1 ON r2.from_id = r1.to_id
                WHERE r2.to_id = ?
                  AND r2.rel_type = 'GENERO_PROMESA'
                  AND r1.rel_type = 'TIENE_INTERACCION'
                LIMIT 1
                """,
                (row["id"],),
            )
            rel = cursor.fetchone()
            cliente_id = rel["cliente_id"] if rel else None

            result.append(
                {
                    "id": row["id"],
                    "cliente_id": cliente_id,
                    **props,
                }
            )

        return result
    finally:
        conn.close()


def get_mejores_horarios(resultado: Optional[str] = None) -> dict:
    """
    Analyze best call times by grouping interactions by hour.
    Optionally filter interactions by resultado value.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, properties FROM nodes WHERE label = 'Interaccion'"
        )
        rows = cursor.fetchall()

        hour_stats: dict[int, dict] = {}

        for row in rows:
            props = _parse_props(row["properties"])
            res = props.get("resultado") or ""
            timestamp = props.get("timestamp") or props.get("fecha") or ""

            # Apply result filter
            if resultado and resultado.lower() not in res.lower():
                continue

            hour = None
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    hour = dt.hour
                except (ValueError, AttributeError):
                    try:
                        parts = str(timestamp).split("T")
                        if len(parts) == 2:
                            hour = int(parts[1][:2])
                    except Exception:
                        pass

            if hour is None:
                continue

            if hour not in hour_stats:
                hour_stats[hour] = {"total": 0, "resultados": {}}

            hour_stats[hour]["total"] += 1
            hour_stats[hour]["resultados"][res] = (
                hour_stats[hour]["resultados"].get(res, 0) + 1
            )

        # Build sorted list
        horarios = []
        for hour, stats in sorted(hour_stats.items()):
            horarios.append(
                {
                    "hora": f"{hour:02d}:00",
                    "total_llamadas": stats["total"],
                    "distribucion_resultados": stats["resultados"],
                }
            )

        # Find best hour
        mejor_hora = None
        if horarios:
            mejor_hora = max(horarios, key=lambda h: h["total_llamadas"])["hora"]

        return {
            "filtro_resultado": resultado,
            "mejor_hora": mejor_hora,
            "detalle_por_hora": horarios,
        }
    finally:
        conn.close()


def get_dashboard() -> dict:
    """
    Return high-level KPIs for the dashboard:
    total_deuda_inicial, total_recuperado, tasa_recuperacion,
    promesas_cumplidas, promesas_incumplidas,
    distribucion_tipos_deuda, actividad_por_dia.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # total_deuda_inicial
        cursor.execute(
            "SELECT properties FROM nodes WHERE label = 'Cliente'"
        )
        cliente_rows = cursor.fetchall()
        total_deuda_inicial = sum(
            _parse_props(r["properties"]).get("monto_deuda_inicial", 0) or 0
            for r in cliente_rows
        )

        # distribucion_tipos_deuda
        distribucion_tipos_deuda: dict[str, int] = {}
        for r in cliente_rows:
            props = _parse_props(r["properties"])
            tipo = props.get("tipo_deuda") or "desconocido"
            distribucion_tipos_deuda[tipo] = distribucion_tipos_deuda.get(tipo, 0) + 1

        # total_recuperado (sum of all Pago nodes)
        cursor.execute("SELECT properties FROM nodes WHERE label = 'Pago'")
        pago_rows = cursor.fetchall()
        total_recuperado = sum(
            _parse_props(r["properties"]).get("monto", 0) or 0 for r in pago_rows
        )

        tasa_recuperacion = (
            round(total_recuperado / total_deuda_inicial, 4)
            if total_deuda_inicial > 0
            else 0.0
        )

        # promesas_cumplidas / promesas_incumplidas
        cursor.execute("SELECT properties FROM nodes WHERE label = 'PromesaPago'")
        promesa_rows = cursor.fetchall()
        promesas_cumplidas = sum(
            1
            for r in promesa_rows
            if _parse_props(r["properties"]).get("cumplida") is True
        )
        promesas_incumplidas = len(promesa_rows) - promesas_cumplidas

        # actividad_por_dia: group interactions and payments by date
        cursor.execute(
            "SELECT id, properties FROM nodes WHERE label = 'Interaccion'"
        )
        interaccion_rows = cursor.fetchall()

        actividad_por_dia: dict[str, dict] = {}
        for r in interaccion_rows:
            props = _parse_props(r["properties"])
            ts = props.get("timestamp") or props.get("fecha") or ""
            day = ts[:10] if ts else "sin_fecha"
            if day not in actividad_por_dia:
                actividad_por_dia[day] = {"llamadas": 0, "pagos": 0}
            actividad_por_dia[day]["llamadas"] += 1

        for r in pago_rows:
            props = _parse_props(r["properties"])
            ts = props.get("fecha") or props.get("timestamp") or ""
            day = ts[:10] if ts else "sin_fecha"
            if day not in actividad_por_dia:
                actividad_por_dia[day] = {"llamadas": 0, "pagos": 0}
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
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Grafo
# ---------------------------------------------------------------------------

def get_grafo_nodos(tipos: Optional[list[str]] = None, limite: int = 200) -> dict:
    """
    Return nodes for D3.js visualization.
    Optionally filter by a list of label types.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        if tipos:
            placeholders = ",".join("?" * len(tipos))
            cursor.execute(
                f"SELECT id, label, properties FROM nodes WHERE label IN ({placeholders}) LIMIT ?",
                (*tipos, limite),
            )
        else:
            cursor.execute(
                "SELECT id, label, properties FROM nodes LIMIT ?", (limite,)
            )

        rows = cursor.fetchall()
        nodos = [
            {
                "id": row["id"],
                "tipo": row["label"],
                "label": _parse_props(row["properties"]).get("nombre")
                or _parse_props(row["properties"]).get("id_cliente")
                or row["id"],
                "propiedades": _parse_props(row["properties"]),
            }
            for row in rows
        ]

        return {"nodos": nodos}
    finally:
        conn.close()


def get_grafo_relaciones(
    cliente_id: Optional[str] = None,
    tipos_relacion: Optional[list[str]] = None,
    profundidad: int = 2,
) -> dict:
    """
    Return relationships for D3.js visualization.
    Optionally filter by cliente_id (subgraph up to `profundidad` hops),
    or by a list of relationship types.
    """
    conn = _get_connection()
    try:
        cursor = conn.cursor()

        conditions = []
        params: list[Any] = []

        if tipos_relacion:
            placeholders_rel = ",".join("?" * len(tipos_relacion))
            conditions.append(f"rel_type IN ({placeholders_rel})")
            params.extend(tipos_relacion)

        if cliente_id:
            # Build subgraph up to N hops from the client node
            connected_ids: set[str] = {cliente_id}
            frontier: set[str] = {cliente_id}

            for _ in range(profundidad):
                if not frontier:
                    break
                next_frontier: set[str] = set()
                for nid in frontier:
                    cursor.execute(
                        """
                        SELECT to_id AS node_id FROM relationships WHERE from_id = ?
                        UNION
                        SELECT from_id AS node_id FROM relationships WHERE to_id = ?
                        """,
                        (nid, nid),
                    )
                    for r in cursor.fetchall():
                        if r["node_id"] not in connected_ids:
                            next_frontier.add(r["node_id"])
                connected_ids.update(next_frontier)
                frontier = next_frontier

            all_ids = list(connected_ids)
            placeholders = ",".join("?" * len(all_ids))
            conditions.append(f"(from_id IN ({placeholders}) OR to_id IN ({placeholders}))")
            params.extend(all_ids)
            params.extend(all_ids)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(
            f"SELECT from_id, rel_type, to_id, properties FROM relationships {where_clause}",
            params,
        )

        rows = cursor.fetchall()
        enlaces = [
            {
                "source": row["from_id"],
                "target": row["to_id"],
                "tipo": row["rel_type"],
            }
            for row in rows
        ]

        return {"enlaces": enlaces}
    finally:
        conn.close()
