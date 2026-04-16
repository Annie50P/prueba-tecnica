# Analizador de Patrones de Llamadas

Sistema de análisis y visualización de patrones de interacción con clientes deudores, basado en grafo de conocimiento (Graphiti + Neo4j).

---

## Descripción

El sistema ingesta datos históricos de 50 clientes, 502 interacciones y 10 agentes, los modela como un grafo de conocimiento, y expone:

- **API REST** (FastAPI) con 11+ endpoints para consultas de negocio
- **Frontend SPA** (React + Vite + D3.js + Chart.js) con dashboard, vista de cliente y explorador de grafo
- **Consultas en lenguaje natural** vía MCP + Claude (Anthropic)
- **Pipeline ML offline** (predicción, anomalías, segmentación) con modelo persistido via `joblib`

---

## Instalación y ejecución (modo local, sin Docker)

### Requisitos
- Python 3.11+
- Node 20+ con `bun` (o `npm`) para el frontend
- No se requiere Docker ni Neo4j para el modo local (usa SQLite como fallback)

### 1. Instalar dependencias

```bash
# Ingesta
cd ingesta
pip install -r requirements.txt

# API
cd ../api
pip install -r requirements.txt
```

### 2. Ejecutar ingesta

```bash
cd ingesta
python ingest.py
```

Esto crea `ingesta/local_graph.db` con 766 nodos y 1748 relaciones.

### 3. (Opcional) Entrenar el modelo ML offline

```bash
cd ..   # raíz del proyecto
python -m api.ml.train_offline
```

Esto persiste el artifact (`model + scaler`) en `api/models/` y registra metadata
en `api/models/registry.json`. Si no se ejecuta, la API entrena on-demand al
primer request (bajo lock singleflight).

### 4. Iniciar la API

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

API disponible en: http://localhost:8001
Swagger UI: http://localhost:8001/docs

### 5. Iniciar el frontend (React + Vite)

```bash
cd frontend
bun install           # o: npm ci
bun run dev           # o: npm run dev
```

Frontend disponible en: http://localhost:5173 (Vite dev server)

En producción el frontend se sirve como estático vía nginx (ver
`frontend/Dockerfile` + `frontend/nginx.conf`), expuesto en puerto 3000.

---

## Ejecución con Docker Compose

### Requisitos
- Docker Desktop instalado
- Clonar el archivo de variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales (especialmente ANTHROPIC_API_KEY)

docker compose up --build
```

Servicios:
| Servicio | Puerto | URL |
|---|---|---|
| Frontend | 3000 | http://localhost:3000 |
| API REST | 8001 | http://localhost:8001/docs |
| Graphiti | 8000 | http://localhost:8000 |
| Neo4j Browser | 7474 | http://localhost:7474 |
| MCP Server | 8002 | http://localhost:8002 |

---

## Endpoints API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/clientes` | Lista todos los clientes con métricas |
| GET | `/clientes/{id}` | Detalle completo de un cliente |
| GET | `/clientes/{id}/timeline` | Historial cronológico del cliente |
| GET | `/agentes` | Lista agentes con métricas |
| GET | `/agentes/{id}/efectividad` | Desempeño del agente |
| GET | `/analytics/promesas-incumplidas` | Promesas vencidas sin pago |
| GET | `/analytics/mejores-horarios` | Horarios más efectivos |
| GET | `/analytics/dashboard` | KPIs globales |
| GET | `/grafo/nodos` | Nodos para visualización D3.js |
| GET | `/grafo/relaciones` | Relaciones para visualización D3.js |
| POST | `/mcp/query` | Consulta en lenguaje natural (requiere ANTHROPIC_API_KEY) |

---

## Modelo de Grafo

### Nodos
| Label | Cantidad | Descripción |
|---|---|---|
| Cliente | 50 | Deudores con métricas derivadas |
| Agente | 10 | Agentes de cobro |
| Interaccion | 502 | Llamadas, emails, SMS, pagos |
| PromesaPago | 96 | Compromisos de pago |
| Pago | 53 | Pagos recibidos |
| PlanPago | 55 | Planes de renegociación |

### Relaciones
| Tipo | Desde → Hacia | Cardinalidad |
|---|---|---|
| TIENE_INTERACCION | Cliente → Interaccion | 1:N |
| CONDUJO | Agente → Interaccion | 1:N |
| GENERO_PROMESA | Interaccion → PromesaPago | 1:1 |
| GENERO_PAGO | Interaccion → Pago | 1:1 |
| GENERO_PLAN | Interaccion → PlanPago | 1:1 |
| PROMESA_DE | PromesaPago → Cliente | N:1 |
| PAGO_DE | Pago → Cliente | N:1 |
| PLAN_DE | PlanPago → Cliente | N:1 |
| CUMPLE_PROMESA | Pago → PromesaPago | inferida |
| SIGUIENTE | Interaccion → Interaccion | cadena temporal |

---

## Decisiones Técnicas

### ¿Por qué grafo en lugar de relacional?

Un modelo relacional requeriría JOINs complejos para reconstruir la cadena temporal de interacciones por cliente o para inferir si un pago cumple una promesa previa. En un grafo, las relaciones `SIGUIENTE` y `CUMPLE_PROMESA` son aristas directas, lo que hace las consultas de caminos más intuitivas y eficientes. Además, el grafo permite agregar nuevos tipos de nodos (ej. `Canal`, `Producto`) sin alterar el esquema existente.

### Escalabilidad a 1 millón de clientes

- Índices en `Cliente.id`, `Interaccion.timestamp`, `PromesaPago.fecha_promesa`
- Particionamiento de `Interaccion` por `timestamp` (sharding temporal)
- Paginación en todos los endpoints (`?limite=` + `?offset=`)
- Cache de KPIs del dashboard (Redis, TTL 5 min)
- Graphiti distribuido sobre Neo4j Cluster (Causal Clustering)
- Ingesta en batch con workers paralelos (Celery)

### Otras fuentes de datos útiles

1. **CRM / historial de crédito**: enriquecer nodos `Cliente` con score crediticio, historial bancario
2. **Calendarios y feriados**: optimizar horarios de llamada considerando días no laborables por país
3. **Canales digitales**: WhatsApp, portal web — capturar interacciones autogestionadas que hoy no están en el grafo
4. **Datos macroeconómicos**: correlacionar tasas de incumplimiento con indicadores económicos (inflación, desempleo)

---

## Pipeline ML - Análisis Predictivo

### Arquitectura

```
features.py  ─┐
              │
train.py  ◄───┼─── train_offline.py  (job offline: CLI / cron / Celery beat)
              │         │
              │         ▼
              │    model_registry.py  (joblib dump + registry.json)
              │         │
              │         ▼
inference.py ◄┴─── predictor.py  (load_latest en startup, lock singleflight)
```

### Modelos
- **GradientBoosting** vs **XGBoost** vs **LightGBM**
- Selección automática por ROC-AUC en CV estratificado
- **Anti data-leakage**: `StandardScaler` dentro de `Pipeline` → se ajusta por fold, nunca ve validación
- **Calibración**: `sigmoid` (Platt) si n<1000, `isotonic` si n≥1000
- **Cutoff temporal derivado** de los timestamps reales del dataset (no hardcoded)

### Métricas
- precision, recall, F1, ROC-AUC, accuracy

### Ground Truth
- label=1: tiene pagos reales O promesa cumplida
- label=0: sin actividad reciente (>30 días)
- label=None: sin evidencia suficiente (semi-supervisado)

### Detección de Anomalías
- **IsolationForest + LOF** ensemble (reducen ~30% FP)
- Contamination adaptivo (IQR de Tukey)
- Z-score univariado por feature

### Segmentación
- **KMeans** con k óptimo por **Silhouette score**
- Análisis de mejores horarios y agentes

### Endpoints ML

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/analytics/prediccion` | Score de riesgo por cliente |
| GET | `/analytics/anomalias` | Anomalías detectadas |
| GET | `/analytics/estrategias` | Segmentos y recomendaciones |

---

## Tests

Ejecutar todos los tests:

```bash
# Tests API
python -m pytest api/tests/ -v

# Tests ML específicos
python -m pytest api/tests/test_ml/ -v

# Tests de integración pipeline
python -m pytest api/tests/test_pipeline.py -v
```

---

## Mejoras Futuras

- Tests automatizados (pytest + httpx para la API, playwright para el frontend)
- Tests de ML unitarios
- Modelo de ML para predicción de cumplimiento de promesas
- Alertas automáticas para promesas próximas a vencer
- Exportación a CSV/Excel desde el dashboard
- Autenticación JWT en la API
