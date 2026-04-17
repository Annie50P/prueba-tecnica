"""
MCP Service — consultas en lenguaje natural con function calling.

Arquitectura:
  query_mcp()  →  get_provider()  →  GeminiProvider | AnthropicProvider
                                            ↓
                                    _execute_tool()  →  graphiti_service
                                            ↓
                                    respuesta sintetizada

El proveedor activo se selecciona automáticamente según las API keys
disponibles en el entorno (ver api/services/llm_providers.py).
"""

import json
import logging
from typing import Any

from api.config import settings
from api.services import graphiti_service as gs
from api.services import analytics_service as ans
from api.services import graphiti_mcp_client as mcp_client
from api.services.llm_providers import get_provider

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Asistente de cobranza. Datos: 50 clientes, 502 interacciones, 10 agentes.
Responde en español, conciso, con números concretos. Usa tools antes de responder.

Guía rápida de tools:
- Rankings/totales globales → get_dashboard (rápida)
- Buscar cliente por nombre → get_clientes
- Detalle de un cliente → get_cliente_detalle o get_cliente_timeline
- Agentes → get_agentes o get_agente_efectividad
- Promesas vencidas → get_promesas_incumplidas
- Horarios → get_mejores_horarios
- Riesgo de UN cliente → predict_cliente(cliente_id)
- Ranking de riesgo → get_prediccion_clientes
- Anomalías → get_anomalias
- Búsqueda semántica en grafo → mcp__search_nodes o mcp__search_memory_facts

Predicción: categoria_riesgo alto=impago probable; probabilidad_pago ∈ [0,1]."""

# ─────────────────────────────────────────────────────────────────
# Tool definitions (formato Claude — los providers convierten según necesidad)
# ─────────────────────────────────────────────────────────────────

LOCAL_TOOLS: list[dict] = [
    {
        "name": "get_dashboard",
        "description": "KPIs globales: deuda total, recuperado, tasa recuperación, promesas cumplidas/incumplidas, top clientes por deuda, agentes destacados.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_cliente_detalle",
        "description": "Detalle de UN cliente: pagos, promesas, interacciones. Requiere cliente_id (ej: cliente_007).",
        "input_schema": {
            "type": "object",
            "properties": {"cliente_id": {"type": "string"}},
            "required": ["cliente_id"],
        },
    },
    {
        "name": "get_agentes",
        "description": "Lista de agentes con métricas: tasa de promesas, tasa de pago inmediato, total llamadas.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_promesas_incumplidas",
        "description": "Promesas de pago incumplidas/vencidas.",
        "input_schema": {
            "type": "object",
            "properties": {"fecha": {"type": "string", "description": "Fecha límite YYYY-MM-DD"}},
            "required": [],
        },
    },
    {
        "name": "get_mejores_horarios",
        "description": "Horarios con mayor tasa de éxito para llamadas.",
        "input_schema": {
            "type": "object",
            "properties": {"resultado": {"type": "string"}},
            "required": [],
        },
    },
    {
        "name": "predict_cliente",
        "description": "Predicción ML para UN cliente: score_riesgo (0-100), categoria_riesgo, probabilidad_pago, factores. Requiere cliente_id.",
        "input_schema": {
            "type": "object",
            "properties": {"cliente_id": {"type": "string"}},
            "required": ["cliente_id"],
        },
    },
    {
        "name": "get_clientes",
        "description": "Lista todos los clientes con métricas clave: deuda inicial, total pagado, deuda pendiente, tasa de cumplimiento. Útil para buscar por nombre o comparar clientes.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_cliente_timeline",
        "description": "Historial cronológico completo de UN cliente: interacciones, promesas, pagos y planes en orden temporal. Requiere cliente_id.",
        "input_schema": {
            "type": "object",
            "properties": {"cliente_id": {"type": "string"}},
            "required": ["cliente_id"],
        },
    },
    {
        "name": "get_agente_efectividad",
        "description": "Métricas detalladas de UN agente: distribución de resultados, sentimientos, mejor horario. Requiere agente_id.",
        "input_schema": {
            "type": "object",
            "properties": {"agente_id": {"type": "string"}},
            "required": ["agente_id"],
        },
    },
    {
        "name": "get_prediccion_clientes",
        "description": "Ranking completo de todos los clientes ordenado por riesgo de impago (score_riesgo 0-100, categoria_riesgo, probabilidad_pago).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_anomalias",
        "description": "Detección de anomalías en el comportamiento de pago usando IsolationForest + LOF. Identifica clientes atípicos.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_estrategias",
        "description": "Segmentación de clientes por comportamiento (KMeans) con estrategias de cobranza recomendadas por segmento.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

# ─────────────────────────────────────────────────────────────────
# Tool executor (independiente del proveedor LLM)
# ─────────────────────────────────────────────────────────────────

async def _execute_tool(tool_name: str, tool_input: dict) -> Any:
    """Despacha la tool solicitada por el LLM y retorna el resultado crudo.

    - Tools con prefijo `mcp__` se enrutan al servidor MCP oficial de Graphiti.
    - El resto son tools locales (analytics / predicción ML / KPIs).
    """
    logger.info("[mcp] tool=%s args=%s", tool_name, tool_input)

    # Ruta 1 — tool del MCP server oficial (Graphiti).
    if tool_name.startswith("mcp__"):
        try:
            result = await mcp_client.call_mcp_tool(tool_name, tool_input or {})
        except Exception as e:
            logger.exception("[mcp] error MCP tool %s: %s", tool_name, e)
            result = {"error": "mcp_tool_error", "tool_name": tool_name, "message": str(e)}
        logger.info("[mcp] tool=%s → %d chars", tool_name, len(str(result)))
        return result

    # Ruta 2 — tools locales.
    try:
        if tool_name == "get_dashboard":
            raw = await gs.get_dashboard()
            # Excluir actividad_por_dia (array grande) — no relevante para el LLM
            result = {k: v for k, v in raw.items() if k != "actividad_por_dia"} if isinstance(raw, dict) else raw
        elif tool_name == "get_clientes":
            clientes = await gs.get_all_clientes()
            result = [
                {
                    "cliente_id": c.get("cliente_id"),
                    "nombre": c.get("nombre"),
                    "deuda_inicial": c.get("monto_deuda_inicial"),
                    "total_pagado": c.get("total_pagado"),
                    "deuda_pendiente": c.get("monto_pendiente"),
                    "tasa_cumplimiento": c.get("tasa_cumplimiento"),
                }
                for c in clientes
            ]
        elif tool_name == "get_cliente_detalle":
            result = await gs.get_cliente_by_id(tool_input.get("cliente_id", ""))
            if result is None:
                result = {"error": "not_found", "cliente_id": tool_input.get("cliente_id")}
        elif tool_name == "get_cliente_timeline":
            result = await gs.get_cliente_timeline(tool_input.get("cliente_id", ""))
            if result is None:
                result = {"error": "not_found", "cliente_id": tool_input.get("cliente_id")}
        elif tool_name == "get_agentes":
            result = await gs.get_all_agentes()
        elif tool_name == "get_agente_efectividad":
            result = await gs.get_agente_efectividad(tool_input.get("agente_id", ""))
            if result is None:
                result = {"error": "not_found", "agente_id": tool_input.get("agente_id")}
        elif tool_name == "get_promesas_incumplidas":
            result = await gs.get_promesas_incumplidas(tool_input.get("fecha"))
        elif tool_name == "get_mejores_horarios":
            result = await gs.get_mejores_horarios(tool_input.get("resultado"))
        elif tool_name == "get_prediccion_clientes":
            result = await ans.get_prediccion_clientes()
        elif tool_name == "predict_cliente":
            cliente_id = tool_input.get("cliente_id", "")
            predicciones = await ans.get_prediccion_clientes()
            result = next(
                (p for p in predicciones if p.get("cliente_id") == cliente_id),
                {"error": "not_found", "cliente_id": cliente_id,
                 "message": "Cliente no encontrado o sin datos suficientes para predecir."},
            )
        elif tool_name == "get_anomalias":
            result = await ans.get_anomalias()
        elif tool_name == "get_estrategias":
            result = await ans.get_estrategias()
        else:
            result = {"error": "unknown_tool", "tool_name": tool_name}
    except Exception as e:
        logger.exception("[mcp] error executing tool %s: %s", tool_name, e)
        result = {"error": "tool_execution_error", "tool_name": tool_name, "message": str(e)}

    result = _trim_tool_result(result)
    logger.info("[mcp] tool=%s → %d chars", tool_name, len(str(result)))
    return result


_TOOL_MAX_CHARS = 1500  # Groq free tier: ~6000 tokens/min; system+tools+result deben caber


def _trim_tool_result(result: Any) -> Any:
    """
    Limita el tamaño del resultado antes de pasarlo al LLM.
    Las listas se recortan a 10 items; el JSON total a 3000 chars.
    """
    if isinstance(result, list) and len(result) > 10:
        trimmed = result[:10]
        trimmed.append({"_note": f"truncado — mostrando 10 de {len(result)} items"})
        result = trimmed
    serialized = json.dumps(result, ensure_ascii=False, default=str)
    if len(serialized) > _TOOL_MAX_CHARS:
        return {"_note": f"resultado truncado a {_TOOL_MAX_CHARS} chars",
                "data": serialized[:_TOOL_MAX_CHARS]}
    return result


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

_TOOL_CATALOG_CACHE: list[dict] = []

async def _build_tool_catalog() -> list[dict]:
    """
    Catálogo completo expuesto al LLM: tools locales + tools del MCP server.
    Las tools MCP se descubren una sola vez y se cachean en memoria (el set
    de tools del servidor no cambia en runtime).
    """
    global _TOOL_CATALOG_CACHE
    if _TOOL_CATALOG_CACHE:
        return _TOOL_CATALOG_CACHE

    mcp_tools = await mcp_client.list_mcp_tools()
    if mcp_tools:
        logger.info("[mcp] %d tools descubiertas del MCP server oficial", len(mcp_tools))
    _TOOL_CATALOG_CACHE = LOCAL_TOOLS + mcp_tools
    return _TOOL_CATALOG_CACHE


async def query_mcp(query: str, params: dict | None = None) -> dict[str, Any]:
    """
    Procesa una consulta en lenguaje natural usando el proveedor LLM activo.

    Selección de proveedor (variable LLM_PROVIDER en .env, default "auto"):
      auto      → OpenAI > Gemini > Anthropic (primera key disponible)
      openai    → Fuerza OpenAI
      gemini    → Fuerza Gemini
      anthropic → Fuerza Anthropic

    El catálogo de tools se construye dinámicamente: tools locales (analítica +
    predicción ML) + tools descubiertas en el MCP server oficial de Graphiti
    (add_episode, search_nodes, search_facts, get_episodes, etc.).
    """
    provider = get_provider(settings)

    if provider is None:
        return {
            "status": "error",
            "error": "mcp_not_configured",
            "message": (
                "No hay proveedor LLM configurado. "
                "Define OPENAI_API_KEY, GEMINI_API_KEY (gratis en aistudio.google.com) "
                "o ANTHROPIC_API_KEY en el archivo .env."
            ),
            "respuesta": "",
            "datos": [],
        }

    tools = await _build_tool_catalog()

    return await provider.run(
        query=query,
        system_prompt=SYSTEM_PROMPT,
        tools=tools,
        execute_tool=_execute_tool,
        max_iterations=5,
    )
