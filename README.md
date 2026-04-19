# Analizador de Patrones de Llamadas

Sistema de análisis de interacciones con clientes deudores modelado como grafo de conocimiento temporal (Graphiti + Neo4j). Incluye API REST, dashboard interactivo, pipeline ML y consultas en lenguaje natural.

---

## Estado actual del sistema

| Componente | Estado | Notas |
|---|---|---|
| Ingesta de nodos y relaciones (Neo4j) | ✅ Funcional | 1354 nodos, 17266 relaciones |
| API REST (FastAPI) | ✅ Funcional | 16 endpoints |
| Frontend (React + D3.js) | ✅ Funcional | Dashboard, grafo, timelines |
| Pipeline ML (predicción, anomalías, segmentación) | ✅ Funcional | Entrena on-demand |
| Chat MCP en lenguaje natural | ✅ Funcional | Requiere al menos una LLM key |
| Episodios semánticos (Graphiti LLM) | ⚠️ Opcional | Requiere Groq + Gemini keys activas |
| Búsqueda semántica (`/analytics/busqueda-semantica`) | ⚠️ Depende de episodios | Funciona solo si hay episodios ingeridos |

> **Nota**: el sistema funciona completamente sin episodios semánticos. La búsqueda semántica es una capa adicional sobre el grafo estructurado que ya contiene toda la información de negocio.

---

## Descripción de la solución

El sistema ingesta datos históricos de interacciones de cobranza (50 clientes, 502 interacciones, 10 agentes) y los modela en un **grafo de conocimiento temporal** con 7 tipos de nodos y 9 tipos de relaciones dirigidas.

Sobre ese grafo se construyen:

- **API REST** (FastAPI) con endpoints de negocio, métricas derivadas y ML
- **Frontend SPA** (React + Vite + D3.js + Chart.js) con dashboard, explorador de grafo interactivo y chat IA
- **Pipeline ML** (predicción de riesgo, detección de anomalías, segmentación de clientes)
- **Chat en lenguaje natural** vía protocolo MCP con múltiples proveedores LLM
- **Búsqueda semántica** sobre hechos extraídos por LLM de las interacciones (requiere configuración de Groq + Gemini)

### ¿Por qué un grafo de conocimiento en lugar de una base de datos relacional?

En cobranza, la información más valiosa está en las **relaciones entre eventos**: qué agente hizo qué llamada, qué promesa generó qué pago, qué cliente incumplió en qué secuencia. En un modelo relacional esto requiere JOINs de 4-6 tablas para cada consulta de negocio. En el grafo:

- La cadena temporal de interacciones es una arista `SIGUIENTE` — la consulta es un `MATCH (a)-[:SIGUIENTE*]->(b)` sin JOINs
- Saber si un pago cumple una promesa es atravesar la arista `CUMPLE_PROMESA` directamente
- La evolución de deuda de un cliente es un camino `ESTADO_DEUDA_EN → SIGUIENTE_ESTADO → ...`
- Agregar un nuevo tipo de evento (llamada por WhatsApp, SMS, email automatizado) no altera el esquema — se añade un nuevo nodo sin migraciones

Además, Graphiti agrega una capa de **memoria temporal**: los hechos extraídos por LLM tienen `valid_at`/`invalid_at`, lo que permite consultas del tipo *"¿qué clientes tenían promesas activas en enero?"* de forma nativa.

---

## Esquema del modelo de grafo

```
                    ┌─────────┐
                    │ Cliente │
                    └────┬────┘
                         │ TIENE_INTERACCION
                         ▼
 ┌────────┐   CONDUJO   ┌──────────────┐   GENERO_PROMESA  ┌─────────────┐
 │ Agente │────────────►│ Interaccion  │──────────────────►│ PromesaPago │
 └────────┘             └──────┬───────┘                   └──────┬──────┘
                               │                                  │
                    ┌──────────┴──────────┐                       │ CUMPLE_PROMESA
                    │                     │                        │
            GENERO_PAGO          GENERO_PLAN                      ▼
                    │                     │                   ┌───────┐
                    ▼                     ▼                   │  Pago │◄──┐
               ┌───────┐          ┌──────────┐               └───────┘   │
               │  Pago │          │ PlanPago │──GENERA_CUOTA──►PromesaPago│
               └───────┘          └──────────┘                            │
                                                                          │
                    ┌─────────┐                                           │
                    │ Cliente │──ESTADO_DEUDA_EN──►┌─────────────┐       │
                    └─────────┘                    │ EstadoDeuda │◄──────┘
                                                   └──────┬──────┘
                                                          │ SIGUIENTE_ESTADO
                                                          ▼
                                                   ┌─────────────┐
                                                   │ EstadoDeuda │ ...
                                                   └─────────────┘
```

### Nodos

| Label | Descripción |
|---|---|
| `Cliente` | Deudor con métricas derivadas (tasa cumplimiento, monto pendiente) |
| `Agente` | Agente de cobranza con métricas de efectividad |
| `Interaccion` | Llamada, email o pago recibido — evento central del grafo |
| `PromesaPago` | Compromiso de pago generado en una interacción |
| `Pago` | Pago recibido, puede cumplir una promesa |
| `PlanPago` | Plan de renegociación con N cuotas |
| `EstadoDeuda` | Snapshot del saldo en un momento dado — cadena temporal |

### Relaciones

| Tipo | Dirección | Semántica |
|---|---|---|
| `TIENE_INTERACCION` | Cliente → Interaccion | El cliente participó en este evento |
| `CONDUJO` | Agente → Interaccion | El agente gestionó este evento |
| `GENERO_PROMESA` | Interaccion → PromesaPago | La interacción generó esta promesa |
| `GENERO_PAGO` | Interaccion → Pago | La interacción registró este pago |
| `GENERO_PLAN` | Interaccion → PlanPago | La interacción originó este plan |
| `GENERA_CUOTA` | PlanPago → PromesaPago | El plan genera N promesas (una por cuota) |
| `CUMPLE_PROMESA` | Pago → PromesaPago | El pago satisface la promesa |
| `SIGUIENTE` | Interaccion → Interaccion | Cadena cronológica de interacciones del cliente |
| `ESTADO_DEUDA_EN` | Cliente → EstadoDeuda | El cliente tiene este estado de deuda |
| `SIGUIENTE_ESTADO` | EstadoDeuda → EstadoDeuda | Cadena temporal de evolución de deuda |

---

## Instalación y ejecución

### Prerrequisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- Al menos una API key gratuita de LLM (ver tabla abajo)

### Variables de entorno requeridas

Copia `.env.example` a `.env` y completa:

```bash
cp .env.example .env
```

| Variable | Obligatoria | Dónde obtener |
|---|---|---|
| `NEO4J_PASSWORD` | Sí | Elige una contraseña (mín. 8 chars) |
| `GROQ_API_KEY` | Para chat IA | [console.groq.com](https://console.groq.com) — gratis |
| `GEMINI_API_KEY` | Para embeddings | [aistudio.google.com](https://aistudio.google.com) — gratis |
| `OPENROUTER_API_KEY` | Alternativa | [openrouter.ai](https://openrouter.ai) — gratis |
| `ANTHROPIC_API_KEY` | Alternativa | [console.anthropic.com](https://console.anthropic.com) |

> El sistema funciona con **solo Groq key** para el chat. Los episodios semánticos requieren además Gemini.

---

## Cómo ejecutar el proyecto

### Opción A — Script automático (recomendado)

Un solo comando levanta todo: Neo4j, Graphiti, ingesta, API y frontend.

```bash
bash start.sh
```

El script:
1. Verifica que Docker esté corriendo
2. Crea `.env` desde `.env.example` si no existe
3. Levanta todos los servicios en orden correcto
4. Espera a que cada servicio esté healthy antes de continuar
5. Corre la ingesta (la omite si los datos ya están cargados)
6. Verifica que todos los endpoints respondan
7. Imprime las URLs finales

Al terminar verás:

```
============================================================
   Sistema listo
============================================================

  Frontend        →  http://localhost:3000
  API Swagger     →  http://localhost:8001/docs
  Neo4j Browser   →  http://localhost:7474

  ML endpoints:
    Predicción    →  http://localhost:8001/analytics/prediccion
    Anomalías     →  http://localhost:8001/analytics/anomalias
    Estrategias   →  http://localhost:8001/analytics/estrategias
    Dashboard     →  http://localhost:8001/analytics/dashboard

  Para detener:   docker compose down
============================================================
```

> La primera ejecución tarda ~20 minutos (ingesta de datos en Neo4j). Las siguientes son inmediatas — el script detecta que los datos ya existen y omite la ingesta.

---

### Opción B — Manual paso a paso

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar .env y agregar al menos GROQ_API_KEY

# 2. Levantar infraestructura
docker compose up -d neo4j graphiti graphiti-mcp
# Esperar ~90 segundos

# 3. Levantar API y frontend
docker compose up -d api frontend

# 4. Ingestar datos (una sola vez, ~17 minutos)
docker compose run --rm ingesta
```

| Servicio | URL |
|---|---|
| **Frontend** | http://localhost:3000 |
| **API Swagger** | http://localhost:8001/docs |
| **Neo4j Browser** | http://localhost:7474 |

### (Opcional) Episodios semánticos

Activa la búsqueda semántica en lenguaje natural. Requiere `GROQ_API_KEY` + `GEMINI_API_KEY` en `.env`.

```bash
docker compose build ingesta
docker compose run --rm ingesta python ingest_episodes.py
```

Tarda ~20 minutos (throttling para respetar rate limits gratuitos).

---

### Sin Docker (modo desarrollo, SQLite)

```bash
cd ingesta && pip install -r requirements.txt
cd ../api  && pip install -r requirements.txt

cd ../ingesta && python ingest.py        # crea local_graph.db
cd ..
GRAPH_BACKEND=sqlite python -m uvicorn api.main:app --port 8001 --reload

cd frontend && bun install && bun run dev  # http://localhost:5173
```

> En modo SQLite el chat MCP y la búsqueda semántica no están disponibles.

---

## Endpoints API

**Base URL**: `http://localhost:8001`  
**Documentación interactiva**: `http://localhost:8001/docs`

### Clientes

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/clientes` | Lista clientes con métricas derivadas. Params: `limite`, `offset` |
| GET | `/clientes/{id}` | Detalle completo: métricas, promesas, pagos, plan |
| GET | `/clientes/{id}/timeline` | Historial cronológico de interacciones |
| GET | `/clientes/{id}/evolucion-deuda` | Evolución del saldo en el tiempo |

### Agentes

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/agentes` | Lista agentes con métricas de efectividad |
| GET | `/agentes/{id}/efectividad` | Desempeño detallado del agente |

### Analytics

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/analytics/dashboard` | KPIs globales (tasa cumplimiento, monto pendiente, etc.) |
| GET | `/analytics/promesas-incumplidas` | Promesas vencidas. Param: `fecha` (YYYY-MM-DD) |
| GET | `/analytics/mejores-horarios` | Análisis de horarios por resultado. Param: `resultado` |
| GET | `/analytics/prediccion` | Score de riesgo por cliente (ML) |
| GET | `/analytics/anomalias` | Clientes con comportamiento anómalo (ML) |
| GET | `/analytics/estrategias` | Segmentos de clientes y recomendaciones (ML) |
| GET | `/analytics/busqueda-semantica` | Búsqueda semántica en el grafo. Params: `q`, `n`, `fecha` |

### Grafo

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/grafo/nodos` | Nodos para visualización D3.js. Param: `tipo` |
| GET | `/grafo/relaciones` | Relaciones para visualización D3.js. Params: `cliente_id`, `tipo` |

### Chat / MCP

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/mcp/query` | Consulta en lenguaje natural sobre el grafo |

### Sistema

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio y backends disponibles |
| GET | `/` | Metadata de la API |

---

## Decisiones técnicas

### Backend de datos intercambiable

El sistema tiene tres backends detrás de una interfaz `GraphRepository`:

- **`graphiti`** — usa Neo4j vía graphiti-core SDK. Modo de producción. Soporta búsqueda semántica y temporalidad.
- **`neo4j`** — usa Neo4j directo con Cypher. Más control, sin capa semántica.
- **`sqlite`** — fallback local para desarrollo sin infraestructura. Automático si Neo4j no está disponible.

Configurable con `GRAPH_BACKEND=graphiti|neo4j|sqlite` en `.env`.

### Promesa cumplida: modo dinámico vs snapshot

`cumplida` en `PromesaPago` puede evaluarse de dos formas:

- **`snapshot`**: lee el bool guardado en el nodo al momento de la ingesta
- **`dynamic`** (por defecto): traversa la arista `CUMPLE_PROMESA` en el grafo — detecta pagos registrados después de la ingesta

El modo dinámico evita inconsistencias cuando se reciben pagos tardíos sin re-ingestar.

### Pipeline ML anti-leakage

El `StandardScaler` vive **dentro** del `Pipeline` de scikit-learn. Se ajusta por fold en CV estratificado — nunca ve datos de validación. Todos los modelos (GradientBoosting, XGBoost, LightGBM) se evalúan con ROC-AUC y el mejor se persiste vía joblib. Si no hay modelo entrenado, la API entrena on-demand bajo lock singleflight.

### Proveedores LLM intercambiables

El chat MCP soporta 5 proveedores con selección automática:

```
OpenRouter → Groq → OpenAI → Gemini → Anthropic
```

El primer proveedor con API key válida en el `.env` se usa automáticamente. Configurable con `LLM_PROVIDER=auto|groq|openai|gemini|anthropic|openrouter`.

---

## Escalabilidad a 1 millón de clientes

| Capa | Estrategia |
|---|---|
| **Neo4j** | Índices compuestos en `(cliente_id, timestamp)`, `(agente_id)`, `(tipo, resultado)`. Cluster causal para HA y sharding. |
| **Ingesta** | Workers en paralelo con Celery + Redis. Batch de 500 nodos por transacción Neo4j. |
| **API** | Paginación en todos los endpoints. Cache de KPIs en Redis (TTL 5 min). |
| **ML** | Reentrenamiento incremental con datos de las últimas N semanas. Inferencia en batch asíncrono. |
| **Graphiti** | Particionamiento por `group_id` — cada empresa/cartera es un grupo aislado. |

Con Neo4j Enterprise y Causal Clustering, el grafo escala horizontalmente. La arquitectura actual ya usa MERGE en lugar de INSERT, lo que garantiza idempotencia en re-ingestas.

---

## Otras fuentes de datos útiles

| Fuente | Valor aportado |
|---|---|
| **Score crediticio externo** (Equifax, bureaus locales) | Enriquecer `Cliente` con historial crediticio previo al préstamo — mejor predicción de riesgo |
| **Canales digitales** (WhatsApp, portal web, SMS) | Capturar interacciones autogestionadas que hoy no están en el grafo |
| **Calendarios y feriados por país** | Optimizar horarios de llamada evitando días no laborables |
| **Datos macroeconómicos** (inflación, desempleo) | Correlacionar picos de incumplimiento con indicadores económicos |
| **Grabaciones de llamadas** (transcripciones ASR) | Extraer sentimiento y compromisos verbales directamente del audio |
| **Historial de deudas anteriores** | Detectar patrones de reincidencia en el mismo cliente |

---

## Pipeline ML

```
features.py ─┐
             ├──► train.py ──► model_registry.py (joblib + registry.json)
train_offline.py              │
                              ▼
                    predictor.py (load_latest en startup, lock singleflight)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        inference.py    anomalies.py   segmentation.py
```

- **Modelos**: GradientBoosting vs XGBoost vs LightGBM — selección por ROC-AUC
- **Ground truth**: label=1 si tiene pagos reales o promesa cumplida; label=0 si sin actividad >30 días
- **Anomalías**: IsolationForest + LOF ensemble con contamination adaptivo (IQR de Tukey)
- **Segmentación**: KMeans con k óptimo por Silhouette score

---

## Tests

```bash
# Todos los tests
python -m pytest api/tests/ -v

# Solo ML
python -m pytest api/tests/test_ml/ -v

# Solo integración pipeline
python -m pytest api/tests/test_pipeline.py -v
```

**Baseline esperado**: 69 fallan (requieren Neo4j activo), 43 pasan (unit tests puros).  
Con Docker levantado: todos los tests de API pasan.

---

## Mejoras futuras

- **Autenticación JWT** con roles (agente / supervisor / admin)
- **Alertas automáticas** para promesas próximas a vencer (webhook / email)
- **Reentrenamiento automático** del modelo ML (job nocturno con Celery beat)
- **Tests E2E** del frontend con Playwright
- **Exportación CSV/Excel** del dashboard y listas de clientes
- **Ingesta en tiempo real** vía webhook — registrar pagos y llamadas en el momento
- **Métricas de Graphiti** en el dashboard — visualizar entidades y hechos extraídos por LLM
- **Multi-tenancy** — un `group_id` por empresa para aislar grafos de diferentes carteras
