"""
Interfaz del repositorio de grafo (B1).

Cualquier implementación (SQLite local, Neo4j+Graphiti real) debe exponer
estos métodos para que services/ y routers/ sean agnósticos al backend.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class GraphRepository(ABC):
    """Contrato mínimo para un backend de lectura del grafo."""

    @abstractmethod
    def get_nodes_by_label(
        self, label: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Retorna [{id, properties}] para nodos del label dado."""

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        """Retorna {id, label, properties} o None."""

    @abstractmethod
    def get_outgoing(
        self, from_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Retorna aristas salientes: [{from_id, rel_type, to_id, properties}]."""

    @abstractmethod
    def get_incoming(
        self, to_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Retorna aristas entrantes."""

    @abstractmethod
    def count_nodes_by_label(self, label: str) -> int:
        """Total de nodos del label (útil para paginación)."""
