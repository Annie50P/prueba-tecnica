#!/usr/bin/env bash
# start.sh — levanta todo el sistema con un solo comando.
# Uso: bash start.sh
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✔${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
step() { echo -e "\n${GREEN}▶${NC} $1"; }

echo ""
echo "============================================================"
echo "   Analizador de Patrones de Llamadas — Setup completo"
echo "============================================================"

# ── 1. Prerequisitos ─────────────────────────────────────────────
step "Verificando prerequisitos..."

command -v docker >/dev/null 2>&1 || fail "Docker no encontrado. Instalar Docker Desktop."
docker info >/dev/null 2>&1      || fail "Docker no está corriendo. Abre Docker Desktop."
ok "Docker disponible"

# ── 2. Variables de entorno ──────────────────────────────────────
step "Configurando variables de entorno..."

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    warn ".env creado desde .env.example"
    warn "Edita .env y agrega al menos GROQ_API_KEY para el chat IA."
    warn "Continuar de todas formas con valores por defecto? (Ctrl+C para cancelar)"
    sleep 3
  else
    fail ".env.example no encontrado"
  fi
else
  ok ".env existe"
fi

# Leer NEO4J_PASSWORD del .env para usarlo en healthcheck
NEO4J_PASSWORD=$(grep -E '^NEO4J_PASSWORD=' .env | cut -d= -f2 | tr -d '"' | tr -d "'")
NEO4J_USER=$(grep -E '^NEO4J_USER=' .env 2>/dev/null | cut -d= -f2 | tr -d '"' | tr -d "'")
NEO4J_USER=${NEO4J_USER:-neo4j}

# ── 3. Infraestructura base ──────────────────────────────────────
step "Levantando Neo4j, Graphiti y MCP server..."
docker compose up -d neo4j graphiti graphiti-mcp
ok "Servicios iniciados"

# ── 4. Esperar Neo4j ─────────────────────────────────────────────
step "Esperando que Neo4j esté listo (puede tardar ~90 segundos)..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' neo4j 2>/dev/null || echo "starting")
  if [ "$STATUS" = "healthy" ]; then
    ok "Neo4j listo"
    break
  fi
  printf "  [%ds] Neo4j: %s...\r" "$ELAPSED" "$STATUS"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done
[ "$STATUS" != "healthy" ] && fail "Neo4j no arrancó en ${MAX_WAIT}s. Revisa: docker compose logs neo4j"

# ── 5. Esperar Graphiti ──────────────────────────────────────────
step "Esperando Graphiti..."
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  if curl -sf http://localhost:8000/healthcheck >/dev/null 2>&1; then
    ok "Graphiti listo"
    break
  fi
  printf "  [%ds] Graphiti iniciando...\r" "$ELAPSED"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

# ── 6. Ingesta de datos ──────────────────────────────────────────
step "Ingiriendo datos en Neo4j (primera vez tarda ~17 minutos)..."

# Verificar si ya hay datos
NODE_COUNT=$(docker exec neo4j cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
  "MATCH (n) RETURN count(n) AS c" 2>/dev/null | grep -E '^[0-9]+$' || echo "0")

if [ "$NODE_COUNT" -gt "100" ] 2>/dev/null; then
  ok "Datos ya presentes en Neo4j ($NODE_COUNT nodos) — saltando ingesta"
else
  docker compose run --rm ingesta
  ok "Ingesta completada"
fi

# ── 7. API y Frontend ────────────────────────────────────────────
step "Levantando API y Frontend..."
docker compose up -d api frontend
ok "API y Frontend iniciados"

# ── 8. Esperar API ───────────────────────────────────────────────
step "Esperando que la API esté lista..."
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  if curl -sf http://localhost:8001/health >/dev/null 2>&1; then
    ok "API lista"
    break
  fi
  printf "  [%ds] API iniciando...\r" "$ELAPSED"
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

# ── 9. Verificación rápida ───────────────────────────────────────
step "Verificando endpoints..."

check_endpoint() {
  local url=$1 label=$2
  if curl -sf "$url" >/dev/null 2>&1; then
    ok "$label"
  else
    warn "$label (no responde — puede tardar un momento más)"
  fi
}

check_endpoint "http://localhost:8001/health"              "GET /health"
check_endpoint "http://localhost:8001/analytics/dashboard" "GET /analytics/dashboard"
check_endpoint "http://localhost:8001/analytics/prediccion" "GET /analytics/prediccion (ML)"
check_endpoint "http://localhost:8001/analytics/anomalias"  "GET /analytics/anomalias (ML)"
check_endpoint "http://localhost:3000"                      "Frontend"

# ── 10. Resumen ──────────────────────────────────────────────────
echo ""
echo "============================================================"
echo -e "   ${GREEN}Sistema listo${NC}"
echo "============================================================"
echo ""
echo "  Frontend        →  http://localhost:3000"
echo "  API Swagger     →  http://localhost:8001/docs"
echo "  Neo4j Browser   →  http://localhost:7474"
echo ""
echo "  ML endpoints:"
echo "    Predicción    →  http://localhost:8001/analytics/prediccion"
echo "    Anomalías     →  http://localhost:8001/analytics/anomalias"
echo "    Estrategias   →  http://localhost:8001/analytics/estrategias"
echo "    Dashboard     →  http://localhost:8001/analytics/dashboard"
echo ""
echo "  Para detener:   docker compose down"
echo "============================================================"
