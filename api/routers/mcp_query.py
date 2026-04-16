"""
Router for /mcp/query endpoint.
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.mcp_service import query_mcp

router = APIRouter(prefix="/mcp", tags=["MCP"])


class MCPQueryRequest(BaseModel):
    query: str = Field(..., max_length=500)


class MCPQueryResponse(BaseModel):
    respuesta: str
    datos: list = []
    queries_ejecutadas: list[str] = []
    tokens_usados: int = 0


@router.post("/query", response_model=MCPQueryResponse, summary="Consulta en lenguaje natural")
async def mcp_query(body: MCPQueryRequest):
    """
    Procesa una consulta en lenguaje natural sobre el grafo de conocimiento
    usando Claude (Anthropic) con tool use.
    Requiere ANTHROPIC_API_KEY configurada en el entorno.
    """
    result = await query_mcp(query=body.query)

    error = result.get("error")
    if error in ("mcp_not_configured", "auth_error", "insufficient_credits", "api_error"):
        raise HTTPException(
            status_code=503,
            detail={
                "error": error,
                "message": result.get("message", "Servicio MCP no disponible"),
            },
        )
    if error == "bad_request":
        raise HTTPException(
            status_code=400,
            detail={"error": error, "message": result.get("message", "")},
        )
    if error == "internal_error":
        raise HTTPException(status_code=500, detail={"error": error})

    return MCPQueryResponse(
        respuesta=result.get("respuesta", ""),
        datos=result.get("datos", []),
        queries_ejecutadas=result.get("queries_ejecutadas", []),
        tokens_usados=result.get("tokens_usados", 0),
    )
