# Agente 2 — API REST (FastAPI)

## Contexto
Eres el agente de API de un sistema de análisis de cobros.
Tu trabajo es crear una API REST en FastAPI que consulte el grafo en Graphiti/Neo4j
y exponga los datos a la capa de frontend y al agente MCP.
No tienes contexto de ninguna sesión previa. Todo lo que necesitas está en disco.

---

## Inputs (verificar existencia antes de ejecutar)

```
PLAN.md                          ← endpoints requeridos, schema del grafo, estructura de carpetas
ingesta/ingesta_completada.json  ← confirma que el grafo está cargado
.env                             ← GRAPHITI_URL, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, API_PORT
```

**Validación de inputs — DETENTE si alguno falla:**
1. `PLAN.md` existe
2. `ingesta/ingesta_completada.json` existe y tiene `"status": "ok"`
3. Variables de entorno requeridas están definidas
4. Graphiti responde en `$GRAPHITI_URL/health` (HTTP 200)

---

## Responsabilidad

Crear e implementar el módulo `api/` completo con FastAPI que exponga los 11 endpoints
definidos en `PLAN.md` sección **"2. Endpoints de la API REST"**.

---

## Endpoints a Implementar

Leer sección **"2. Endpoints de la API REST"** de `PLAN.md` para la lista completa.
Aquí se detallan los más complejos:

### `GET /analytics/promesas-incumplidas`
- Query param `?fecha=YYYY-MM-DD` (default: fecha actual)
- Retorna promesas donde `cumplida == false` Y `fecha_promesa < fecha_param`
- Response:
```json
[
  {
    "cliente_id": "cliente_023",
    "cliente_nombre": "Cliente 24",
    "promesa_id": "int_abc123_promesa",
    "monto_prometido": 1500,
    "fecha_promesa": "2025-06-15",
    "dias_vencida": 12,
    "ultimo_sentimiento": "cooperativo"
  }
]
```

### `GET /analytics/mejores-horarios`
- Agrupa interacciones de tipo llamada por `hora_del_dia` y `dia_semana`
- Calcula tasa de éxito = llamadas con resultado en `["promesa_pago","pago_inmediato"]` / total llamadas del slot
- Query param `?resultado=promesa_pago` para filtrar por resultado específico
- Response:
```json
[
  {
    "hora": 10,
    "dia_semana": 1,
    "dia_nombre": "Martes",
    "total_llamadas": 45,
    "tasa_exito": 0.42
  }
]
```

### `GET /analytics/dashboard`
Response:
```json
{
  "total_deuda_inicial": 269464,
  "total_recuperado": 48230,
  "tasa_recuperacion": 0.179,
  "promesas_cumplidas": 31,
  "promesas_incumplidas": 65,
  "tasa_cumplimiento_promesas": 0.323,
  "distribucion_tipos_deuda": {
    "hipoteca": 15, "tarjeta_credito": 12, "prestamo_personal": 13, "auto": 10
  },
  "actividad_por_dia": [
    {"fecha": "2025-05-17", "total": 8, "llamadas": 6, "pagos": 1}
  ]
}
```

### `GET /grafo/nodos` y `GET /grafo/relaciones`
- Usados por el frontend para el visualizador D3.js
- `/grafo/nodos`: query params `?tipos=Cliente,Agente` y `?limite=200`
- `/grafo/relaciones`: query params `?cliente_id=...` o `?tipo_rel=TIENE_INTERACCION`
- Formato de respuesta compatible con D3.js force-directed:
```json
{
  "nodos": [{"id": "cliente_000", "tipo": "Cliente", "label": "Cliente 1", "propiedades": {...}}],
  "enlaces": [{"source": "cliente_000", "target": "int_ddb0b226", "tipo": "TIENE_INTERACCION"}]
}
```

---

## Estructura de Archivos a Crear

```
api/
├── requirements.txt
├── main.py                    ← FastAPI app, monta routers, CORS habilitado
├── config.py                  ← carga .env con pydantic-settings
├── routers/
│   ├── __init__.py
│   ├── clientes.py            ← GET /clientes, /clientes/{id}, /clientes/{id}/timeline
│   ├── agentes.py             ← GET /agentes, /agentes/{id}/efectividad
│   ├── analytics.py           ← GET /analytics/promesas-incumplidas, /mejores-horarios, /dashboard
│   ├── grafo.py               ← GET /grafo/nodos, /grafo/relaciones
│   └── mcp_query.py           ← POST /mcp/query (stub para Agente 4)
├── services/
│   ├── __init__.py
│   ├── graphiti_service.py    ← toda la lógica de queries a Graphiti/Neo4j
│   └── mcp_service.py         ← stub vacío para Agente 4
└── schemas/
    ├── __init__.py
    ├── cliente.py
    ├── agente.py
    ├── analytics.py
    └── grafo.py
```

### `api/requirements.txt`:
```
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.0
pydantic-settings>=2.0
requests>=2.31
python-dotenv>=1.0
```

### `api/main.py` debe:
- Habilitar CORS para `*` (frontend en localhost)
- Montar todos los routers con prefijo `/`
- Exponer `/docs` (Swagger UI automático)
- Exponer `GET /health` → `{"status": "ok"}`

### `api/services/graphiti_service.py` debe:
- Conectarse a Graphiti vía `GRAPHITI_URL` (HTTP REST)
- O conectarse directamente a Neo4j vía bolt si Graphiti no expone las queries necesarias
- Centralizar toda la lógica de queries (no queries en los routers)
- Manejar errores de conexión con mensajes claros

---

## Criterio de Éxito

La API termina **correctamente** cuando:

1. `uvicorn api.main:app --port 8001` arranca sin errores
2. `GET http://localhost:8001/health` → `{"status": "ok"}`
3. `GET http://localhost:8001/docs` → Swagger UI carga en browser
4. Cada uno de los 11 endpoints responde HTTP 200 con datos reales del grafo
5. `GET http://localhost:8001/clientes/cliente_000/timeline` retorna al menos 1 interacción
6. `GET http://localhost:8001/analytics/dashboard` retorna `total_deuda_inicial > 0`
7. `GET http://localhost:8001/grafo/nodos?tipos=Cliente&limite=10` retorna exactamente 10 nodos tipo Cliente

Escribe el resultado en `api/api_verificada.json`:
```json
{
  "status": "ok",
  "endpoints_verificados": 11,
  "url_base": "http://localhost:8001"
}
```

---

## Cómo Ejecutar

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Notas de Implementación

- El router `mcp_query.py` debe existir con un stub que retorne `{"status": "not_implemented"}` — el Agente 4 lo completará
- No hardcodear URLs ni credenciales — todo desde `.env`
- Graphiti expone su propia API REST; si las queries de grafo no son suficientes, conectarse directamente a Neo4j con `neo4j` driver Python
- Para los endpoints de grafo (`/grafo/nodos`, `/grafo/relaciones`), limitar a máximo 500 nodos para no saturar el frontend
- CORS debe estar habilitado para `http://localhost:3000` y `http://localhost:5500`
