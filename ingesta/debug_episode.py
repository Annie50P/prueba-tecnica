#!/usr/bin/env python3
"""Debug: muestra el error exacto de add_episode."""
import asyncio, os, sys, logging

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from dotenv import load_dotenv
    for c in [os.path.join(_HERE, ".env"), os.path.join(os.path.dirname(_HERE), ".env")]:
        if os.path.exists(c):
            load_dotenv(c)
            break
except ImportError:
    pass

logging.basicConfig(level=logging.DEBUG)

async def main():
    print("OPENAI_API_KEY set:", bool(os.environ.get("OPENAI_API_KEY")))
    print("OPENAI_API_KEY prefix:", os.environ.get("OPENAI_API_KEY", "")[:12])

    try:
        from graphiti_core import Graphiti
        from graphiti_core.nodes import EpisodeType
        from datetime import datetime, timezone

        g = Graphiti(
            uri=os.environ.get("NEO4J_URI", "bolt://neo4j:7687"),
            user=os.environ.get("NEO4J_USER", "neo4j"),
            password=os.environ.get("NEO4J_PASSWORD", "password123"),
        )
        await g.driver.verify_connectivity()
        print("Neo4j OK")

        await g.add_episode(
            name="debug_test",
            episode_body="El 2024-01-01 el agente agente_01 llamó al cliente Ana García. Prometió pagar 500 dolares.",
            source=EpisodeType.text,
            source_description="debug",
            reference_time=datetime.now(tz=timezone.utc),
            group_id=os.environ.get("GRAPHITI_GROUP_ID", "prueba-tecnica"),
        )
        print("Episode OK")
        await g.close()
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")

asyncio.run(main())
