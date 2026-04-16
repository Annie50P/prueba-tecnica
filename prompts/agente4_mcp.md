# Agente 4 — Integración MCP + LLM

## Contexto
Eres el agente de integración MCP de un sistema de análisis de cobros.
Tu trabajo es completar el endpoint `POST /mcp/query` en la API existente,
conectando el servidor MCP de Graphiti con un LLM (Claude via Anthropic API)
para responder consultas en lenguaje natural sobre el grafo de conocimiento.
No tienes contexto de ninguna sesión previa. Todo lo que necesitas está en disco.

---

## Inputs (verificar existencia antes de ejecutar)

```
PLAN.md                    ← arquitectura MCP, endpoint /mcp/query
api/api_verificada.json    ← confirma que la API base está funcionando
api/routers/mcp_query.py   ← stub vacío creado por Agente 2 (a completar)
api/services/mcp_service.py ← stub vacío creado por Agente 2 (a completar)
.env                       ← ANTHROPIC_API_KEY, GRAPHITI_URL
```

**Validación de inputs — DETENTE si alguno falla:**
1. `PLAN.md` existe
2. `api/api_verificada.json` existe y tiene `"status": "ok"`
3. `api/routers/mcp_query.py` existe
4. `api/services/mcp_service.py` existe
5. Variable de entorno `ANTHROPIC_API_KEY` está definida y empieza con `sk-ant-`
6. La API responde en `GET {url_base}/health` → `{"status": "ok"}`
7. Graphiti responde en `$GRAPHITI_URL/health` → HTTP 200

---

## Responsabilidad

Completar la integración MCP + LLM implementando:

1. **Configuración del servidor MCP de Graphiti** (proceso separado)
2. **Cliente MCP** que se conecta al servidor MCP de Graphiti desde Python
3. **Servicio LLM** usando Anthropic Claude con tool use para las tools MCP
4. **Endpoint `POST /mcp/query`** que orquesta todo el flujo
5. **docker-compose.yml** actualizado para incluir el servicio MCP

---

## Arquitectura del Flujo MCP

```
Usuario → POST /mcp/query {"query": "¿Qué agente tiene más promesas cumplidas?"}
            ↓
    api/services/mcp_service.py
            ↓
    Claude API (Anthropic) con tools del servidor MCP de Graphiti
            ↓  (Claude llama tools MCP automáticamente)
    Servidor MCP de Graphiti → Neo4j
            ↓
    Claude sintetiza respuesta
            ↓
    Response: {"respuesta": "El agente_003...", "datos": [...], "queries_ejecutadas": [...]}
```

---

## Implementación del Servidor MCP de Graphiti

El servidor MCP de Graphiti se levanta como proceso Docker separado.

Añadir al `docker-compose.yml` existente:

```yaml
  graphiti-mcp:
    image: getzep/graphiti-mcp:latest
    depends_on:
      - graphiti
    ports:
      - "8002:8002"
    environment:
      - GRAPHITI_URL=http://graphiti:8000
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=${NEO4J_USER}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
```

Verificar que el servidor MCP está corriendo:
```bash
curl http://localhost:8002/health
```

---

## Archivos a Crear/Modificar

### `api/services/mcp_service.py` (completar el stub)

Implementar la clase `MCPService`:

```python
class MCPService:
    def __init__(self):
        self.mcp_url = settings.MCP_URL  # http://localhost:8002
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
    
    async def query(self, user_query: str) -> dict:
        # 1. Obtener las tools disponibles del servidor MCP de Graphiti
        # 2. Enviar query a Claude con las tools
        # 3. Ejecutar las tools que Claude solicite (llamar al servidor MCP)
        # 4. Retornar la respuesta sintetizada
        ...
```

**Flujo de tool use con Claude:**
1. Obtener tools del servidor MCP: `GET http://localhost:8002/tools`
2. Primera llamada a Claude: enviar `user_query` + lista de tools MCP
3. Si Claude responde con `tool_use`, ejecutar la tool en el servidor MCP: `POST http://localhost:8002/tools/{tool_name}` con los argumentos
4. Enviar el resultado de la tool de vuelta a Claude como `tool_result`
5. Repetir hasta que Claude responda con `end_turn` (máximo 5 iteraciones)
6. Retornar la respuesta final de Claude

**Prompt del sistema para Claude:**
```
Eres un asistente de análisis de datos de una empresa de gestión de cobros.
Tienes acceso a un grafo de conocimiento con datos de 50 clientes, 502 interacciones,
10 agentes y 90 días de actividad.
Responde en español de forma concisa y con datos concretos.
Cuando sea relevante, incluye números específicos y porcentajes.
```

### `api/routers/mcp_query.py` (completar el stub)

```python
@router.post("/mcp/query")
async def mcp_query(request: MCPQueryRequest) -> MCPQueryResponse:
    # Delegar a MCPService
    # Manejar errores: MCP no disponible → 503, LLM error → 500
    ...
```

Schemas:
```python
class MCPQueryRequest(BaseModel):
    query: str  # max_length=500

class MCPQueryResponse(BaseModel):
    respuesta: str
    datos: list = []
    queries_ejecutadas: list[str] = []
    tokens_usados: int = 0
```

### `api/config.py` (añadir)

```python
MCP_URL: str = "http://localhost:8002"
ANTHROPIC_API_KEY: str
```

### `api/requirements.txt` (añadir)

```
anthropic>=0.25
```

---

## Ejemplos de Consultas que Deben Funcionar

El endpoint debe responder correctamente a estas consultas de prueba:

1. `"¿Cuál agente tiene la mayor tasa de promesas cumplidas?"`
2. `"¿Qué clientes tienen promesas vencidas esta semana?"`
3. `"¿Cuál es el mejor horario para llamar a clientes con deuda tipo hipoteca?"`
4. `"Muéstrame el historial del cliente_010"`
5. `"¿Cuánto dinero total se ha recuperado hasta la fecha?"`

---

## Criterio de Éxito

La integración MCP termina **correctamente** cuando:

1. `docker compose up graphiti-mcp` levanta sin errores
2. `GET http://localhost:8002/health` → HTTP 200
3. `POST http://localhost:8001/mcp/query` con `{"query": "¿Cuántos clientes hay?"}` → HTTP 200 con `respuesta` que menciona "50"
4. Al menos 3 de los 5 ejemplos de consultas retornan respuestas coherentes con los datos
5. Si `ANTHROPIC_API_KEY` no está configurada, el endpoint retorna `{"error": "mcp_not_configured", "message": "ANTHROPIC_API_KEY no está configurada"}` con HTTP 503 (no crash)

Escribe `api/mcp_verificado.json`:
```json
{
  "status": "ok",
  "mcp_url": "http://localhost:8002",
  "llm_model": "claude-sonnet-4-6",
  "consultas_probadas": 5,
  "consultas_exitosas": 3
}
```

---

## Cómo Ejecutar

```bash
# 1. Levantar servidor MCP
docker compose up graphiti-mcp -d

# 2. Verificar MCP
curl http://localhost:8002/health

# 3. Reiniciar API para cargar los cambios
cd api
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 4. Probar el endpoint
curl -X POST http://localhost:8001/mcp/query \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuántos clientes tienen promesas vencidas?"}'
```

---

## Notas de Implementación

- Usar `anthropic` SDK oficial (`pip install anthropic`) — no llamadas HTTP directas
- El modelo a usar es `claude-sonnet-4-6` (disponible, costo razonable)
- Implementar prompt caching para el system prompt (usar `cache_control: {"type": "ephemeral"}`) — reduce costos en consultas repetidas
- El loop de tool use debe tener un máximo de **5 iteraciones** para evitar loops infinitos
- Si el servidor MCP no está disponible, el endpoint debe degradarse gracefully (no 500)
- Loggear cada tool call y su resultado para debugging: `[mcp] tool=search_nodes args={...} → {resultado}`
- El campo `queries_ejecutadas` en la response debe listar las tools MCP que Claude ejecutó
- No exponer la `ANTHROPIC_API_KEY` en ningún log ni response
