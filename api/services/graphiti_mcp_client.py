"""
graphiti_mcp_client.py — Cliente MCP para el servidor oficial de Graphiti.

Referencia: https://help.getzep.com/v3/graphiti/getting-started/mcp-server

Responsabilidades:
  - Abrir/cerrar sesión Streamable HTTP contra el MCP server.
  - Descubrir las tools expuestas (list_tools) en tiempo de arranque.
  - Ejecutar una tool (call_tool) devolviendo el resultado serializable.

Uso desde el chat (mcp_service.py):
  tools = await list_mcp_tools()           → lista con schemas (formato LLM)
  result = await call_mcp_tool(name, args) → str/dict listo para feedback al LLM

El cliente es resiliente: si el MCP server no responde, las funciones devuelven
lista vacía / dict de error sin romper el chat local (las tools de analítica y
predicción siguen disponibles).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from api.config import settings

logger = logging.getLogger(__name__)

# Tools que NO queremos exponer al LLM del chat (destructivas / admin).
# Conservadoras: `clear_graph` y `delete_*` quedan fuera por defecto.
# Tools bloqueadas: destructivas/admin + add_memory (escritura, no útil en chat de consulta)
_BLOCKED_TOOLS: set[str] = {
    "clear_graph",
    "delete_entity_edge",
    "delete_episode",
    "add_memory",
    "get_entity_edge",
    "get_episodes",
}


def _mcp_enabled() -> bool:
    return bool(settings.graphiti_mcp_url)


def _mcp_host_header() -> dict[str, str]:
    """
    El Graphiti MCP server valida el header Host contra el host de arranque
    (localhost). Desde dentro de Docker la conexión llega con Host=graphiti-mcp:8000,
    lo que provoca 421 Misdirected Request. Forzamos Host: localhost:8000 para
    que el servidor acepte la petición.
    """
    from urllib.parse import urlparse
    parsed = urlparse(settings.graphiti_mcp_url)
    # Solo añadimos override si el host NO es localhost (entorno Docker).
    if parsed.hostname not in ("localhost", "127.0.0.1"):
        return {"Host": f"localhost:{parsed.port or 8000}"}
    return {}


async def _with_session(fn):
    """
    Abre una sesión Streamable HTTP contra el MCP server y ejecuta `fn(session)`.
    El import de `mcp` es perezoso — si la librería no está instalada, devuelve None.
    """
    if not _mcp_enabled():
        return None

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError:
        logger.warning(
            "[mcp-client] librería `mcp` no disponible — instalar con `pip install mcp`."
        )
        return None

    try:
        async with streamablehttp_client(
            settings.graphiti_mcp_url,
            headers=_mcp_host_header(),
        ) as (read_stream, write_stream, _get_session_id):
            async with ClientSession(read_stream, write_stream) as session:
                await asyncio.wait_for(session.initialize(), timeout=8.0)
                return await asyncio.wait_for(fn(session), timeout=10.0)
    except Exception as exc:
        logger.warning(
            "[mcp-client] error conectando a %s: %s",
            settings.graphiti_mcp_url, exc,
        )
        return None


def _tool_to_llm_schema(tool) -> dict[str, Any]:
    """Convierte un `mcp.types.Tool` al formato schema usado por mcp_service.TOOLS."""
    schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    return {
        "name": f"mcp__{tool.name}",  # namespace para evitar colisiones con tools locales
        "description": (
            f"[Graphiti MCP] {tool.description or tool.name}"
        ),
        "input_schema": schema,
    }


async def list_mcp_tools() -> list[dict[str, Any]]:
    """
    Lista las tools expuestas por el MCP server en el schema que usa el chat.
    Devuelve [] si el MCP no está disponible.
    """
    async def _list(session):
        resp = await session.list_tools()
        out: list[dict[str, Any]] = []
        for t in resp.tools:
            if t.name in _BLOCKED_TOOLS:
                continue
            out.append(_tool_to_llm_schema(t))
        return out

    tools = await _with_session(_list)
    return tools or []


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    Ejecuta una tool del MCP server y devuelve el resultado en forma serializable.
    Si viene namespacada (`mcp__foo`), la desnamespaca antes de invocar.
    """
    real_name = tool_name.removeprefix("mcp__")

    if real_name in _BLOCKED_TOOLS:
        return {"error": "tool_blocked", "tool_name": real_name,
                "message": "Esta tool está bloqueada por política de servidor."}

    async def _call(session):
        result = await session.call_tool(real_name, arguments or {})
        # `result.content` es una lista de TextContent / ImageContent / ResourceContents.
        parts: list[Any] = []
        for block in (result.content or []):
            # TextContent tiene .text; otros tipos los serializamos tal cual.
            text = getattr(block, "text", None)
            if text is not None:
                # Muchas tools de Graphiti devuelven JSON stringificado: intentamos parsear.
                try:
                    parts.append(json.loads(text))
                except (json.JSONDecodeError, TypeError):
                    parts.append(text)
            else:
                parts.append(getattr(block, "model_dump", lambda: str(block))())
        if len(parts) == 1:
            return parts[0]
        return parts

    payload = await _with_session(_call)
    if payload is None:
        return {
            "error": "mcp_unavailable",
            "tool_name": real_name,
            "message": (
                "El servidor MCP de Graphiti no está disponible. "
                "Verifica que el contenedor `graphiti-mcp` esté en ejecución."
            ),
        }
    return payload


def run_async(coro):
    """Helper sync→async para invocar desde `_execute_tool` que no es async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Estamos dentro de FastAPI; ejecutamos en un loop dedicado via run_until_complete
            # sólo si no es el loop principal. En práctica usamos asyncio.run desde contexto sync.
            return asyncio.ensure_future(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)
