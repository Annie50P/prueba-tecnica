#!/bin/bash
# Script de migración completa a Neo4j + Graphiti
# Uso: ./scripts/migrate_to_neo4j.sh

set -e

echo "=========================================="
echo "MIGRACIÓN A NEO4J + GRAPHITI"
echo "=========================================="

# 1. Verificar Docker
echo ""
echo "[1/7] Verificando Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker no está funcionando"
    exit 1
fi
echo "✅ Docker funcionando"

# 2. Limpiar containers existentes (force recreate)
echo ""
echo "[2/7] Limpiando containers existentes..."
docker compose down 2>/dev/null || true
docker compose rm -f 2>/dev/null || true
echo "✅ Containers limpiados"

# 3. Forzar recreation con images nuevas
echo ""
echo "[3/7] Forzando recreate con images nuevas..."
docker compose build --no-cache

# 4. Levantar servicios
echo ""
echo "[4/7] Levantando Neo4j y Graphiti..."
docker compose up -d neo4j graphiti

# 5. Esperar a que Neo4j esté listo
echo ""
echo "[5/7] Esperando a Neo4j..."
for i in {1..30}; do
    if docker exec neo4j cypher-shell -u neo4j -p password123 "RETURN 1" > /dev/null 2>&1; then
        echo "✅ Neo4j listo"
        break
    fi
    echo "   Esperando... ($i/30)"
    sleep 2
done

# 6. Esperar a Graphiti
echo ""
echo "[6/7] Esperando a Graphiti..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Graphiti listo"
        break
    fi
    echo "   Esperando... ($i/30)"
    sleep 2
done

# 7. Ejecutar ingesta
echo ""
echo "[7/7] Ejecutando ingesta a Neo4j..."
cd ingesta && python ingest.py

echo ""
echo "=========================================="
echo "MIGRACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Para verificar:"
echo "  - Neo4j Browser: http://localhost:7474"
echo "  - Graphiti: http://localhost:8000"
echo "  - API: http://localhost:8001"
echo ""