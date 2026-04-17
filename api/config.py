"""
Configuration module using pydantic-settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # API settings
    app_name: str = Field(
        default="Call Pattern Analyzer API", description="Application name"
    )
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    port: int = Field(default=8001, description="Port to bind the server to")

    # Database
    db_path: str = Field(
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ingesta",
            "local_graph.db",
        ),
        description="Path to the SQLite database",
    )

    # Neo4j (for Graphiti integration)
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j Bolt URI",
    )
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password123", description="Neo4j password")

    # Graphiti
    graphiti_url: str = Field(
        default="http://localhost:8000",
        description="Graphiti API URL",
    )
    graphiti_mcp_url: str = Field(
        default="http://localhost:8020/mcp",
        description=(
            "Endpoint Streamable HTTP del servidor MCP oficial de Graphiti. "
            "Deja vacío para desactivar la integración MCP real."
        ),
    )
    use_neo4j: bool = Field(
        default=False,
        description="Use Neo4j instead of SQLite",
    )
    graph_backend: str = Field(
        default="graphiti",
        description=(
            "Active read backend: "
            "'graphiti' (default — acceso a Neo4j vía graphiti-core, fuente única de verdad), "
            "'neo4j' (driver neo4j directo), "
            "'sqlite' (fallback local sin Neo4j)."
        ),
    )
    graphiti_group_id: str = Field(
        default="prueba-tecnica",
        description="Group ID de Graphiti para aislar el grafo del proyecto.",
    )
    promesa_cumplida_mode: str = Field(
        default="snapshot",
        description=(
            "'snapshot' (leer props.cumplida, rápido) o 'dynamic' (compute-on-read "
            "a partir de Pago dentro de grace_days — C4 event-free)."
        ),
    )
    promesa_grace_days: int = Field(
        default=3,
        description="Ventana de gracia para considerar una promesa cumplida (C6).",
    )

    # CORS — list expected (comma-separated in env). Use explicit origins when you
    # need credentials; leave ["*"] for public read-only APIs.
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # LLM providers (for /mcp/query natural language endpoint)
    anthropic_api_key: str = Field(default="", description="Anthropic API key (Claude)")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    openai_api_key: str = Field(default="", description="OpenAI API key (GPT)")
    groq_api_key: str = Field(default="", description="Groq API key (gratis — console.groq.com)")
    openrouter_api_key: str = Field(default="", description="OpenRouter API key (openrouter.ai — modelos :free disponibles)")
    llm_provider: str = Field(
        default="auto",
        description=(
            "LLM provider: 'auto' (OpenRouter > Groq > OpenAI > Gemini > Anthropic), "
            "'openrouter', 'groq', 'openai', 'gemini', 'anthropic'."
        ),
    )
    mcp_enabled: bool = Field(default=False, description="Whether MCP is enabled")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
