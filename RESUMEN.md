# RESUMEN.md — Analizador de Patrones de Llamadas

---

## 1. Problema a Resolver

Una empresa de gestión de cobros necesita analizar y visualizar los patrones de interacción con sus clientes deudores. El sistema debe:

1. **Ingestar** datos históricos de interacciones desde un JSON plano hacia un **grafo de conocimiento** (Graphiti + Neo4j), modelando entidades, relaciones temporales, estados y transiciones.
2. **Exponer** una API REST (y opcionalmente una interfaz MCP + LLM) para consultas de negocio: timeline por cliente, efectividad de agentes, promesas incumplidas, horarios óptimos.
3. **Visualizar** el grafo y métricas clave en una interfaz web con dashboard, vista de cliente individual y explorador de grafo interactivo.

Los datos cubren **50 clientes**, **502 interacciones** y **10 agentes** a lo largo de ~108 días (2025-05-17 → 2025-09-02).

---

## 2. Diccionario de Datos

### 2.1 Objeto `metadata`

| Campo | Tipo | Ejemplo Real | Observación |
|---|---|---|---|
| `fecha_generacion` | string (ISO-8601 datetime) | `"2025-08-12T13:37:49.852579"` | Sin zona horaria (naive) |
| `total_clientes` | integer | `50` | Coincide con array `clientes` |
| `total_interacciones` | integer | `502` | Coincide con array `interacciones` |
| `periodo` | string | `"90 días"` | Valor descriptivo; el rango real es ~108 días |

### 2.2 Objeto `clientes[]`

| Campo | Tipo | Ejemplo Real | Observación |
|---|---|---|---|
| `id` | string | `"cliente_000"` | Formato `cliente_NNN`, 3 dígitos, obligatorio, único |
| `nombre` | string | `"Cliente 1"` | Nombres sintéticos ("Cliente N"), obligatorio |
| `telefono` | string | `"+507 6656-8011"` | Formato panameño `+507 XXXX-XXXX`, obligatorio |
| `monto_deuda_inicial` | integer | `2062` | Rango: 633–9,645 USD; sin decimales, obligatorio |
| `fecha_prestamo` | string (ISO-8601 date) | `"2024-12-28"` | Formato `YYYY-MM-DD`, obligatorio |
| `tipo_deuda` | string (enum) | `"hipoteca"` | Valores: `auto`, `hipoteca`, `prestamo_personal`, `tarjeta_credito`; obligatorio |

### 2.3 Objeto `interacciones[]` — Campos siempre presentes

| Campo | Tipo | Ejemplo Real | Observación |
|---|---|---|---|
| `id` | string | `"int_ddb0b226"` | Formato `int_XXXXXXXX` (hex 8 chars), obligatorio, único |
| `cliente_id` | string | `"cliente_000"` | FK a `clientes[].id`, obligatorio |
| `timestamp` | string (ISO-8601 datetime + Z) | `"2025-05-17T13:37:49.849120Z"` | UTC con sufijo `Z`, obligatorio |
| `tipo` | string (enum) | `"llamada_saliente"` | Valores: `email`, `llamada_entrante`, `llamada_saliente`, `pago_recibido`, `sms`; obligatorio |

### 2.4 Campos condicionales — Llamadas (`llamada_saliente` / `llamada_entrante`)
Presentes en 377/502 interacciones (todas las llamadas).

| Campo | Tipo | Ejemplo Real | Observación |
|---|---|---|---|
| `duracion_segundos` | integer | `414` | Rango: 30–600 s, avg 317 s; presente en 377/502 |
| `agente_id` | string | `"agente_002"` | Formato `agente_NNN`; 10 agentes únicos (`agente_001`..`agente_010`); presente en 377/502 |
| `resultado` | string (enum) | `"disputa"` | Valores: `disputa`, `pago_inmediato`, `promesa_pago`, `renegociacion`, `se_niega_pagar`, `sin_respuesta`; presente en 377/502 |
| `sentimiento` | string (enum) | `"frustrado"` | Valores: `cooperativo`, `frustrado`, `hostil`, `n/a`, `neutral`; presente en 377/502 |

### 2.5 Campos condicionales — Resultado `promesa_pago`
Presentes cuando `resultado == "promesa_pago"` (96/502).

| Campo | Tipo | Ejemplo Real | Observación |
|---|---|---|---|
| `monto_prometido` | integer | `3060` | Monto comprometido por el cliente; presente en 96/502 |
| `fecha_promesa` | string (ISO-8601 date) | `"2025-05-29"` | Fecha límite de cumplimiento; presente en 96/502 |

### 2.6 Campos condicionales — Resultado `renegociacion`
Presentes cuando `resultado == "renegociacion"` (55/502).

| Campo | Tipo | Observación |
|---|---|---|
| `nuevo_plan_pago` | object | Objeto anidado; presente en 55/502 |
| `nuevo_plan_pago.cuotas` | integer | Ej: `7` — número de cuotas pactadas |
| `nuevo_plan_pago.monto_mensual` | integer | Ej: `294` — monto por cuota en USD |

### 2.7 Campos condicionales — Tipo `pago_recibido`
Presentes en 53/502 interacciones.

| Campo | Tipo | Ejemplo Real | Observación |
|---|---|---|---|
| `monto` | integer | `920` | Rango: 169–3,103 USD; presente en 53/502 |
| `metodo_pago` | string (enum) | `"transferencia"` | Valores: `efectivo`, `tarjeta`, `transferencia`; presente en 53/502 |
| `pago_completo` | boolean | `true` | `true` en 31 casos, `false` en 22 (pago parcial); presente en 53/502 |

---

## 3. Entidades Identificadas y Relaciones

### 3.1 Entidades

| Entidad | Fuente | Cardinalidad | Propiedades clave |
|---|---|---|---|
| **Cliente** | `clientes[]` | 50 instancias | id, nombre, telefono, monto_deuda_inicial, fecha_prestamo, tipo_deuda |
| **Agente** | `interacciones[].agente_id` | 10 instancias | id (agente_001..010) |
| **Interaccion** | `interacciones[]` | 502 instancias | id, timestamp, tipo, + campos condicionales |
| **PromesaPago** | subset de Interaccion (`resultado=promesa_pago`) | 96 instancias | monto_prometido, fecha_promesa, cumplida (derivado) |
| **Pago** | subset de Interaccion (`tipo=pago_recibido`) | 53 instancias | monto, metodo_pago, pago_completo |
| **PlanPago** | objeto anidado en Interaccion (`resultado=renegociacion`) | 55 instancias | cuotas, monto_mensual |

### 3.2 Relaciones

| Relación | Desde | Hacia | Tipo | Cardinalidad | Notas |
|---|---|---|---|---|---|
| `TIENE_INTERACCION` | Cliente | Interaccion | directa | 1:N | Un cliente tiene múltiples interacciones |
| `CONDUJO` | Agente | Interaccion | directa | 1:N | Un agente conduce múltiples llamadas |
| `GENERO_PROMESA` | Interaccion | PromesaPago | derivada | 1:1 (opcional) | Solo cuando resultado=promesa_pago |
| `RECIBIO_PAGO` | Cliente | Pago | derivada | 1:N | Extraído de interacciones tipo pago_recibido |
| `TIENE_PLAN` | Cliente | PlanPago | derivada | 1:N | Extraído de interacciones con renegociacion |
| `CUMPLE_PROMESA` | Pago | PromesaPago | implícita | N:M (aproximada) | No hay FK directa; se infiere por cliente_id + fecha |
| `SIGUIENTE` | Interaccion | Interaccion | temporal | 1:1 (por cliente) | Cadena cronológica por cliente |

**Relación implícita clave**: No existe un campo que vincule directamente una `PromesaPago` con un `Pago` posterior. La conexión debe inferirse por `cliente_id` + comparación de fechas (`fecha_promesa` vs `timestamp` del pago).

**Gap importante**: 96 promesas vs 53 pagos → tasa de cumplimiento ~55% como techo máximo (algunos pagos pueden no tener promesa previa).

---

## 4. Lista Completa de Requisitos

### 4.1 Ingesta y Modelado de Grafo (40%)

- [ ] Leer y validar `interacciones_clientes.json` (schema, tipos, integridad referencial)
- [ ] Diseñar estructura de grafo con nodos: Cliente, Agente, Interaccion, PromesaPago, Pago, PlanPago
- [ ] Modelar relaciones temporales entre interacciones (orden cronológico por cliente)
- [ ] Modelar transiciones de estado: promesa → pago / incumplimiento
- [ ] Implementar carga a Graphiti mediante su API REST
- [ ] Pre-calcular propiedades derivadas útiles en el grafo (ej: `dias_desde_prestamo`, `promesa_cumplida`, `tasa_incumplimiento`)
- [ ] Documentar decisiones de modelado

### 4.2 API REST de Consultas (30%)

- [ ] `GET /clientes/{id}/timeline` — historial completo cronológico de un cliente
- [ ] `GET /agentes/{id}/efectividad` — métricas de desempeño del agente (tasa resolución, tipos de resultado, sentimientos)
- [ ] `GET /analytics/promesas-incumplidas` — clientes con promesas vencidas sin pago posterior
- [ ] `GET /analytics/mejores-horarios` — análisis de horarios más efectivos para contacto
- [ ] Integración MCP + LLM con servidor MCP de Graphiti para consultas en lenguaje natural
- [ ] Configurar servidor MCP de Graphiti
- [ ] Integrar con LLM (OpenAI, Anthropic, o Ollama) para interpretar consultas en lenguaje natural

### 4.3 Visualización Web (30%)

**Dashboard General**
- [ ] KPIs principales: tasa de recuperación, promesas cumplidas vs incumplidas, total cobrado vs deuda total
- [ ] Distribución de tipos de deuda (gráfico)
- [ ] Actividad por período de tiempo (timeline/heatmap)

**Vista de Cliente Individual**
- [ ] Timeline interactivo de todas las interacciones del cliente
- [ ] Estado actual y evolución de la deuda
- [ ] Predicción de comportamiento futuro (ML simple o heurístico)

**Vista de Grafo**
- [ ] Visualización del grafo de relaciones (D3.js, Cytoscape.js, o Vis.js)
- [ ] Exploración interactiva de conexiones entre entidades
- [ ] Filtros por: tipo de relación, período de tiempo, resultado de interacción

### 4.4 Bonus (tratados como obligatorios)

- [ ] Análisis predictivo (probabilidad de pago basada en historial)
- [ ] Detección de anomalías (patrones inusuales de comportamiento)
- [ ] Optimización de estrategias (recomendaciones de horario/agente por tipo de cliente)
- [ ] Tests automatizados (unitarios e integración)
- [ ] Deployment (Docker Compose funcional con neo4j + graphiti + api + frontend)

### 4.5 Entrega

- [ ] Repositorio Git con `.gitignore` apropiado y sin credenciales
- [ ] `README.md` con: descripción, instalación paso a paso, cómo ejecutar, decisiones técnicas, mejoras futuras
- [ ] Esquema del modelo de grafo (diagrama o descripción detallada)
- [ ] Lista de endpoints API implementados
- [ ] Respuestas a las 3 preguntas de reflexión:
  1. Ventajas de grafo vs relacional para este problema
  2. Escalabilidad a 1 millón de clientes
  3. Otras fuentes de datos útiles para el análisis

---

## Observaciones Técnicas Relevantes

- **`email` y `sms`** no tienen campos adicionales más allá de los 4 obligatorios — son interacciones de contacto sin resultado registrado.
- **`sentimiento: "n/a"`** aparece en llamadas donde no aplica análisis de sentimiento (posiblemente buzón de voz o sin respuesta).
- **No hay FK directa** entre promesas y pagos — esta relación debe construirse como inferencia en el grafo.
- **Montos enteros** en todos los casos (sin decimales en los datos reales, aunque el schema define `number`).
- **Timestamps de interacciones** tienen zona horaria UTC (`Z`), mientras que `fecha_generacion` en metadata no tiene zona horaria.
