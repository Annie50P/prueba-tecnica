# PLAN.md — Analizador de Patrones de Llamadas

> Fuente de verdad compartida entre todos los agentes.
> Archivo: `PLAN.md` en la raíz del proyecto.

---

## 1. Schema del Grafo (Neo4j / Graphiti)

### 1.1 Nodos

#### `Cliente`
| Propiedad | Tipo | Constraint |
|---|---|---|
| `id` | string | UNIQUE, NOT NULL |
| `nombre` | string | NOT NULL |
| `telefono` | string | — |
| `monto_deuda_inicial` | integer | NOT NULL |
| `fecha_prestamo` | date (ISO) | NOT NULL |
| `tipo_deuda` | string (enum) | NOT NULL |
| `monto_pendiente` | integer | Derivado: calculado en ingesta |
| `total_pagado` | integer | Derivado: suma de pagos recibidos |
| `tasa_cumplimiento` | float | Derivado: pagos_realizados / promesas_hechas |

#### `Agente`
| Propiedad | Tipo | Constraint |
|---|---|---|
| `id` | string | UNIQUE, NOT NULL |
| `total_llamadas` | integer | Derivado |
| `tasa_promesa` | float | Derivado: llamadas con promesa / total llamadas |
| `tasa_pago_inmediato` | float | Derivado |

#### `Interaccion`
| Propiedad | Tipo | Constraint |
|---|---|---|
| `id` | string | UNIQUE, NOT NULL |
| `cliente_id` | string | NOT NULL, FK → Cliente |
| `timestamp` | datetime (UTC) | NOT NULL |
| `tipo` | string (enum) | NOT NULL |
| `duracion_segundos` | integer | Opcional (solo llamadas) |
| `agente_id` | string | Opcional (solo llamadas) |
| `resultado` | string (enum) | Opcional (solo llamadas) |
| `sentimiento` | string (enum) | Opcional (solo llamadas) |
| `hora_del_dia` | integer | Derivado: hora UTC de timestamp (0–23) |
| `dia_semana` | integer | Derivado: 0=lunes … 6=domingo |

#### `PromesaPago`
| Propiedad | Tipo | Constraint |
|---|---|---|
| `id` | string | UNIQUE, NOT NULL (= `interaccion_id + "_promesa"`) |
| `interaccion_id` | string | NOT NULL, FK → Interaccion |
| `cliente_id` | string | NOT NULL, FK → Cliente |
| `monto_prometido` | integer | NOT NULL |
| `fecha_promesa` | date (ISO) | NOT NULL |
| `cumplida` | boolean | Derivado: true si existe Pago del mismo cliente posterior a timestamp y antes/en fecha_promesa |
| `dias_hasta_vencimiento` | integer | Derivado en ingesta |

#### `Pago`
| Propiedad | Tipo | Constraint |
|---|---|---|
| `id` | string | UNIQUE, NOT NULL (= `interaccion_id + "_pago"`) |
| `interaccion_id` | string | NOT NULL, FK → Interaccion |
| `cliente_id` | string | NOT NULL, FK → Cliente |
| `timestamp` | datetime (UTC) | NOT NULL |
| `monto` | integer | NOT NULL |
| `metodo_pago` | string (enum) | NOT NULL |
| `pago_completo` | boolean | NOT NULL |

#### `PlanPago`
| Propiedad | Tipo | Constraint |
|---|---|---|
| `id` | string | UNIQUE, NOT NULL (= `interaccion_id + "_plan"`) |
| `interaccion_id` | string | NOT NULL, FK → Interaccion |
| `cliente_id` | string | NOT NULL, FK → Cliente |
| `cuotas` | integer | NOT NULL |
| `monto_mensual` | integer | NOT NULL |
| `monto_total_plan` | integer | Derivado: cuotas × monto_mensual |
| `fecha_inicio` | date | = fecha de la interacción de renegociación |

---

### 1.2 Relaciones

| Relación | Desde | Hacia | Cardinalidad | Propiedades |
|---|---|---|---|---|
| `TIENE_INTERACCION` | Cliente | Interaccion | 1:N | — |
| `CONDUJO` | Agente | Interaccion | 1:N | — |
| `GENERO_PROMESA` | Interaccion | PromesaPago | 1:1 (condicional) | — |
| `GENERO_PAGO` | Interaccion | Pago | 1:1 (condicional) | — |
| `GENERO_PLAN` | Interaccion | PlanPago | 1:1 (condicional) | — |
| `PROMESA_DE` | PromesaPago | Cliente | N:1 | — |
| `PAGO_DE` | Pago | Cliente | N:1 | — |
| `PLAN_DE` | PlanPago | Cliente | N:1 | — |
| `CUMPLE_PROMESA` | Pago | PromesaPago | N:M (inferida) | `inferido: true` |
| `SIGUIENTE` | Interaccion | Interaccion | 1:1 (por cliente) | `cliente_id` |

**Lógica de `CUMPLE_PROMESA`**: Para cada `PromesaPago` con `cumplida=false`, buscar Pagos del mismo cliente donde `pago.timestamp > promesa.interaccion.timestamp` y `pago.timestamp <= promesa.fecha_promesa + 3 días` (margen de gracia).

---

### 1.3 Índices Recomendados (Neo4j)

```cypher
CREATE INDEX ON :Cliente(id);
CREATE INDEX ON :Agente(id);
CREATE INDEX ON :Interaccion(id);
CREATE INDEX ON :Interaccion(cliente_id);
CREATE INDEX ON :Interaccion(timestamp);
CREATE INDEX ON :Interaccion(tipo);
CREATE INDEX ON :Interaccion(resultado);
CREATE INDEX ON :Interaccion(hora_del_dia);
CREATE INDEX ON :PromesaPago(cliente_id);
CREATE INDEX ON :PromesaPago(fecha_promesa);
CREATE INDEX ON :PromesaPago(cumplida);
CREATE INDEX ON :Pago(cliente_id);
CREATE INDEX ON :Pago(timestamp);
```

---

## 2. Endpoints de la API REST

Base URL: `http://localhost:8001`

| # | Método | Ruta | Descripción | Input | Output |
|---|---|---|---|---|---|
| 1 | GET | `/clientes` | Listar todos los clientes con métricas básicas | — | Array de clientes + métricas derivadas |
| 2 | GET | `/clientes/{id}` | Detalle completo de un cliente | `id`: path param | Objeto cliente completo |
| 3 | GET | `/clientes/{id}/timeline` | Historial cronológico completo | `id`: path param | Array de interacciones ordenadas por timestamp |
| 4 | GET | `/agentes` | Listar agentes con métricas | — | Array de agentes + métricas |
| 5 | GET | `/agentes/{id}/efectividad` | Métricas de desempeño del agente | `id`: path param | `{total_llamadas, tasa_promesa, tasa_pago_inmediato, distribucion_resultados, distribucion_sentimientos, mejor_horario}` |
| 6 | GET | `/analytics/promesas-incumplidas` | Clientes con promesas vencidas sin pago | `?fecha=YYYY-MM-DD` (opcional, default: hoy) | Array de `{cliente, promesa, dias_vencida}` |
| 7 | GET | `/analytics/mejores-horarios` | Horarios y días más efectivos | `?resultado=promesa_pago` (opcional) | Array de `{hora, dia_semana, total_llamadas, tasa_exito}` |
| 8 | GET | `/analytics/dashboard` | KPIs globales del dashboard | — | `{total_deuda, total_recuperado, tasa_recuperacion, promesas_cumplidas, promesas_incumplidas, distribucion_deuda_tipo, actividad_por_dia}` |
| 9 | GET | `/grafo/nodos` | Nodos para visualización | `?tipo=Cliente,Agente,...` `?limite=200` | Array de `{id, tipo, label, propiedades}` |
| 10 | GET | `/grafo/relaciones` | Relaciones para visualización | `?cliente_id=...` `?tipo_rel=...` | Array de `{source, target, tipo}` |
| 11 | POST | `/mcp/query` | Consulta en lenguaje natural vía MCP+LLM | `{"query": "¿Cuáles agentes tienen más promesas cumplidas?"}` | `{"respuesta": "...", "datos": [...]}` |

**Códigos de respuesta estándar**: `200 OK`, `404 Not Found` (`{"error": "not_found", "message": "..."}`), `422 Unprocessable Entity`, `500 Internal Server Error`.

---

## 3. Estructura de Carpetas del Proyecto

```
/
├── PLAN.md                          ← fuente de verdad compartida
├── RESUMEN.md                       ← análisis de datos
├── prompts/
│   ├── agente1_ingesta.md
│   ├── agente2_api.md
│   ├── agente3_frontend.md
│   └── agente4_mcp.md
├── data/
│   └── interacciones_clientes.json  ← datos originales (solo lectura)
├── ingesta/
│   ├── ingest.py                    ← script principal de ingesta
│   ├── models.py                    ← clases de dominio (Pydantic)
│   ├── graphiti_client.py           ← wrapper de API REST de Graphiti
│   ├── validators.py                ← validación del JSON
│   └── requirements.txt
├── api/
│   ├── main.py                      ← FastAPI app + routers
│   ├── routers/
│   │   ├── clientes.py
│   │   ├── agentes.py
│   │   ├── analytics.py
│   │   ├── grafo.py
│   │   └── mcp_query.py
│   ├── services/
│   │   ├── graphiti_service.py      ← queries a Graphiti/Neo4j
│   │   └── mcp_service.py          ← integración MCP + LLM
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.js                  ← entrypoint
│   │   ├── api.js                   ← cliente HTTP para la API
│   │   ├── views/
│   │   │   ├── Dashboard.js
│   │   │   ├── ClienteDetalle.js
│   │   │   └── GrafoViewer.js
│   │   └── components/
│   │       ├── Timeline.js
│   │       ├── KpiCard.js
│   │       └── GrafoD3.js
│   └── package.json
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Decisiones de Diseño

### 4.1 Graphiti como capa de grafo (no Neo4j directo)
Graphiti es el requirement explícito del enunciado. Expone una API REST sobre Neo4j, lo que permite separar la lógica de negocio de la capa de base de datos. Los agentes 1 y 2 se comunican con Graphiti vía HTTP, no con Neo4j directamente.

### 4.2 Nodos separados para PromesaPago, Pago y PlanPago
Aunque estas entidades están embebidas en `interacciones[]`, extraerlas como nodos propios permite:
- Queries directos sin filtrar por propiedades de Interaccion
- Modelar la relación `CUMPLE_PROMESA` como arista explícita
- Calcular métricas de incumplimiento eficientemente

### 4.3 Propiedades derivadas pre-calculadas en ingesta
`hora_del_dia`, `dia_semana`, `cumplida`, `monto_pendiente`, `tasa_cumplimiento` se calculan **una sola vez** en la ingesta y se almacenan como propiedades del nodo. Esto evita cálculos on-the-fly en cada query de la API.

### 4.4 Inferencia de `CUMPLE_PROMESA` en ingesta
La relación promesa→pago no tiene FK en el JSON original. Se infiere en ingesta: para cada promesa, se busca el primer pago del mismo cliente dentro del ventana `[timestamp_promesa, fecha_promesa + 3 días]`. Esta lógica vive en `ingesta/ingest.py` y el resultado se almacena como propiedad `cumplida: bool` en el nodo `PromesaPago`.

### 4.5 FastAPI para la API REST
FastAPI provee validación automática con Pydantic, documentación OpenAPI/Swagger en `/docs`, y es estándar en el ecosistema Python donde vive Graphiti.

### 4.6 Vanilla JS + D3.js para el frontend
Sin framework de build para reducir complejidad de setup. D3.js para el grafo de fuerza (force-directed), Chart.js para KPIs y gráficos estadísticos. El frontend consume la API REST del agente 2.

### 4.7 MCP + Anthropic Claude para consultas naturales
El servidor MCP de Graphiti se ejecuta como proceso separado. El endpoint `POST /mcp/query` actúa como proxy: recibe la query en lenguaje natural, la envía al LLM (Claude via API de Anthropic) con acceso a las tools MCP, y retorna la respuesta estructurada.

### 4.8 Un `docker-compose.yml` para todo
Neo4j + Graphiti + API + Frontend se levantan con un solo `docker compose up`. Variables sensibles (claves API) se pasan por `.env`, nunca hardcodeadas.

### 4.9 JSON de datos en carpeta `data/` (solo lectura)
El archivo original nunca se modifica. La ingesta lee de `data/interacciones_clientes.json`. Esto permite re-ejecutar la ingesta desde cero sin perder los datos originales.

---

## 5. Variables de Entorno Requeridas (`.env.example`)

```
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
GRAPHITI_URL=http://graphiti:8000
ANTHROPIC_API_KEY=sk-ant-...
API_PORT=8001
FRONTEND_PORT=3000
```

---

## 6. Orden de Ejecución de Agentes

```
Agente 1 (ingesta)   → popula Neo4j/Graphiti
         ↓
Agente 2 (api)       → levanta FastAPI que consulta Graphiti
         ↓
Agente 3 (frontend)  → SPA que consume la API
         ↓
Agente 4 (mcp)       → agrega endpoint /mcp/query a la API existente
```

**Dependencias entre agentes:**
- Agente 2 requiere que Agente 1 haya completado la ingesta (Graphiti con datos)
- Agente 3 requiere que Agente 2 esté corriendo (API disponible en `:8001`)
- Agente 4 requiere Agente 2 (modifica `api/`) + `ANTHROPIC_API_KEY` configurada
