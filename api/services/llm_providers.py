"""
llm_providers.py — Abstracción intercambiable de proveedores LLM.

Proveedores disponibles:
  - OpenRouterProvider: OpenRouter (gratis con modelos :free — openrouter.ai)
  - GroqProvider      : Groq (GRATIS, sin tarjeta — llama-3.3-70b con function calling)
  - OpenAIProvider    : OpenAI GPT (requiere créditos)
  - GeminiProvider    : Google Gemini (free tier con límites)
  - AnthropicProvider : Anthropic Claude (requiere créditos)

Selección automática via factory `get_provider(settings)`:
  - llm_provider = "auto"        → OpenRouter > Groq > OpenAI > Gemini > Anthropic
  - llm_provider = "openrouter"  → OpenRouter (falla si no hay key)
  - llm_provider = "groq"        → Groq (falla si no hay key)
  - llm_provider = "openai"      → OpenAI
  - llm_provider = "gemini"      → Gemini
  - llm_provider = "anthropic"   → Anthropic
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
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
        execute_tool: Callable[[str, dict], Awaitable[Any]],
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
        execute_tool: Callable[[str, dict], Awaitable[Any]],
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

                    result = await execute_tool(fc.name, dict(fc.args))
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
# OpenRouter Provider  (OpenAI-compatible API — modelos :free disponibles)
# ─────────────────────────────────────────────────────────────────

class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter — gateway multi-modelo con tier gratuito.
    Modelos :free con function calling confirmado:
      - meta-llama/llama-3.3-70b-instruct:free  (default)
      - mistralai/mistral-small-3.1-24b-instruct:free
    Registro: https://openrouter.ai
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    @staticmethod
    def _build_tools(tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    async def run(
        self,
        query: str,
        system_prompt: str,
        tools: list[dict],
        execute_tool: Callable[[str, dict], Awaitable[Any]],
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        from openai import OpenAI, AuthenticationError, RateLimitError, BadRequestError, APIStatusError

        queries_ejecutadas: list[str] = []
        tokens_usados = 0
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        or_tools = self._build_tools(tools)

        try:
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL,
                default_headers={"HTTP-Referer": "https://github.com", "X-Title": "prueba-tecnica"},
            )

            for _ in range(max_iterations):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    tools=or_tools,     # type: ignore[arg-type]
                    temperature=0.1,
                )

                if response.usage:
                    tokens_usados += (response.usage.prompt_tokens or 0) + (
                        response.usage.completion_tokens or 0
                    )

                msg = response.choices[0].message
                tool_calls = msg.tool_calls or []

                if not tool_calls:
                    return {
                        "status": "ok",
                        "respuesta": (msg.content or "").strip(),
                        "datos": [],
                        "queries_ejecutadas": queries_ejecutadas,
                        "tokens_usados": tokens_usados,
                        "proveedor": f"openrouter/{self.model}",
                    }

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    queries_ejecutadas.append(name)
                    logger.info("[openrouter] tool=%s args=%s", name, args)
                    result = await execute_tool(name, args)
                    logger.info("[openrouter] tool=%s → %d chars", name, len(str(result)))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

        except AuthenticationError:
            return {"status": "error", "error": "auth_error",
                    "message": "OPENROUTER_API_KEY inválida.", "respuesta": "", "datos": []}
        except RateLimitError as e:
            return {"status": "error", "error": "quota_exceeded",
                    "message": f"Rate limit de OpenRouter alcanzado: {str(e)[:150]}",
                    "respuesta": "", "datos": []}
        except BadRequestError as e:
            return {"status": "error", "error": "bad_request",
                    "message": f"Error en solicitud a OpenRouter: {str(e)[:200]}",
                    "respuesta": "", "datos": []}
        except APIStatusError as e:
            return {"status": "error", "error": "api_error",
                    "message": f"Error API OpenRouter (HTTP {e.status_code})",
                    "respuesta": "", "datos": []}
        except Exception as e:
            logger.exception("[openrouter] unexpected error: %s", e)
            return {"status": "error", "error": "internal_error",
                    "message": f"Error interno con OpenRouter: {type(e).__name__}",
                    "respuesta": "", "datos": []}

        return {
            "status": "ok",
            "respuesta": "Se alcanzó el límite de iteraciones.",
            "datos": [], "queries_ejecutadas": queries_ejecutadas,
            "tokens_usados": tokens_usados, "proveedor": f"openrouter/{self.model}",
        }


# ─────────────────────────────────────────────────────────────────
# Groq Provider  (OpenAI-compatible API — gratis, sin tarjeta)
# ─────────────────────────────────────────────────────────────────

class GroqProvider(BaseLLMProvider):
    """
    Groq — free tier generoso (14 400 req/día, sin tarjeta).
    Usa la API compatible con OpenAI, modelo llama-3.3-70b-versatile
    que soporta function calling completo.
    Registro: https://console.groq.com
    """

    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    @staticmethod
    def _build_tools(tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    async def run(
        self,
        query: str,
        system_prompt: str,
        tools: list[dict],
        execute_tool: Callable[[str, dict], Awaitable[Any]],
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        from openai import OpenAI, AuthenticationError, RateLimitError, BadRequestError, APIStatusError

        queries_ejecutadas: list[str] = []
        tokens_usados = 0
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        groq_tools = self._build_tools(tools)

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.BASE_URL)

            for _ in range(max_iterations):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    tools=groq_tools,   # type: ignore[arg-type]
                    temperature=0.1,
                )

                if response.usage:
                    tokens_usados += (response.usage.prompt_tokens or 0) + (
                        response.usage.completion_tokens or 0
                    )

                msg = response.choices[0].message
                tool_calls = msg.tool_calls or []

                if not tool_calls:
                    return {
                        "status": "ok",
                        "respuesta": (msg.content or "").strip(),
                        "datos": [],
                        "queries_ejecutadas": queries_ejecutadas,
                        "tokens_usados": tokens_usados,
                        "proveedor": f"groq/{self.model}",
                    }

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    queries_ejecutadas.append(name)
                    logger.info("[groq] tool=%s args=%s", name, args)
                    result = await execute_tool(name, args)
                    logger.info("[groq] tool=%s → %d chars", name, len(str(result)))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

        except AuthenticationError:
            return {"status": "error", "error": "auth_error",
                    "message": "GROQ_API_KEY inválida.", "respuesta": "", "datos": []}
        except RateLimitError as e:
            return {"status": "error", "error": "quota_exceeded",
                    "message": f"Rate limit de Groq alcanzado: {str(e)[:150]}",
                    "respuesta": "", "datos": []}
        except BadRequestError as e:
            return {"status": "error", "error": "bad_request",
                    "message": f"Error en solicitud a Groq: {str(e)[:200]}",
                    "respuesta": "", "datos": []}
        except APIStatusError as e:
            if e.status_code == 413:
                return {"status": "error", "error": "bad_request",
                        "message": "Respuesta demasiado grande para el modelo. Intenta una consulta más específica.",
                        "respuesta": "", "datos": []}
            return {"status": "error", "error": "api_error",
                    "message": f"Error API Groq (HTTP {e.status_code})",
                    "respuesta": "", "datos": []}
        except Exception as e:
            logger.exception("[groq] unexpected error: %s", e)
            return {"status": "error", "error": "internal_error",
                    "message": f"Error interno con Groq: {type(e).__name__}",
                    "respuesta": "", "datos": []}

        return {
            "status": "ok",
            "respuesta": "Se alcanzó el límite de iteraciones.",
            "datos": [], "queries_ejecutadas": queries_ejecutadas,
            "tokens_usados": tokens_usados, "proveedor": f"groq/{self.model}",
        }


# ─────────────────────────────────────────────────────────────────
# OpenAI Provider
# ─────────────────────────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """
    Proveedor OpenAI GPT con function calling (Chat Completions API).

    Schema de tools en formato Claude → convertido a OpenAI `tools=[{type,function}]`.
    """

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL

    @staticmethod
    def _build_openai_tools(tools: list[dict]) -> list[dict]:
        """Convierte schema Claude → OpenAI tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]

    async def run(
        self,
        query: str,
        system_prompt: str,
        tools: list[dict],
        execute_tool: Callable[[str, dict], Awaitable[Any]],
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        from openai import (
            OpenAI,
            AuthenticationError,
            RateLimitError,
            BadRequestError,
            APIStatusError,
        )

        queries_ejecutadas: list[str] = []
        tokens_usados = 0

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]
        openai_tools = self._build_openai_tools(tools)

        try:
            client = OpenAI(api_key=self.api_key)

            for _ in range(max_iterations):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,  # type: ignore[arg-type]
                    tools=openai_tools,  # type: ignore[arg-type]
                    temperature=0.1,
                )

                if response.usage:
                    tokens_usados += (response.usage.prompt_tokens or 0) + (
                        response.usage.completion_tokens or 0
                    )

                msg = response.choices[0].message
                tool_calls = msg.tool_calls or []

                if not tool_calls:
                    return {
                        "status": "ok",
                        "respuesta": (msg.content or "").strip(),
                        "datos": [],
                        "queries_ejecutadas": queries_ejecutadas,
                        "tokens_usados": tokens_usados,
                        "proveedor": f"openai/{self.model}",
                    }

                # Persistir el turno assistant con tool_calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )

                # Ejecutar cada tool_call y añadir el resultado como rol "tool"
                for tc in tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    queries_ejecutadas.append(name)
                    logger.info("[openai] tool=%s args=%s", name, args)

                    result = await execute_tool(name, args)
                    logger.info("[openai] tool=%s → %d chars", name, len(str(result)))

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        }
                    )

        except AuthenticationError:
            return {
                "status": "error",
                "error": "auth_error",
                "message": "OPENAI_API_KEY inválida.",
                "respuesta": "", "datos": [],
            }
        except RateLimitError as e:
            msg = str(e).lower()
            if "insufficient_quota" in msg or "quota" in msg:
                return {
                    "status": "error",
                    "error": "insufficient_credits",
                    "message": (
                        "Créditos insuficientes en OpenAI. "
                        "Recarga tu cuenta en https://platform.openai.com/account/billing."
                    ),
                    "respuesta": "", "datos": [],
                }
            return {
                "status": "error",
                "error": "quota_exceeded",
                "message": "Cuota de OpenAI agotada. Espera unos segundos e intenta de nuevo.",
                "respuesta": "", "datos": [],
            }
        except BadRequestError as e:
            return {
                "status": "error",
                "error": "bad_request",
                "message": f"Error en la solicitud a OpenAI: {str(e)[:200]}",
                "respuesta": "", "datos": [],
            }
        except APIStatusError as e:
            return {
                "status": "error",
                "error": "api_error",
                "message": f"Error de la API de OpenAI (HTTP {e.status_code})",
                "respuesta": "", "datos": [],
            }
        except Exception as e:
            logger.exception("[openai] unexpected error: %s", e)
            return {
                "status": "error",
                "error": "internal_error",
                "message": f"Error interno con OpenAI: {type(e).__name__}",
                "respuesta": "", "datos": [],
            }

        return {
            "status": "ok",
            "respuesta": "Se alcanzó el límite de iteraciones sin una respuesta final.",
            "datos": [],
            "queries_ejecutadas": queries_ejecutadas,
            "tokens_usados": tokens_usados,
            "proveedor": f"openai/{self.model}",
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
        execute_tool: Callable[[str, dict], Awaitable[Any]],
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
                            result = await execute_tool(block.name, block.input)
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
      1. OpenRouter si OPENROUTER_API_KEY presente
      2. Groq       si GROQ_API_KEY presente (gratis, sin tarjeta)
      3. OpenAI     si OPENAI_API_KEY presente
      4. Gemini     si GEMINI_API_KEY presente
      5. Anthropic  si ANTHROPIC_API_KEY presente
    """
    mode = (settings.llm_provider or "auto").lower()

    if mode in ("openrouter", "auto"):
        key = getattr(settings, "openrouter_api_key", "")
        if key:
            logger.info("[factory] proveedor seleccionado: OpenRouter")
            return OpenRouterProvider(api_key=key)
        if mode == "openrouter":
            return None

    if mode in ("groq", "auto"):
        key = getattr(settings, "groq_api_key", "")
        if key:
            logger.info("[factory] proveedor seleccionado: Groq")
            return GroqProvider(api_key=key)
        if mode == "groq":
            return None

    if mode in ("openai", "auto"):
        key = getattr(settings, "openai_api_key", "")
        if key and key.startswith("sk-"):
            logger.info("[factory] proveedor seleccionado: OpenAI")
            return OpenAIProvider(api_key=key)
        if mode == "openai":
            return None

    if mode in ("gemini", "auto"):
        key = getattr(settings, "gemini_api_key", "")
        if key:
            logger.info("[factory] proveedor seleccionado: Gemini")
            return GeminiProvider(api_key=key)
        if mode == "gemini":
            return None

    if mode in ("anthropic", "auto"):
        key = getattr(settings, "anthropic_api_key", "")
        if key and key.startswith("sk-ant-"):
            logger.info("[factory] proveedor seleccionado: Anthropic")
            return AnthropicProvider(api_key=key)

    return None
