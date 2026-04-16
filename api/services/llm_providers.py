"""
llm_providers.py — Abstracción intercambiable de proveedores LLM.

Proveedores disponibles:
  - GeminiProvider  : Google Gemini (free tier con GEMINI_API_KEY)
  - AnthropicProvider: Anthropic Claude (requiere créditos)

Selección automática via factory `get_provider(settings)`:
  - llm_provider = "auto"      → Gemini si hay GEMINI_API_KEY, sino Anthropic
  - llm_provider = "gemini"    → Gemini (falla si no hay key)
  - llm_provider = "anthropic" → Anthropic (falla si no hay key)
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """Contrato común para todos los proveedores LLM."""

    @abstractmethod
    async def run(
        self,
        query: str,
        system_prompt: str,
        tools: list[dict],
        execute_tool: Callable[[str, dict], Any],
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        """
        Ejecuta la consulta en lenguaje natural con function calling.

        Retorna:
          {
            "status": "ok" | "error",
            "respuesta": str,
            "datos": list,
            "queries_ejecutadas": list[str],
            "tokens_usados": int,
            "proveedor": str,
            # solo en caso de error:
            "error": str,
            "message": str,
          }
        """


# ─────────────────────────────────────────────────────────────────
# Gemini Provider
# ─────────────────────────────────────────────────────────────────

class GeminiProvider(BaseLLMProvider):
    """
    Proveedor Google Gemini usando google-genai SDK >= 1.0.
    Modelo por defecto: gemini-2.0-flash (free tier).
    """

    DEFAULT_MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Tool format conversion: Claude schema → Gemini FunctionDeclaration
    # ------------------------------------------------------------------

    @staticmethod
    def _build_gemini_tools(tools: list[dict]):
        from google.genai import types

        declarations = []
        for t in tools:
            schema_dict = t.get("input_schema", {})
            props_raw = schema_dict.get("properties", {})
            required = schema_dict.get("required", [])

            # Convierte cada propiedad a types.Schema
            properties: dict[str, types.Schema] = {}
            for prop_name, prop_def in props_raw.items():
                prop_type_str = prop_def.get("type", "string").upper()
                prop_type = getattr(types.Type, prop_type_str, types.Type.STRING)
                properties[prop_name] = types.Schema(
                    type=prop_type,
                    description=prop_def.get("description", ""),
                )

            # Construye el Schema del parámetro principal
            params_schema = types.Schema(
                type=types.Type.OBJECT,
                properties=properties if properties else None,
                required=required if required else None,
            )

            declarations.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=params_schema,
                )
            )

        return types.Tool(function_declarations=declarations)

    # ------------------------------------------------------------------
    # Extrae todas las function_call parts de una respuesta
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fn_calls(response) -> list:
        """Devuelve lista de parts con function_call activo."""
        try:
            parts = response.candidates[0].content.parts or []
        except (AttributeError, IndexError):
            return []
        return [p for p in parts if p.function_call and p.function_call.name]

    @staticmethod
    def _extract_text(response) -> str:
        """Extrae el texto final de la respuesta."""
        try:
            parts = response.candidates[0].content.parts or []
            for p in parts:
                if p.text:
                    return p.text
        except (AttributeError, IndexError, ValueError):
            pass
        return ""

    @staticmethod
    def _tokens(response) -> int:
        try:
            return response.usage_metadata.total_token_count or 0
        except AttributeError:
            return 0

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(
        self,
        query: str,
        system_prompt: str,
        tools: list[dict],
        execute_tool: Callable[[str, dict], Any],
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        from google import genai
        from google.genai import types

        queries_ejecutadas: list[str] = []
        tokens_usados = 0

        try:
            client = genai.Client(api_key=self.api_key)
            gemini_tool = self._build_gemini_tools(tools)

            chat = client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[gemini_tool],
                    temperature=0.1,
                ),
            )

            response = chat.send_message(query)
            tokens_usados += self._tokens(response)

            for _ in range(max_iterations):
                fn_calls = self._extract_fn_calls(response)

                if not fn_calls:
                    # Sin más tool calls → respuesta final
                    return {
                        "status": "ok",
                        "respuesta": self._extract_text(response),
                        "datos": [],
                        "queries_ejecutadas": queries_ejecutadas,
                        "tokens_usados": tokens_usados,
                        "proveedor": f"gemini/{self.model}",
                    }

                # Ejecutar todas las tools en este turno
                fn_response_parts = []
                for part in fn_calls:
                    fc = part.function_call
                    queries_ejecutadas.append(fc.name)
                    logger.info("[gemini] tool=%s args=%s", fc.name, dict(fc.args))

                    result = execute_tool(fc.name, dict(fc.args))
                    logger.info("[gemini] tool=%s → %d chars", fc.name, len(str(result)))

                    fn_response_parts.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={
                                    "result": json.dumps(
                                        result, ensure_ascii=False, default=str
                                    )
                                },
                            )
                        )
                    )

                response = chat.send_message(
                    types.Content(parts=fn_response_parts, role="user")
                )
                tokens_usados += self._tokens(response)

        except Exception as e:
            # google.genai usa su propio árbol de excepciones (no google.api_core)
            from google.genai import errors as genai_errors

            err_str = str(e)
            status_code = getattr(e, "status_code", None) or getattr(e, "code", None)

            if isinstance(e, genai_errors.ClientError):
                if status_code == 401 or "API_KEY_INVALID" in err_str or "permission" in err_str.lower():
                    return {
                        "status": "error",
                        "error": "auth_error",
                        "message": "GEMINI_API_KEY inválida o sin permisos.",
                        "respuesta": "", "datos": [],
                    }
                if status_code == 429 or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    return {
                        "status": "error",
                        "error": "quota_exceeded",
                        "message": "Cuota de Gemini agotada. Espera unos minutos o revisa tu plan en aistudio.google.com.",
                        "respuesta": "", "datos": [],
                    }
                if status_code == 400 or "INVALID_ARGUMENT" in err_str:
                    return {
                        "status": "error",
                        "error": "bad_request",
                        "message": f"Argumento inválido en la solicitud a Gemini: {err_str[:200]}",
                        "respuesta": "", "datos": [],
                    }
                return {
                    "status": "error",
                    "error": "api_error",
                    "message": f"Error de la API de Gemini (HTTP {status_code}): {err_str[:200]}",
                    "respuesta": "", "datos": [],
                }

            logger.exception("[gemini] unexpected error: %s", e)
            return {
                "status": "error",
                "error": "internal_error",
                "message": f"Error interno con Gemini: {type(e).__name__}: {err_str[:200]}",
                "respuesta": "", "datos": [],
            }

        # Máximo de iteraciones alcanzado
        return {
            "status": "ok",
            "respuesta": "Se alcanzó el límite de iteraciones sin una respuesta final.",
            "datos": [],
            "queries_ejecutadas": queries_ejecutadas,
            "tokens_usados": tokens_usados,
            "proveedor": f"gemini/{self.model}",
        }


# ─────────────────────────────────────────────────────────────────
# Anthropic Provider
# ─────────────────────────────────────────────────────────────────

class AnthropicProvider(BaseLLMProvider):
    """
    Proveedor Anthropic Claude.
    Requiere créditos en la cuenta de Anthropic.
    """

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    async def run(
        self,
        query: str,
        system_prompt: str,
        tools: list[dict],
        execute_tool: Callable[[str, dict], Any],
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        import anthropic

        queries_ejecutadas: list[str] = []
        tokens_usados = 0
        messages: list[dict] = [{"role": "user", "content": query}]

        try:
            client = anthropic.Anthropic(api_key=self.api_key)

            for _ in range(max_iterations):
                response = client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    tools=tools,  # type: ignore[arg-type]
                    messages=messages,
                )

                tokens_usados += (
                    response.usage.input_tokens + response.usage.output_tokens
                )

                if response.stop_reason == "end_turn":
                    respuesta = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            respuesta = block.text
                            break
                    return {
                        "status": "ok",
                        "respuesta": respuesta,
                        "datos": [],
                        "queries_ejecutadas": queries_ejecutadas,
                        "tokens_usados": tokens_usados,
                        "proveedor": f"anthropic/{self.model}",
                    }

                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            queries_ejecutadas.append(block.name)
                            logger.info("[anthropic] tool=%s args=%s", block.name, block.input)
                            result = execute_tool(block.name, block.input)
                            logger.info("[anthropic] tool=%s → %d chars", block.name, len(str(result)))
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": json.dumps(
                                        result, ensure_ascii=False, default=str
                                    ),
                                }
                            )
                    messages.append({"role": "user", "content": tool_results})
                    continue

                break  # stop_reason desconocido

        except anthropic.AuthenticationError:
            return {
                "status": "error",
                "error": "auth_error",
                "message": "ANTHROPIC_API_KEY inválida.",
                "respuesta": "", "datos": [],
            }
        except anthropic.BadRequestError as e:
            msg = str(e)
            if "credit balance" in msg.lower() or "too low" in msg.lower():
                return {
                    "status": "error",
                    "error": "insufficient_credits",
                    "message": "Créditos insuficientes en Anthropic. Visita console.anthropic.com.",
                    "respuesta": "", "datos": [],
                }
            return {
                "status": "error",
                "error": "bad_request",
                "message": f"Error en la solicitud a Claude: {msg}",
                "respuesta": "", "datos": [],
            }
        except anthropic.APIStatusError as e:
            return {
                "status": "error",
                "error": "api_error",
                "message": f"Error de la API de Anthropic (HTTP {e.status_code})",
                "respuesta": "", "datos": [],
            }
        except Exception as e:
            logger.exception("[anthropic] unexpected error: %s", e)
            return {
                "status": "error",
                "error": "internal_error",
                "message": f"Error interno con Anthropic: {type(e).__name__}",
                "respuesta": "", "datos": [],
            }

        return {
            "status": "ok",
            "respuesta": "Se alcanzó el límite de iteraciones sin una respuesta final.",
            "datos": [],
            "queries_ejecutadas": queries_ejecutadas,
            "tokens_usados": tokens_usados,
            "proveedor": f"anthropic/{self.model}",
        }


# ─────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────

def get_provider(settings) -> BaseLLMProvider | None:
    """
    Devuelve el proveedor activo según la configuración.

    Lógica de selección con llm_provider = "auto":
      1. Gemini si GEMINI_API_KEY está presente
      2. Anthropic si ANTHROPIC_API_KEY está presente
      3. None si no hay ninguna key configurada
    """
    mode = (settings.llm_provider or "auto").lower()

    if mode in ("gemini", "auto"):
        key = settings.gemini_api_key
        if key:
            logger.info("[factory] proveedor seleccionado: Gemini")
            return GeminiProvider(api_key=key)
        if mode == "gemini":
            return None  # explícitamente solicitado pero sin key

    if mode in ("anthropic", "auto"):
        key = settings.anthropic_api_key
        if key and key.startswith("sk-ant-"):
            logger.info("[factory] proveedor seleccionado: Anthropic")
            return AnthropicProvider(api_key=key)

    return None
