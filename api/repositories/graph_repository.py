"""
Interfaz del repositorio de grafo (B1).

Cualquier implementación (SQLite local, Neo4j real) debe exponer estos
métodos para que services/ y routers/ sean agnósticos al backend.

Diseño: primitivas mínimas + 3 helpers semánticos para evitar N+1 en los
patrones más comunes del dominio (Cliente → Interaccion → Pago/Promesa/Plan).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class GraphRepository(ABC):
    """Contrato de lectura del grafo. Debe ser backend-agnóstico."""

    # ---- primitivas ----

    @abstractmethod
    async def get_nodes_by_label(
        self, label: str, limit: int | None = None, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Retorna [{id, properties}] para nodos del label dado."""

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[dict[str, Any]]:
        """Retorna {id, label, properties} o None."""

    @abstractmethod
    async def get_outgoing(
        self, from_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Retorna aristas salientes: [{from_id, rel_type, to_id, properties}]."""

    @abstractmethod
    async def get_incoming(
        self, to_id: str, rel_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Retorna aristas entrantes."""

    @abstractmethod
    async def count_nodes_by_label(self, label: str) -> int:
        """Total de nodos del label (útil para paginación)."""

    # ---- helpers semánticos (anti N+1) ----

    @abstractmethod
    async def get_outgoing_nodes(
        self,
        from_id: str,
        rel_type: str,
        target_label: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Un salto: desde `from_id` via `rel_type` llega a los nodos destino.
        Retorna `[{id, label, properties}]` de los nodos destino (filtrando
        opcionalmente por `target_label`). Se implementa server-side para
        evitar el patrón N+1 (edge lookup + node lookup).
        """

    @abstractmethod
    async def get_two_hop_nodes(
        self,
        from_id: str,
        rel1: str,
        intermediate_label: str,
        rel2: str,
        target_label: str,
    ) -> list[dict[str, Any]]:
        """
        Dos saltos: `from_id -[rel1]-> (:intermediate_label) -[rel2]-> (:target_label)`.
        Retorna los nodos destino finales con sus properties. Patrón canónico
        Cliente → Interaccion → Pago / Promesa / Plan.
        """

    @abstractmethod
    async def get_all_relationships(
        self, rel_types: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """
        Retorna todas las aristas del grafo. Filtro opcional por `rel_types`.
        Usado por el renderer D3.js (`/grafo/relaciones`).
        """
