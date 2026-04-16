"""
GraphitiClient – HTTP client for the Graphiti/Neo4j API with automatic
SQLite fallback when the remote service is unavailable.

SQLite schema
-------------
    nodes         (id TEXT PRIMARY KEY, label TEXT, properties TEXT)
    relationships (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   from_id TEXT, rel_type TEXT, to_id TEXT, properties TEXT)
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from typing import Any, Dict, Optional

try:
    import requests
    from requests.exceptions import ConnectionError, RequestException, Timeout
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Default configuration (overridden by environment variables / constructor)
# ---------------------------------------------------------------------------
_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_TIMEOUT = 5        # seconds per request attempt
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY = 1.0  # seconds between retries
_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_graph.db")


class GraphitiClient:
    """Thin wrapper around the Graphiti HTTP API.

    Falls back to a local SQLite database automatically when the Graphiti
    service is not reachable.  All public methods have identical signatures
    regardless of which backend is active.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_delay: float = _DEFAULT_RETRY_DELAY,
        db_path: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("GRAPHITI_URL", _DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = int(os.environ.get("GRAPHITI_TIMEOUT", timeout))
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.db_path = db_path or os.environ.get("GRAPHITI_DB_PATH", _DEFAULT_DB_PATH)

        # Will be set to True once health_check() confirms the service is up
        self._graphiti_available: Optional[bool] = None

        # Initialise SQLite (always – used as fallback or primary)
        self._sqlite_conn = self._init_sqlite()

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _init_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id         TEXT PRIMARY KEY,
                label      TEXT,
                properties TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id    TEXT,
                rel_type   TEXT,
                to_id      TEXT,
                properties TEXT
            )
            """
        )
        conn.commit()
        return conn

    def _sqlite_create_node(self, label: str, properties: Dict[str, Any]) -> str:
        node_id = properties.get("id") or str(uuid.uuid4())
        props_json = json.dumps(properties, ensure_ascii=False, default=str)
        self._sqlite_conn.execute(
            "INSERT OR REPLACE INTO nodes (id, label, properties) VALUES (?, ?, ?)",
            (node_id, label, props_json),
        )
        self._sqlite_conn.commit()
        return node_id

    def _sqlite_create_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        props_json = json.dumps(properties, ensure_ascii=False, default=str)
        self._sqlite_conn.execute(
            "INSERT INTO relationships (from_id, rel_type, to_id, properties) VALUES (?, ?, ?, ?)",
            (from_id, rel_type, to_id, props_json),
        )
        self._sqlite_conn.commit()
        return True

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _http_post(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict]:
        """POST to Graphiti API with retry logic.  Returns parsed JSON or None."""
        if not _REQUESTS_AVAILABLE:
            return None

        url = f"{self.base_url}{endpoint}"
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                return resp.json()
            except (ConnectionError, Timeout) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
            except RequestException as exc:
                # Non-connection error (e.g. 4xx/5xx) – don't retry
                raise

        # All retries exhausted
        return None

    def _http_get(self, endpoint: str) -> Optional[Dict]:
        if not _REQUESTS_AVAILABLE:
            return None

        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """Return True if the Graphiti service is reachable and healthy."""
        if not _REQUESTS_AVAILABLE:
            self._graphiti_available = False
            return False

        result = self._http_get("/health")
        self._graphiti_available = result is not None
        return self._graphiti_available

    def _use_graphiti(self) -> bool:
        """Decide whether to use the remote service for this call."""
        if self._graphiti_available is None:
            # Lazy first check
            self.health_check()
        return bool(self._graphiti_available)

    def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """Create a node.  Returns the node id."""
        if self._use_graphiti():
            try:
                result = self._http_post("/nodes", {"label": label, "properties": properties})
                if result and "id" in result:
                    return result["id"]
                # Service returned unexpected payload – fall through to SQLite
                self._graphiti_available = False
            except Exception:
                self._graphiti_available = False

        # SQLite fallback
        return self._sqlite_create_node(label, properties)

    def create_relationship(
        self,
        from_id: str,
        rel_type: str,
        to_id: str,
        properties: Dict[str, Any] | None = None,
    ) -> bool:
        """Create a directed relationship.  Returns True on success."""
        props = properties or {}

        if self._use_graphiti():
            try:
                result = self._http_post(
                    "/relationships",
                    {
                        "from_id": from_id,
                        "rel_type": rel_type,
                        "to_id": to_id,
                        "properties": props,
                    },
                )
                if result is not None:
                    return True
                self._graphiti_available = False
            except Exception:
                self._graphiti_available = False

        # SQLite fallback
        return self._sqlite_create_relationship(from_id, rel_type, to_id, props)

    # ------------------------------------------------------------------
    # Introspection helpers (useful for summaries / tests)
    # ------------------------------------------------------------------

    def count_nodes(self) -> int:
        row = self._sqlite_conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
        return row[0] if row else 0

    def count_relationships(self) -> int:
        row = self._sqlite_conn.execute("SELECT COUNT(*) FROM relationships").fetchone()
        return row[0] if row else 0

    def count_nodes_by_label(self) -> Dict[str, int]:
        rows = self._sqlite_conn.execute(
            "SELECT label, COUNT(*) FROM nodes GROUP BY label ORDER BY label"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def count_rels_by_type(self) -> Dict[str, int]:
        rows = self._sqlite_conn.execute(
            "SELECT rel_type, COUNT(*) FROM relationships GROUP BY rel_type ORDER BY rel_type"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def close(self) -> None:
        """Close the SQLite connection."""
        try:
            self._sqlite_conn.close()
        except Exception:
            pass
