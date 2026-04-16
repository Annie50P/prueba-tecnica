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
    use_neo4j: bool = Field(
        default=False,
        description="Use Neo4j instead of SQLite",
    )

    # CORS
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")

    # LLM providers (for /mcp/query natural language endpoint)
    anthropic_api_key: str = Field(default="", description="Anthropic API key (Claude)")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    llm_provider: str = Field(
        default="auto",
        description="LLM provider: 'auto' (Gemini if available, else Anthropic), 'gemini', 'anthropic'",
    )
    mcp_enabled: bool = Field(default=False, description="Whether MCP is enabled")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
