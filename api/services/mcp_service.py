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
from api.services.llm_providers import get_provider

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un asistente de análisis de datos de una empresa de gestión de cobros.
Tienes acceso a un grafo de conocimiento con datos de 50 clientes, 502 interacciones,
10 agentes y 90 días de actividad.
Responde en español de forma concisa y con datos concretos.
Cuando sea relevante, incluye números específicos y porcentajes.
Usa las herramientas disponibles para consultar la base de datos antes de responder."""

# ─────────────────────────────────────────────────────────────────
# Tool definitions (formato Claude — los providers convierten según necesidad)
# ─────────────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "name": "get_dashboard",
        "description": "Retorna KPIs globales: total de deuda, dinero recuperado, tasa de recuperación, promesas cumplidas/incumplidas y actividad por día.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_clientes",
        "description": "Retorna la lista de todos los clientes con sus métricas derivadas (monto deuda, total pagado, tasa de cumplimiento).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_cliente_detalle",
        "description": "Retorna el detalle completo de un cliente: interacciones, promesas, pagos y planes de pago.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {
                    "type": "string",
                    "description": "ID del cliente, por ejemplo: cliente_001",
                }
            },
            "required": ["cliente_id"],
        },
    },
    {
        "name": "get_cliente_timeline",
        "description": "Retorna el historial cronológico de interacciones de un cliente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente_id": {
                    "type": "string",
                    "description": "ID del cliente",
                }
            },
            "required": ["cliente_id"],
        },
    },
    {
        "name": "get_agentes",
        "description": "Retorna la lista de todos los agentes con métricas de desempeño (tasa de promesas, tasa de pago inmediato, total llamadas).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_agente_efectividad",
        "description": "Retorna métricas detalladas de desempeño de un agente: distribución de resultados, sentimientos y mejor horario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agente_id": {
                    "type": "string",
                    "description": "ID del agente, por ejemplo: agente_01",
                }
            },
            "required": ["agente_id"],
        },
    },
    {
        "name": "get_promesas_incumplidas",
        "description": "Retorna las promesas de pago incumplidas. Opcionalmente filtra por fecha límite.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": {
                    "type": "string",
                    "description": "Fecha límite en formato YYYY-MM-DD. Solo retorna promesas vencidas hasta esa fecha.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_mejores_horarios",
        "description": "Retorna los horarios con mayor tasa de éxito para llamadas. Opcionalmente filtra por tipo de resultado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resultado": {
                    "type": "string",
                    "description": "Filtro de resultado, por ejemplo: 'promesa_pago'",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_prediccion_clientes",
        "description": "Análisis predictivo: retorna un score de riesgo (0-100) para cada cliente, con categoría (alto/medio/bajo), probabilidad de pago y factores explicativos.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_anomalias",
        "description": "Detección de anomalías: identifica pagos atípicos, promesas que exceden deuda, horarios inusuales, agentes con rendimiento atípico y cambios bruscos de sentimiento.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_estrategias",
        "description": "Optimización de estrategias: genera recomendaciones de cobranza, segmentación de cartera (quick wins, alto potencial, críticos), mejores horarios y asignación de agentes.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# ─────────────────────────────────────────────────────────────────
# Tool executor (independiente del proveedor LLM)
# ─────────────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, tool_input: dict) -> Any:
    """Despacha la tool solicitada por el LLM y retorna el resultado crudo."""
    logger.info("[mcp] tool=%s args=%s", tool_name, tool_input)

    try:
        if tool_name == "get_dashboard":
            result = gs.get_dashboard()
        elif tool_name == "get_clientes":
            result = gs.get_all_clientes()
        elif tool_name == "get_cliente_detalle":
            result = gs.get_cliente_by_id(tool_input.get("cliente_id", ""))
            if result is None:
                result = {"error": "not_found", "cliente_id": tool_input.get("cliente_id")}
        elif tool_name == "get_cliente_timeline":
            result = gs.get_cliente_timeline(tool_input.get("cliente_id", ""))
            if result is None:
                result = {"error": "not_found", "cliente_id": tool_input.get("cliente_id")}
        elif tool_name == "get_agentes":
            result = gs.get_all_agentes()
        elif tool_name == "get_agente_efectividad":
            result = gs.get_agente_efectividad(tool_input.get("agente_id", ""))
            if result is None:
                result = {"error": "not_found", "agente_id": tool_input.get("agente_id")}
        elif tool_name == "get_promesas_incumplidas":
            result = gs.get_promesas_incumplidas(tool_input.get("fecha"))
        elif tool_name == "get_mejores_horarios":
            result = gs.get_mejores_horarios(tool_input.get("resultado"))
        elif tool_name == "get_prediccion_clientes":
            result = ans.get_prediccion_clientes()
        elif tool_name == "get_anomalias":
            result = ans.get_anomalias()
        elif tool_name == "get_estrategias":
            result = ans.get_estrategias()
        else:
            result = {"error": "unknown_tool", "tool_name": tool_name}
    except Exception as e:
        logger.exception("[mcp] error executing tool %s: %s", tool_name, e)
        result = {"error": "tool_execution_error", "tool_name": tool_name, "message": str(e)}

    logger.info("[mcp] tool=%s → %d chars", tool_name, len(str(result)))
    return result


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

async def query_mcp(query: str, params: dict | None = None) -> dict[str, Any]:
    """
    Procesa una consulta en lenguaje natural usando el proveedor LLM activo.

    Selección de proveedor (variable LLM_PROVIDER en .env, default "auto"):
      auto      → Gemini si GEMINI_API_KEY presente, sino Anthropic
      gemini    → Fuerza Gemini
      anthropic → Fuerza Anthropic

    Retorna siempre la misma estructura de respuesta independientemente
    del proveedor, para no romper la interfaz del endpoint.
    """
    provider = get_provider(settings)

    if provider is None:
        return {
            "status": "error",
            "error": "mcp_not_configured",
            "message": (
                "No hay proveedor LLM configurado. "
                "Define GEMINI_API_KEY (gratis en aistudio.google.com) "
                "o ANTHROPIC_API_KEY en el archivo .env."
            ),
            "respuesta": "",
            "datos": [],
        }

    return await provider.run(
        query=query,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        execute_tool=_execute_tool,
        max_iterations=5,
    )
