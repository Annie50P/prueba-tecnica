"""
graphiti_search_service.py — Búsqueda semántica sobre el knowledge graph de Graphiti.

Expone la capacidad diferencial de Graphiti: `graphiti.search()` encuentra hechos
extraídos por LLM de los episodios, con soporte temporal (valid_at / invalid_at).

A diferencia del grafo de dominio estructurado (Cliente, Interaccion, etc.),
el grafo semántico de Graphiti trabaja con hechos en lenguaje natural:
  "El agente agente_01 gestionó una promesa de pago de $500 del cliente Ana García"

Esto permite consultas como:
  - "clientes con promesas incumplidas de más de $1000"
  - "agentes con mayor tasa de rechazo"
  - "interacciones con sentimiento negativo en enero"
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from api.config import settings

logger = logging.getLogger(__name__)

_GROUP_ID = settings.graphiti_group_id or "prueba-tecnica"


def _get_graphiti():
    """Instancia Graphiti usando la misma conexión Neo4j que el resto del sistema."""
    from graphiti_core import Graphiti
    return Graphiti(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )


def _serialize_result(r: Any) -> dict:
    """
    Serializa un resultado de graphiti.search() independientemente de la versión
    de graphiti-core (EntityEdge, SearchResult o dict).
    """
    if isinstance(r, dict):
        return r

    fact = getattr(r, "fact", None) or getattr(r, "content", None) or str(r)
    name = getattr(r, "name", "")
    uuid = getattr(r, "uuid", "") or getattr(r, "id", "")

    valid_at = getattr(r, "valid_at", None)
    invalid_at = getattr(r, "invalid_at", None)

    source_uuid = (
        getattr(r, "source_node_uuid", None)
        or getattr(r, "source_uuid", None)
    )
    target_uuid = (
        getattr(r, "target_node_uuid", None)
        or getattr(r, "target_uuid", None)
    )

    return {
        "hecho": fact,
        "nombre": name,
        "uuid": str(uuid) if uuid else None,
        "entidad_origen_uuid": str(source_uuid) if source_uuid else None,
        "entidad_destino_uuid": str(target_uuid) if target_uuid else None,
        "valido_desde": valid_at.isoformat() if isinstance(valid_at, datetime) else str(valid_at) if valid_at else None,
        "valido_hasta": invalid_at.isoformat() if isinstance(invalid_at, datetime) else str(invalid_at) if invalid_at else None,
    }


async def busqueda_semantica(
    query: str,
    num_results: int = 10,
    fecha_ref: Optional[str] = None,
) -> dict:
    """
    Búsqueda semántica sobre los hechos extraídos por Graphiti de los episodios.

    Args:
        query:       consulta en lenguaje natural
        num_results: máximo de resultados a devolver
        fecha_ref:   fecha de referencia temporal ISO (YYYY-MM-DD) — filtra hechos
                     válidos en esa fecha según valid_at/invalid_at de Graphiti

    Returns:
        dict con `query`, `resultados` (lista de hechos), `total`, `nota`
    """
    try:
        g = _get_graphiti()
    except ImportError:
        return {
            "query": query,
            "resultados": [],
            "total": 0,
            "nota": "graphiti-core no instalado. Instalar con: pip install graphiti-core",
        }

    try:
        # graphiti.search() devuelve hechos semánticos extraídos de los episodios.
        # Acepta group_ids para aislar el conocimiento del proyecto.
        raw_results = await g.search(
            query=query,
            group_ids=[_GROUP_ID],
            num_results=num_results,
        )

        resultados = [_serialize_result(r) for r in (raw_results or [])]

        # Filtro temporal post-búsqueda: si se pasa fecha_ref, excluimos hechos
        # cuyo invalid_at sea anterior a la fecha (hechos ya invalidados en esa fecha).
        if fecha_ref and resultados:
            try:
                ref_dt = datetime.fromisoformat(fecha_ref).replace(tzinfo=timezone.utc)
                resultados = [
                    r for r in resultados
                    if (
                        r.get("valido_hasta") is None
                        or datetime.fromisoformat(r["valido_hasta"].replace("Z", "+00:00")) >= ref_dt
                    )
                ]
            except (ValueError, TypeError):
                pass

        return {
            "query": query,
            "resultados": resultados,
            "total": len(resultados),
            "nota": (
                "Resultados del knowledge graph semántico de Graphiti. "
                "Requiere LLM configurado (ANTHROPIC_API_KEY / OPENAI_API_KEY) "
                "durante la ingesta para extraer hechos."
            ),
        }

    except Exception as exc:
        logger.warning("[graphiti-search] search('%s') falló: %s", query, exc)
        return {
            "query": query,
            "resultados": [],
            "total": 0,
            "error": str(exc),
            "nota": (
                "El knowledge graph semántico no está disponible. "
                "Verifica que Neo4j esté activo y que se hayan ingestado episodios con LLM."
            ),
        }
    finally:
        try:
            await g.close()
        except Exception:
            pass
