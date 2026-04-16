#!/usr/bin/env python3
"""
Utility script to check and manage Neo4j + Graphiti connection.

Usage:
    python scripts/check_neo4j.py status    # Check connection status
    python scripts/check_neo4j.py test     # Test queries
    python scripts/check_neo4j.py switch  # Switch to Neo4j mode
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


async def check_status():
    """Check Neo4j and Graphiti status."""
    print("=" * 50)
    print("CHECKING NEO4J + GRAPHITI STATUS")
    print("=" * 50)

    # Check Neo4j
    try:
        from neo4j import GraphDatabase

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password123")

        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            if record:
                print(f"✅ Neo4j: CONECTED ({uri})")
            driver.close()
    except Exception as e:
        print(f"❌ Neo4j: {e}")

    # Check Graphiti
    try:
        import httpx

        url = os.getenv("GRAPHITI_URL", "http://localhost:8000")
        response = httpx.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Graphiti: CONECTED ({url})")
            print(f"   Nodes: {data.get('num_nodes', 'N/A')}")
            print(f"   Relationships: {data.get('num_relationships', 'N/A')}")
        else:
            print(f"⚠️ Graphiti: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Graphiti: {e}")

    # Check SQLite fallback
    db_path = PROJECT_ROOT / "ingesta" / "local_graph.db"
    if db_path.exists():
        print(f"✅ SQLite fallback: EXISTS ({db_path})")
    else:
        print(f"⚠️ SQLite fallback: NOT FOUND")

    print("=" * 50)


async def test_queries():
    """Test Cypher queries."""
    print("=" * 50)
    print("TESTING CYPHER QUERIES")
    print("=" * 50)

    try:
        from neo4j import GraphDatabase

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password123")

        driver = GraphDatabase.driver(uri, auth=(user, password))

        with driver.session() as session:
            # Count nodes by type
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as type, count(n) as count
                ORDER BY count DESC
            """)
            print("\n📊 NODES BY TYPE:")
            for record in result:
                print(f"   {record['type']}: {record['count']}")

            # Count relationships
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            print("\n🔗 RELATIONSHIPS:")
            for record in result:
                print(f"   {record['type']}: {record['count']}")

        driver.close()
        print("=" * 50)

    except Exception as e:
        print(f"❌ Error: {e}")
        print("=" * 50)


async def test_graphiti_api():
    """Test Graphiti REST API."""
    print("=" * 50)
    print("TESTING GRAPHITI REST API")
    print("=" * 50)

    try:
        import httpx

        url = os.getenv("GRAPHITI_URL", "http://localhost:8000")

        # Test nodes endpoint
        response = httpx.get(f"{url}/api/v1/nodes", timeout=10)
        print(f"\nGET /api/v1/nodes: {response.status_code}")

        # Test search endpoint
        response = httpx.get(
            f"{url}/api/v1/search", params={"query": "cliente_001"}, timeout=10
        )
        print(f"GET /api/v1/search: {response.status_code}")

        print("=" * 50)

    except Exception as e:
        print(f"❌ Error: {e}")
        print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_neo4j.py [status|test|graphiti]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        asyncio.run(check_status())
    elif command == "test":
        asyncio.run(test_queries())
    elif command == "graphiti":
        asyncio.run(test_graphiti_api())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
