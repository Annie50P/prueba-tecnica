# Agente 1 — Ingesta y Modelado de Grafo

## Contexto
Eres el agente de ingesta de un sistema de análisis de cobros.
Tu único trabajo es leer el JSON de interacciones, validarlo, transformarlo y cargarlo en Graphiti.
No tienes contexto de ninguna sesión previa. Todo lo que necesitas está en disco.

---

## Inputs (verificar existencia antes de ejecutar)

```
PLAN.md                              ← schema del grafo, decisiones de diseño
data/interacciones_clientes.json     ← datos originales (SOLO LECTURA, no modificar)
.env                                 ← variables de entorno (NEO4J_*, GRAPHITI_URL)
```

**Validación de inputs — DETENTE si alguno falla:**
1. `data/interacciones_clientes.json` existe y es JSON válido
2. `PLAN.md` existe
3. Variables de entorno `GRAPHITI_URL`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` están definidas
4. Graphiti responde en `$GRAPHITI_URL/health` (HTTP 200)
5. Neo4j responde en el URI bolt configurado

---

## Responsabilidad

Crear e implementar el módulo `ingesta/` completo que:

1. **Valida** el JSON de entrada (schema, tipos, integridad referencial)
2. **Transforma** los datos al modelo de grafo definido en `PLAN.md`
3. **Pre-calcula** propiedades derivadas
4. **Carga** todos los nodos y relaciones en Graphiti vía su API REST
5. **Verifica** que la carga fue exitosa

---

## Schema de Grafo a Implementar

Leer sección **"1. Schema del Grafo"** de `PLAN.md` para los nodos y relaciones exactas.

### Nodos a crear:
- `Cliente` — 50 nodos
- `Agente` — 10 nodos (deduplicados de `interacciones[].agente_id`)
- `Interaccion` — 502 nodos
- `PromesaPago` — 96 nodos (cuando `resultado == "promesa_pago"`)
- `Pago` — 53 nodos (cuando `tipo == "pago_recibido"`)
- `PlanPago` — 55 nodos (cuando `resultado == "renegociacion"`)

### Propiedades derivadas a calcular:

**En `Interaccion`:**
- `hora_del_dia`: `int(timestamp.hour)` (0–23, UTC)
- `dia_semana`: `timestamp.weekday()` (0=lunes, 6=domingo)

**En `PromesaPago`:**
- `cumplida`: `True` si existe un `Pago` del mismo `cliente_id` donde
  `pago.timestamp > interaccion.timestamp` Y
  `pago.timestamp <= fecha_promesa + timedelta(days=3)`
- `dias_hasta_vencimiento`: `(fecha_promesa - interaccion.timestamp.date()).days`

**En `Cliente`:**
- `total_pagado`: suma de `monto` de todos sus `Pago`
- `monto_pendiente`: `monto_deuda_inicial - total_pagado`
- `tasa_cumplimiento`: `promesas_cumplidas / total_promesas` (0.0 si no hay promesas)

**En `Agente`:**
- `total_llamadas`: count de interacciones donde `agente_id == este agente`
- `tasa_promesa`: llamadas con `resultado == "promesa_pago"` / `total_llamadas`
- `tasa_pago_inmediato`: llamadas con `resultado == "pago_inmediato"` / `total_llamadas`

**En `PlanPago`:**
- `monto_total_plan`: `cuotas * monto_mensual`
- `fecha_inicio`: fecha de la interacción de renegociación

### Relaciones a crear (leer `PLAN.md` sección 1.2):
- `TIENE_INTERACCION`: Cliente → Interaccion
- `CONDUJO`: Agente → Interaccion (solo llamadas con agente_id)
- `GENERO_PROMESA`: Interaccion → PromesaPago
- `GENERO_PAGO`: Interaccion → Pago
- `GENERO_PLAN`: Interaccion → PlanPago
- `PROMESA_DE`: PromesaPago → Cliente
- `PAGO_DE`: Pago → Cliente
- `PLAN_DE`: PlanPago → Cliente
- `CUMPLE_PROMESA`: Pago → PromesaPago (inferida, con propiedad `inferido: true`)
- `SIGUIENTE`: Interaccion → Interaccion (cadena cronológica por cliente)

---

## Estructura de Archivos a Crear

```
ingesta/
├── requirements.txt
├── models.py          ← clases Pydantic para validación
├── validators.py      ← validación de integridad referencial
├── transforms.py      ← lógica de transformación y derivados
├── graphiti_client.py ← wrapper HTTP para API REST de Graphiti
└── ingest.py          ← script principal, punto de entrada
```

### `ingesta/requirements.txt`:
```
pydantic>=2.0
requests>=2.31
python-dotenv>=1.0
```

### `ingesta/ingest.py` debe:
1. Cargar `.env`
2. Validar inputs (ver sección anterior)
3. Leer JSON **una sola vez** (`json.load`) y procesar en memoria
4. Crear nodos en orden: Agente → Cliente → Interaccion → PromesaPago → Pago → PlanPago
5. Crear relaciones después de todos los nodos
6. Imprimir progreso cada 50 items: `[ingesta] Cargando Interaccion 50/502...`
7. Al finalizar, escribir `ingesta/ingesta_completada.json` con el resumen

### `ingesta/graphiti_client.py` debe:
- Usar la API REST de Graphiti (base URL desde env `GRAPHITI_URL`)
- Método `create_node(label: str, properties: dict) -> str` que retorna el ID del nodo creado
- Método `create_relationship(from_id: str, rel_type: str, to_id: str, properties: dict = {}) -> bool`
- Método `health_check() -> bool`
- Manejar errores HTTP con reintentos (máximo 3, backoff exponencial)
- Loggear cada request fallido con el payload para debug

---

## Criterio de Éxito

La ingesta termina **correctamente** cuando:

1. El archivo `ingesta/ingesta_completada.json` existe y contiene:
```json
{
  "status": "ok",
  "nodos_creados": {
    "Cliente": 50,
    "Agente": 10,
    "Interaccion": 502,
    "PromesaPago": 96,
    "Pago": 53,
    "PlanPago": 55
  },
  "relaciones_creadas": {
    "TIENE_INTERACCION": 502,
    "CONDUJO": 377,
    "GENERO_PROMESA": 96,
    "GENERO_PAGO": 53,
    "GENERO_PLAN": 55,
    "CUMPLE_PROMESA": "N (variable)",
    "SIGUIENTE": "~452 (502 - 50 clientes)"
  },
  "errores": []
}
```

2. No hay errores en stderr durante la ejecución
3. Una query de verificación a Graphiti devuelve >= 766 nodos en total

---

## Cómo Ejecutar

```bash
cd ingesta
pip install -r requirements.txt
python ingest.py
```

---

## Notas de Implementación

- **No cargues el array completo en variables de contexto del LLM** — procesa con iteradores
- La relación `CUMPLE_PROMESA` debe calcularse **después** de que todos los nodos Pago y PromesaPago existan
- Si un `agente_id` aparece en interacciones pero no tiene nodo Agente aún, créalo en el paso de Agentes
- Los IDs de PromesaPago, Pago y PlanPago se construyen como `{interaccion_id}_promesa`, `{interaccion_id}_pago`, `{interaccion_id}_plan`
- `email` y `sms` solo tienen los 4 campos base — no generar nodos derivados para ellos
- Documentar en comentarios las decisiones de modelado no obvias
