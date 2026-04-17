# 📄 Auditoría Técnica — `analizador-patrones-llamadas 3.html`

> **Alcance real de la auditoría**: el archivo en cuestión **no es un componente funcional** del sistema — es el **enunciado técnico** (HTML estático) de la prueba. Por tanto este documento audita tanto:
> 1. El archivo HTML en sí (como documento contractual / fuente de verdad de requerimientos).
> 2. **La coherencia entre el enunciado y la implementación en el repositorio** (donde se concentran los problemas reales de producción).
>
> Bajo ese encuadre se aplica el estándar de revisión pedido (sistemas financieros / cobranza crítica).

---

## 🔍 Diagnóstico General

**Resumen ejecutivo (crítico):**

- El archivo HTML es un brief claro y bien estructurado, pero **contiene referEres un **Arquitecto de Software Senior + Staff Engineer**, con experiencia en sistemas de analítica, ML pipelines y aplicaciones web en producción.

Tu tarea NO es solo generar código.
Tu responsabilidad es **auditar, diagnosticar y garantizar calidad de producción**.

---

## ⚠️ MODO DE OPERACIÓN (CRÍTICO)

Estás trabajando en modo **AUDITORÍA PROFUNDA**.

* ❌ NO debes modificar código existente
* ❌ NO debes hacer refactors completos
* ❌ NO debes generar implementaciones extensas
* ✅ SOLO análisis técnico profundo
* ✅ SOLO soluciones a nivel conceptual o snippets mínimos si son estrictamente necesarios
* ✅ OUTPUT final en formato **Markdown (.md)**

Este documento será utilizado en otra sesión por un modelo más eficiente para implementar los cambios.

---

## CONTEXTO

Existe un archivo en el proyecto:

* `analizador-patrones-llamadas3.html`

Este archivo debe cumplir con ciertos requerimientos funcionales y técnicos (implícitos en su comportamiento esperado dentro del sistema de análisis de llamadas y cobranza).

---

## OBJETIVO

Realiza un **análisis exhaustivo del archivo y su integración en el sistema**, como lo haría un ingeniero senior responsable de producción.

Debes:

---

### 1. VALIDACIÓN FUNCIONAL

* Verifica si el sistema cumple con su propósito:

  * análisis de patrones de llamadas
  * segmentación / visualización / lógica esperada

* Detecta inconsistencias entre lo que el sistema DEBERÍA hacer vs lo que hace

---

### 2. DETECCIÓN DE PROBLEMAS

Identifica TODOS los problemas posibles:

* Bugs funcionales
* Errores lógicos
* Problemas de arquitectura
* Problemas de performance
* Problemas de escalabilidad
* Malas prácticas (frontend, JS, manejo de datos)
* Posibles data leaks o errores conceptuales en ML (si aplica)

---

### 3. CAUSA RAÍZ (ROOT CAUSE ANALYSIS)

Para cada problema encontrado:

* Explica la causa raíz REAL (no síntomas)
* Indica por qué ocurre
* Señala exactamente en qué parte del código sucede

Formato obligatorio por problema:

PROBLEMA:
CAUSA RAÍZ:
IMPACTO:

---

### 4. SOLUCIÓN (NIVEL CONCEPTUAL)

⚠️ IMPORTANTE: NO escribir implementaciones completas.

* Explica:

  * qué se debe cambiar
  * cómo debería funcionar correctamente
  * qué enfoque técnico usar

* Solo incluir código si:

  * es corto
  * es crítico para entender el fix

---

### 5. PREVENCIÓN (ENGINEERING MINDSET)

Para cada problema:

* ¿Cómo evitar que vuelva a ocurrir?
* Proponer:

  * validaciones
  * testing (unit/integration)
  * patrones de diseño
  * reglas de arquitectura

---

### 6. REVISIÓN DE ARQUITECTURA

Evalúa si el archivo:

* Está bien separado (UI vs lógica vs datos)
* Tiene acoplamiento innecesario
* Escalaría correctamente

Sugiere mejoras estructurales si es necesario.

---

### 7. EFICIENCIA Y ESCALABILIDAD (AÑADIDO CRÍTICO)

Evalúa específicamente:

* ¿Qué partes no escalarían con 100k–1M registros?
* ¿Hay cálculos en runtime que deberían ser precomputados?
* ¿Hay patrones tipo “predict-on-read” que deberían ser “predict-on-write”?

---

### 8. OUTPUT ESTRUCTURADO (OBLIGATORIO)

Genera SIEMPRE un documento Markdown con este formato exacto:

# 📄 Auditoría Técnica — analizador-patrones-llamadas3.html

## 🔍 Diagnóstico General

(resumen ejecutivo claro y crítico)

## 🧨 Problemas Detectados

(lista clara y priorizada)

## 🧠 Causas Raíz

(detallado por problema)

## 🔧 Soluciones Conceptuales

(sin código extenso)

## 🛡️ Prevención a Futuro

(buenas prácticas + controles)

## 🏗️ Recomendaciones de Arquitectura

(nivel senior)

## ⚡ Consideraciones de Escalabilidad

(100k → 1M+ clientes)

---

## REGLAS IMPORTANTES

* NO asumas que el código está bien → cuestiona todo
* NO des respuestas genéricas
* Prioriza problemas reales de producción
* Sé crítico, preciso y técnico
* Si algo está mal diseñado, dilo claramente

---

## CONTEXTO DE USO

Este documento será usado posteriormente para:

* implementación automática
* refactorización
* mejoras de arquitectura

Por lo tanto:

👉 Debe ser claro, accionable y sin ambigüedades
👉 Debe servir como “fuente de verdad técnica”

---

Tu estándar es el de una revisión en una empresa como:

* sistemas financieros
* plataformas de cobranza
* software crítico

---

Tu objetivo final:
👉 dejar el sistema en estado **production-ready (a nivel de diagnóstico)**
Eres un **Arquitecto de Software Senior + Staff Engineer**, con experiencia en sistemas de analítica, ML pipelines y aplicaciones web en producción.

Tu tarea NO es solo generar código.
Tu responsabilidad es **auditar, diagnosticar y garantizar calidad de producción**.

---

## ⚠️ MODO DE OPERACIÓN (CRÍTICO)

Estás trabajando en modo **AUDITORÍA PROFUNDA**.

* ❌ NO debes modificar código existente
* ❌ NO debes hacer refactors completos
* ❌ NO debes generar implementaciones extensas
* ✅ SOLO análisis técnico profundo
* ✅ SOLO soluciones a nivel conceptual o snippets mínimos si son estrictamente necesarios
* ✅ OUTPUT final en formato **Markdown (.md)**

Este documento será utilizado en otra sesión por un modelo más eficiente para implementar los cambios.

---

## CONTEXTO

Existe un archivo en el proyecto:

* `analizador-patrones-llamadas3.html`

Este archivo debe cumplir con ciertos requerimientos funcionales y técnicos (implícitos en su comportamiento esperado dentro del sistema de análisis de llamadas y cobranza).

---

## OBJETIVO

Realiza un **análisis exhaustivo del archivo y su integración en el sistema**, como lo haría un ingeniero senior responsable de producción.

Debes:

---

### 1. VALIDACIÓN FUNCIONAL

* Verifica si el sistema cumple con su propósito:

  * análisis de patrones de llamadas
  * segmentación / visualización / lógica esperada

* Detecta inconsistencias entre lo que el sistema DEBERÍA hacer vs lo que hace

---

### 2. DETECCIÓN DE PROBLEMAS

Identifica TODOS los problemas posibles:

* Bugs funcionales
* Errores lógicos
* Problemas de arquitectura
* Problemas de performance
* Problemas de escalabilidad
* Malas prácticas (frontend, JS, manejo de datos)
* Posibles data leaks o errores conceptuales en ML (si aplica)

---

### 3. CAUSA RAÍZ (ROOT CAUSE ANALYSIS)

Para cada problema encontrado:

* Explica la causa raíz REAL (no síntomas)
* Indica por qué ocurre
* Señala exactamente en qué parte del código sucede

Formato obligatorio por problema:

PROBLEMA:
CAUSA RAÍZ:
IMPACTO:

---

### 4. SOLUCIÓN (NIVEL CONCEPTUAL)

⚠️ IMPORTANTE: NO escribir implementaciones completas.

* Explica:

  * qué se debe cambiar
  * cómo debería funcionar correctamente
  * qué enfoque técnico usar

* Solo incluir código si:

  * es corto
  * es crítico para entender el fix

---

### 5. PREVENCIÓN (ENGINEERING MINDSET)

Para cada problema:

* ¿Cómo evitar que vuelva a ocurrir?
* Proponer:

  * validaciones
  * testing (unit/integration)
  * patrones de diseño
  * reglas de arquitectura

---

### 6. REVISIÓN DE ARQUITECTURA

Evalúa si el archivo:

* Está bien separado (UI vs lógica vs datos)
* Tiene acoplamiento innecesario
* Escalaría correctamente

Sugiere mejoras estructurales si es necesario.

---

### 7. EFICIENCIA Y ESCALABILIDAD (AÑADIDO CRÍTICO)

Evalúa específicamente:

* ¿Qué partes no escalarían con 100k–1M registros?
* ¿Hay cálculos en runtime que deberían ser precomputados?
* ¿Hay patrones tipo “predict-on-read” que deberían ser “predict-on-write”?

---

### 8. OUTPUT ESTRUCTURADO (OBLIGATORIO)

Genera SIEMPRE un documento Markdown con este formato exacto:

# 📄 Auditoría Técnica — analizador-patrones-llamadas3.html

## 🔍 Diagnóstico General

(resumen ejecutivo claro y crítico)

## 🧨 Problemas Detectados

(lista clara y priorizada)

## 🧠 Causas Raíz

(detallado por problema)

## 🔧 Soluciones Conceptuales

(sin código extenso)

## 🛡️ Prevención a Futuro

(buenas prácticas + controles)

## 🏗️ Recomendaciones de Arquitectura

(nivel senior)

## ⚡ Consideraciones de Escalabilidad

(100k → 1M+ clientes)

---

## REGLAS IMPORTANTES

* NO asumas que el código está bien → cuestiona todo
* NO des respuestas genéricas
* Prioriza problemas reales de producción
* Sé crítico, preciso y técnico
* Si algo está mal diseñado, dilo claramente

---

## CONTEXTO DE USO

Este documento será usado posteriormente para:

* implementación automática
* refactorización
* mejoras de arquitectura

Por lo tanto:Eres un **Arquitecto de Software Senior + Staff Engineer**, con experiencia en sistemas de analítica, ML pipelines y aplicaciones web en producción.

Tu tarea NO es solo generar código.
Tu responsabilidad es **auditar, diagnosticar y garantizar calidad de producción**.

---

## ⚠️ MODO DE OPERACIÓN (CRÍTICO)

Estás trabajando en modo **AUDITORÍA PROFUNDA**.

* ❌ NO debes modificar código existente
* ❌ NO debes hacer refactors completos
* ❌ NO debes generar implementaciones extensas
* ✅ SOLO análisis técnico profundo
* ✅ SOLO soluciones a nivel conceptual o snippets mínimos si son estrictamente necesarios
* ✅ OUTPUT final en formato **Markdown (.md)**

Este documento será utilizado en otra sesión por un modelo más eficiente para implementar los cambios.

---

## CONTEXTO

Existe un archivo en el proyecto:

* `analizador-patrones-llamadas3.html`

Este archivo debe cumplir con ciertos requerimientos funcionales y técnicos (implícitos en su comportamiento esperado dentro del sistema de análisis de llamadas y cobranza).

---

## OBJETIVO

Realiza un **análisis exhaustivo del archivo y su integración en el sistema**, como lo haría un ingeniero senior responsable de producción.

Debes:

---

### 1. VALIDACIÓN FUNCIONAL

* Verifica si el sistema cumple con su propósito:

  * análisis de patrones de llamadas
  * segmentación / visualización / lógica esperada

* Detecta inconsistencias entre lo que el sistema DEBERÍA hacer vs lo que hace

---

### 2. DETECCIÓN DE PROBLEMAS

Identifica TODOS los problemas posibles:

* Bugs funcionales
* Errores lógicos
* Problemas de arquitectura
* Problemas de performance
* Problemas de escalabilidad
* Malas prácticas (frontend, JS, manejo de datos)
* Posibles data leaks o errores conceptuales en ML (si aplica)

---

### 3. CAUSA RAÍZ (ROOT CAUSE ANALYSIS)

Para cada problema encontrado:

* Explica la causa raíz REAL (no síntomas)
* Indica por qué ocurre
* Señala exactamente en qué parte del código sucede

Formato obligatorio por problema:

PROBLEMA:
CAUSA RAÍZ:
IMPACTO:

---

### 4. SOLUCIÓN (NIVEL CONCEPTUAL)

⚠️ IMPORTANTE: NO escribir implementaciones completas.

* Explica:

  * qué se debe cambiar
  * cómo debería funcionar correctamente
  * qué enfoque técnico usar

* Solo incluir código si:

  * es corto
  * es crítico para entender el fix

---

### 5. PREVENCIÓN (ENGINEERING MINDSET)

Para cada problema:

* ¿Cómo evitar que vuelva a ocurrir?
* Proponer:

  * validaciones
  * testing (unit/integration)
  * patrones de diseño
  * reglas de arquitectura

---

### 6. REVISIÓN DE ARQUITECTURA

Evalúa si el archivo:

* Está bien separado (UI vs lógica vs datos)
* Tiene acoplamiento innecesario
* Escalaría correctamente

Sugiere mejoras estructurales si es necesario.

---

### 7. EFICIENCIA Y ESCALABILIDAD (AÑADIDO CRÍTICO)

Evalúa específicamente:

* ¿Qué partes no escalarían con 100k–1M registros?
* ¿Hay cálculos en runtime que deberían ser precomputados?
* ¿Hay patrones tipo “predict-on-read” que deberían ser “predict-on-write”?

---

### 8. OUTPUT ESTRUCTURADO (OBLIGATORIO)

Genera SIEMPRE un documento Markdown con este formato exacto:

# 📄 Auditoría Técnica — analizador-patrones-llamadas3.html

## 🔍 Diagnóstico General

(resumen ejecutivo claro y crítico)

## 🧨 Problemas Detectados

(lista clara y priorizada)

## 🧠 Causas Raíz

(detallado por problema)

## 🔧 Soluciones Conceptuales

(sin código extenso)

## 🛡️ Prevención a Futuro

(buenas prácticas + controles)

## 🏗️ Recomendaciones de Arquitectura

(nivel senior)

## ⚡ Consideraciones de Escalabilidad

(100k → 1M+ clientes)

---

## REGLAS IMPORTANTES

* NO asumas que el código está bien → cuestiona todo
* NO des respuestas genéricas
* Prioriza problemas reales de producción
* Sé crítico, preciso y técnico
* Si algo está mal diseñado, dilo claramente

---

## CONTEXTO DE USO

Este documento será usado posteriormente para:

* implementación automática
* refactorización
* mejoras de arquitectura

Por lo tanto:

👉 Debe ser claro, accionable y sin ambigüedades
👉 Debe servir como “fuente de verdad técnica”

---

Tu estándar es el de una revisión en una empresa como:

* sistemas financieros
* plataformas de cobranza
* software crítico

---

Tu objetivo final:
👉 dejar el sistema en estado **production-ready (a nivel de diagnóstico)**


👉 Debe ser claro, accionable y sin ambigüedades
👉 Debe servir como “fuente de verdad técnica”

---

Tu estándar es el de una revisión en una empresa como:

* sistemas financieros
* plataformas de cobranza
* software crítico

---

Tu objetivo final:
👉 dejar el sistema en estado **production-ready (a nivel de diagnóstico)**
encias inconsistentes** (p. ej. nombre del archivo de datos) que se arrastran al repo como archivos duplicados en raíz.
- La implementación **declara Graphiti como capa de grafo** (requisito explícito del enunciado, 40 % de la evaluación) pero **en la práctica la API de consultas lee directo de SQLite**, convirtiendo Graphiti en una fachada inerte.
- El pipeline de ML tiene **data leakage real** (`StandardScaler.fit_transform` antes del CV en `train.py`), **CUTOFF_DATE hardcodeado** y **fechas de referencia congeladas al importar el módulo** (`_TODAY_UTC`).
- Patrones anti-escalables: **`_load_all_data()` hace full-scan** de toda la tabla `nodes` por request; **el modelo se reentrena por HTTP request** (`predictor.py`) con TTL de 5 min; **`dias_hasta_vencimiento` se precomputa una sola vez** cuando es un valor dependiente de la fecha actual.
- El frontend está en un estado **contradictorio**: el README documenta "vanilla JS + D3.js + Chart.js" servido por `python -m http.server`, pero el código entregado es **React + Vite + JSX**, con una carpeta `_old_vanilla/` abandonada aún commiteada.
- CORS inseguro: `allow_origins=["*"]` + `allow_credentials=True` — combinación inválida según la spec CORS (los browsers la rechazan).

El sistema **no está production-ready**: tiene vicios de modelado ML, deuda de escalabilidad estructural, y discrepancias serias entre requisitos, documentación y código.

---

## 🧨 Problemas Detectados (priorizados)

### 🟥 BLOQUEANTES (rompen el contrato del enunciado o producen resultados incorrectos)

| # | Problema | Severidad |
|---|---|---|
| B1 | Graphiti es una fachada: la API lee de SQLite, no del grafo | Alta |
| B2 | Data leakage en `train.evaluate_model` (scaler global antes de CV) | Alta |
| B3 | `CUTOFF_DATE` hardcodeado a `2025-07-16` — invalida predicciones cuando cambian los datos | Alta |
| B4 | `_TODAY_UTC` congelado al importar `transforms.py` — `dias_hasta_vencimiento` se queda estancado | Alta |
| B5 | `CORS allow_origins=["*"] + allow_credentials=True` — los browsers rechazan requests con credenciales | Alta |
| B6 | README y código del frontend inconsistentes (vanilla vs React+Vite) — el flujo de instalación del README no arranca | Alta |

### 🟧 CRÍTICOS DE PRODUCCIÓN (no bloquean, degradan severamente la solución)

| # | Problema | Severidad |
|---|---|---|
| C1 | `analytics_service._load_all_data` hace full-scan de toda la tabla `nodes` por request | Media-Alta |
| C2 | `predictor.get_prediccion_clientes` reentrena 3 modelos + CV + calibración por request (TTL 5 min) | Media-Alta |
| C3 | `dias_hasta_vencimiento` almacenado como propiedad estática (predict-on-write con un valor que es función del tiempo) | Media-Alta |
| C4 | `PromesaPago.cumplida` es snapshot: pagos recibidos tras la ingesta no actualizan el flag | Media-Alta |
| C5 | `SIGUIENTE` genera N-1 aristas por cliente — a 1 M clientes ≈ 10 M aristas redundantes | Media-Alta |
| C6 | Relación N:M `CUMPLE_PROMESA` con ventana de gracia (3 días) hardcodeada en `transforms.py` | Media |
| C7 | `CalibratedClassifierCV(method="isotonic", cv=...)` sobre ≤ 50 clientes — calibración ruidosa | Media |
| C8 | `_CACHE` en `predictor.py` es un dict global sin lock → doble-entrenamiento bajo concurrencia | Media |
| C9 | Modelo se entrena dentro del request handler — no hay artefacto versionado, no hay job offline | Media |

### 🟨 MENORES (higiene, riesgo latente, documentación)

| # | Problema | Severidad |
|---|---|---|
| M1 | Duplicado `interacciones_clientes 2.json` en raíz (no usado, ensucia el repo) | Baja |
| M2 | Carpeta `frontend/_old_vanilla/` sin uso, shippeada | Baja |
| M3 | Magic numbers: `rfm_recency = 180.0` default, grace `timedelta(days=3)`, umbral z `2.5` | Baja |
| M4 | `_before_cutoff` retorna `True` con timestamp inválido → inclusión silenciosa en features | Baja |
| M5 | `evaluate_model` reutiliza la misma instancia de `StandardScaler` entre modelos | Baja |
| M6 | Tests ML existen pero no hay validación explícita de contratos anti-leakage | Baja |
| M7 | El HTML del enunciado referencia `interacciones_clientes.json` (sin sufijo) pero el zip entregado trae `interacciones_clientes 2.json` | Baja |

---

## 🧠 Causas Raíz (detallado por problema)

### B1 — Graphiti es una fachada; la API lee SQLite

**PROBLEMA:**  `api/services/analytics_service.py` (líneas 28-32) define `DB_PATH` apuntando a `ingesta/local_graph.db` y abre `sqlite3.connect()` directamente. El `GraphitiClient` (en `ingesta/`) tiene fallback a SQLite cuando Graphiti no responde, pero la **API jamás consulta a Graphiti ni a Neo4j**: siempre va a SQLite, incluso cuando Docker levanta los servicios correctamente.

**CAUSA RAÍZ:**  El diseño separa "ingesta → Graphiti" y "API → Graphiti", pero el layer de servicios de la API nunca se conectó al backend del grafo. `graphiti_service.py` existe en `api/services/` pero no es el camino usado por `analytics`, `predictor`, ni `anomalies` — estos importan `analytics_service._load_all_data` que va directo a SQLite. El SQLite pensado como *fallback de ingesta* pasó a ser la **fuente primaria de lectura**.

**IMPACTO:**  Incumple el requerimiento explícito del enunciado ("Implementar la carga de datos a Graphiti usando su API REST" y "Se aprovechan las capacidades de Graphiti" — 40 % de la evaluación). Neo4j + Graphiti en `docker-compose.yml` quedan como infraestructura muerta. Cualquier query Cypher o feature semántica de Graphiti (ej. búsquedas vectoriales, relaciones derivadas) es inalcanzable desde la API. El sistema pierde su razón de ser un grafo.

---

### B2 — Data leakage en `train.evaluate_model`

**PROBLEMA:**  `api/ml/train.py:96` hace `X_s = scaler.fit_transform(X)` antes de `cross_val_predict(model, X_s, y, cv=cv)`. El scaler vio **todos los folds** (incluido el de validación) antes de que se separen los splits.

**CAUSA RAÍZ:**  Confusión conceptual entre "preparar los datos una vez" y "preparar los datos por fold". En `scikit-learn`, toda transformación ajustable (`fit`) debe entrar en un `Pipeline` y pasarse al CV, no aplicarse fuera.

**IMPACTO:**  Las métricas `precision/recall/f1/roc_auc` reportadas están infladas. Al ser 50 clientes con 10 features, la media/std filtrada contamina los folds de validación. Las decisiones tomadas sobre "mejor modelo por ROC-AUC" (`compare_models` línea 180) se basan en métricas sesgadas. Además, `cross_val_score` en la rama de `fold_scores` (línea 223) vuelve a cometer el mismo error.

---

### B3 — `CUTOFF_DATE` hardcodeado

**PROBLEMA:**  `api/ml/features.py:40` fija `CUTOFF_DATE = datetime(2025, 7, 16, tzinfo=timezone.utc)` y `DATA_END_DATE = datetime(2025, 9, 2, tzinfo=timezone.utc)`.

**CAUSA RAÍZ:**  La fecha fue elegida como "día 60 del dataset" sobre la base de metadata del JSON actual (mayo-septiembre 2025). No se deriva dinámicamente de `dataset.metadata.fecha_generacion` ni de los timestamps reales.

**IMPACTO:**  Si los datos cambian (otro período, otro cliente, nuevas cargas), el cutoff queda fuera de rango: todos los registros caerían antes o todos después, `y` colapsa en una sola clase y `build_feature_matrix` devuelve `y=None`, forzando labels heurísticos sin aviso al usuario. El sistema presenta como "temporal_split" una predicción que en realidad es heurística.

---

### B4 — `_TODAY_UTC` congelado al importar `transforms.py`

**PROBLEMA:**  `ingesta/transforms.py:29` captura `_TODAY_UTC = datetime.now(tz=timezone.utc).date()` **a nivel de módulo**. Esta fecha se usa en línea 108 para calcular `dias_hasta_vencimiento`.

**CAUSA RAÍZ:**  Constante de módulo en lugar de función pura. El módulo se importa una vez por proceso Python; si el proceso vive varios días (server long-running), `_TODAY_UTC` queda congelado y las re-ingestas producen valores de `dias_hasta_vencimiento` con respecto al día del *primer import*, no del día actual.

**IMPACTO:**  En un worker de reingesta periódico (cron / Celery), todas las promesas tendrán `dias_hasta_vencimiento` anclado al primer arranque. Datos silenciosamente corruptos → dashboards mienten sobre vencimientos.

---

### B5 — CORS inválido

**PROBLEMA:**  `api/main.py:37-43`: `allow_origins=["*"]` + `allow_credentials=True`.

**CAUSA RAÍZ:**  La spec CORS prohíbe la combinación wildcard + credenciales. Los browsers modernos **ignoran** `Access-Control-Allow-Credentials: true` si `Access-Control-Allow-Origin: *`. El flag `allow_credentials=True` en FastAPI es copy-paste defensivo.

**IMPACTO:**  Cuando el frontend haga requests con cookies / auth (p. ej. al añadir JWT), fallarán silenciosamente en preflight. Además, abierto a cualquier origen es un riesgo de seguridad clásico (CSRF-able si se añade sesión).

---

### B6 — Frontend: README miente sobre la arquitectura

**PROBLEMA:**  `README.md:12` dice "Frontend SPA (vanilla JS + D3.js + Chart.js)" y `README.md:56-58` instruye `cd frontend && python -m http.server 3000`. En realidad `frontend/` contiene `vite.config.js`, `App.jsx`, `main.jsx`, `pages/*.jsx`, `components/*.jsx`, `react-router-dom` como dependencia.

**CAUSA RAÍZ:**  El frontend se refactorizó de vanilla a React (existe `frontend/_old_vanilla/` con la versión antigua aún commiteada) pero el README no se actualizó. La instrucción `python -m http.server 3000` sirve `index.html` literal sin bundlear JSX → el navegador recibe JSX crudo → error.

**IMPACTO:**  Un evaluador siguiendo el README literalmente **no podrá arrancar el frontend**. Penaliza el criterio de "README claro con instrucciones de instalación". Adicionalmente, `_old_vanilla/` añade ruido y puede confundir sobre cuál es el frontend canónico.

---

### C1 — Full scan sobre cada request en `_load_all_data`

**PROBLEMA:**  `api/services/analytics_service.py:54-102` ejecuta 5 queries `SELECT id, properties FROM nodes WHERE label = '…'` cargando en memoria **todos** los `Cliente`, `Interaccion`, `Pago`, `Promesa`, `Agente`. Se invoca desde `get_prediccion_clientes`, `get_anomalias`, `get_estrategias`.

**CAUSA RAÍZ:**  Acoplamiento del pipeline ML a un fetch monolítico "cárgalo todo en Python". No hay paginación, no hay índice por `label`, no hay consulta delta.

**IMPACTO:**  A 50 clientes funciona en ms. A 1 M clientes × ~10 interacciones = ~10 M filas serializadas JSON → minutos por request, OOM fijo sobre un pod de 2 GB. El worker se cae en el primer request de producción.

---

### C2 — Entrenamiento dentro del request handler

**PROBLEMA:**  `api/ml/predictor.py:57` llama `compare_models(X, y_gt)` que corre CV × 3 modelos + `CalibratedClassifierCV` **dentro del request HTTP**. Cache con TTL 300 s (`_CACHE_TTL_SECONDS`).

**CAUSA RAÍZ:**  Ausencia de separación train/inference. El modelo no se persiste; no hay "artifact registry"; el endpoint `/analytics/prediccion` actúa simultáneamente como trigger de entrenamiento.

**IMPACTO:**  Primer request de cada ventana de 5 min paga ~segundos de CPU. Timeouts de HTTP, thundering herd cuando múltiples requests concurrentes pierden cache a la vez (ver también C8).

---

### C3 — Predict-on-write de un valor que es función del tiempo

**PROBLEMA:**  `dias_hasta_vencimiento` se calcula en `ingesta/transforms.py:108` como `(fecha_promesa_date - _TODAY_UTC).days` y se guarda como propiedad del nodo `PromesaPago`. Mañana su valor correcto será `hoy - 1` pero la BD lo mantendrá estable.

**CAUSA RAÍZ:**  El ingeniero confundió "propiedad derivada estática" (ej. `monto_total_plan = cuotas * monto_mensual`) con "propiedad dinámica función del tiempo" (ej. vencimiento). Lo segundo NO debe precomputarse.

**IMPACTO:**  El endpoint `/analytics/promesas-incumplidas` compara contra un campo stale. Un cron nocturno no resuelve el problema de forma elegante — obliga a reingestar. Es exactamente el anti-patrón mencionado por el stakeholder: **predict-on-write donde debería ser compute-on-read**.

---

### C4 — `PromesaPago.cumplida` es snapshot

**PROBLEMA:**  `transforms.py` (Pass 2, líneas 158-171) calcula `cumplida` una sola vez. Si llega un pago nuevo tras la ingesta, no reactiva la lógica.

**CAUSA RAÍZ:**  No hay evento, trigger, ni invalidación. Toda la inferencia vive en la ingesta batch.

**IMPACTO:**  KPI de "promesas cumplidas" mentira en cualquier escenario donde pagos y ingestas no sean atómicos. Operativo incorrecto para reportes ejecutivos.

---

### C5 — `SIGUIENTE` explota a 1 M clientes

**PROBLEMA:**  Por cada cliente con N interacciones se emiten N-1 aristas `SIGUIENTE` (`transforms.py:316-329`). A 1 M clientes × 10 interacciones promedio = **~10 M aristas** solo para esta relación.

**CAUSA RAÍZ:**  Se modeló la cadena temporal como lista enlazada explícita en lugar de confiar en un índice sobre `Interaccion(cliente_id, timestamp)`.

**IMPACTO:**  Neo4j puede con eso, pero es deuda innecesaria. Escrituras por ingesta se vuelven 10× más caras; queries tipo "timeline del cliente" podrían resolverse con un `ORDER BY timestamp` + índice sin necesidad de traversar aristas.

---

### C6 — Ventana de gracia hardcodeada

**PROBLEMA:**  `transforms.py:163` y `:304`: `timedelta(days=3)`. Es una regla de negocio crítica (¿cuándo una promesa vencida se considera cumplida tardíamente?).

**CAUSA RAÍZ:**  Constante in-place sin parámetro ni configuración.

**IMPACTO:**  Si negocio cambia la política (p. ej. 7 días para hipotecas, 0 días para tarjetas), requiere tocar código, release y reingesta. Rigidez operativa.

---

### C7 — Calibración isotónica con n=50

**PROBLEMA:**  `train.py:193`: `CalibratedClassifierCV(gb_base, method="isotonic", cv=n_cv)`. Isotonic regression es no-paramétrica y necesita muchas muestras.

**CAUSA RAÍZ:**  Copia de receta de documentación sin considerar el tamaño muestral. Con 50 clientes + CV estratificada, cada fold de calibración tiene ~10 puntos.

**IMPACTO:**  Probabilidades calibradas ruidosas; en un conjunto tan pequeño, isotonic puede sobreajustar el monotonic mapping y empeorar la métrica frente a sigmoid (Platt). Para n<1000, sigmoid es la opción segura.

---

### C8 — `_CACHE` sin lock bajo concurrencia

**PROBLEMA:**  `predictor.py:24` — `_CACHE: dict[str, Any] = {}`. FastAPI maneja requests concurrentes en threads (o event loop con `run_in_threadpool` para código bloqueante como sklearn). Si dos requests llegan con cache vacío, ambos disparan `compare_models`.

**CAUSA RAÍZ:**  Cache naive sin lock ni singleflight/coalescing.

**IMPACTO:**  Doble trabajo CPU, potencial tormenta al expirar TTL, métricas de latencia p95 erráticas.

---

### C9 — Modelo no persistido

**PROBLEMA:**  El mejor modelo vive en memoria dentro del dict `_CACHE`. No hay `joblib.dump`, ni `model_registry` real (existe `api/ml/model_registry.py` pero auditar su rol excede el alcance — por el nombre y el hecho de que `predictor` no lo usa, parece muerto).

**CAUSA RAÍZ:**  Falta de separación entre training pipeline y serving.

**IMPACTO:**  Reinicio del pod = reentrenamiento en frío. Imposibilita trazabilidad (qué modelo sirvió qué predicción), A/B testing, rollback, auditoría regulatoria.

---

### M1-M7 — Problemas menores

- **M1/M7**: `interacciones_clientes 2.json` en raíz es copia del archivo en `data/` con nombre corrupto (sufijo " 2" típico de descarga duplicada). Nadie lo lee. Confunde.
- **M2**: `frontend/_old_vanilla/` es cementerio commiteado.
- **M3**: Magic numbers sin constantes nombradas:  `180.0`, `days=3`, `z > 2.5`, `MIN_LLAMADAS = 5`.
- **M4**: `features._before_cutoff` retorna `True` (incluir) si no parsea el timestamp. Silencia errores de datos.
- **M5**: `evaluate_model` comparte `scaler` entre modelos — no rompe nada pero ilustra el problema B2.
- **M6**: No hay tests que verifiquen ausencia de data leakage (ej. comparar métricas CV con y sin `Pipeline`).

---

## 🔧 Soluciones Conceptuales

> Regla: sin reescrituras extensas. Solo se indica **qué cambiar** y **enfoque técnico**.

### B1 — Usar Graphiti de verdad
- Mover toda query de lectura a `api/services/graphiti_service.py`, que debería hablar HTTP con Graphiti (o Bolt con Neo4j usando el driver oficial).
- `_load_all_data` pasa a ser un conjunto de queries Cypher concretas por endpoint: `/clientes/{id}/timeline` → `MATCH (c:Cliente {id:$id})-[:TIENE_INTERACCION]->(i) RETURN i ORDER BY i.timestamp`.
- Eliminar dependencia SQLite de la API (dejar SQLite solo como testing store o modo desarrollo aislado, no como backend de producción).

### B2 — Eliminar data leakage
- Reemplazar `scaler.fit_transform(X)` + `cross_val_predict(model, X_s, …)` por:

```python
from sklearn.pipeline import make_pipeline
pipe = make_pipeline(StandardScaler(), model)
y_pred = cross_val_predict(pipe, X, y, cv=cv)
```

- Lo mismo en `cross_val_score` (línea 223).

### B3 — `CUTOFF_DATE` derivado del dataset
- Derivarlo de `dataset.metadata.periodo` o computarlo como "percentil 66 de los timestamps".
- Exponer como parámetro de `build_feature_matrix(data, cutoff_date=...)` y llamarlo desde el caller con un valor **calculado al arranque del servicio**, no hardcoded.

### B4 — `_TODAY_UTC` como función
- Eliminar la constante de módulo. Calcular `datetime.now(tz=timezone.utc).date()` **dentro** de `transform()` (o dentro de cada uso).

### B5 — CORS correcto
- Listar orígenes explícitos: `allow_origins=["http://localhost:3000", "https://tu-dominio.com"]`.
- Si se quiere wildcard, quitar `allow_credentials=True`.

### B6 — Alinear README con frontend real
- Actualizar pasos de instalación del frontend: `cd frontend && bun install && bun run dev` (o `npm ci && npm run dev`).
- Eliminar `frontend/_old_vanilla/`.
- Documentar que el build productivo se sirve vía nginx (ya existe `nginx.conf`).

### C1 — Sustituir full-scan por queries específicas
- Cada endpoint debería pedir solo lo que necesita y al grafo, con paginación (`SKIP / LIMIT`) e índices de PLAN.md § 1.3 (falta verificar que realmente se crean en la ingesta).
- El pipeline ML puede mantener un fetch batch, pero debería ejecutarse **fuera** del request (ver C2).

### C2/C9 — Separar train del serve
- Job offline (cron / Airflow / Celery beat) entrena, valida, y **persiste** el modelo con `joblib.dump` a una ruta versionada (`models/2026-04-16T12:00:00Z/model.pkl`).
- La API solo **carga** un modelo ya entrenado al startup (`on_event("startup")`) y lo sirve.
- `model_registry.py` debería ser el único punto de carga; auditar y completar.

### C3 — `dias_hasta_vencimiento` on-read
- Eliminar la propiedad estática del nodo.
- Calcularla en el endpoint: `dias_hasta_vencimiento = (promesa.fecha_promesa - today).days`.
- O exponerla como view/propiedad derivada en Neo4j (`APOC`, expresión dinámica).

### C4 — `cumplida` dinámica o event-driven
- Opción A (simple): on-read, ejecutar el match `pago ↔ promesa` en query.
- Opción B (escalable): trigger APOC en Neo4j que al insertar un `Pago` busca promesas abiertas del mismo cliente y crea `CUMPLE_PROMESA`.
- Opción C: idempotente "job de reconciliación" cada N horas.

### C5 — Sustituir `SIGUIENTE` por índice
- Eliminar la relación.
- Todas las queries "timeline" ya ordenan por `timestamp` (índice de PLAN.md).
- Si se necesita "anterior" / "siguiente" explícito, exponerlo como función en Cypher con `ORDER BY timestamp LIMIT 1`.

### C6 — Regla de negocio configurable
- Extraer `GRACE_DAYS` a `.env` y pasarlo a `transforms.transform(..., grace_days=...)`.
- Considerar grace diferenciado por `tipo_deuda` (tabla de políticas).

### C7 — Calibración sigmoid para n pequeño
- `method="sigmoid"` cuando `n < 1000`; `isotonic` solo con muestras grandes. Decisión automatizable.

### C8 — Lock o singleflight
- `threading.Lock` simple al entrar a `get_prediccion_clientes` si cache es None.
- O mejor: mover el entrenamiento offline (C2/C9) y ya no se necesita.

### Menores
- **M1/M2/M7**: borrar `interacciones_clientes 2.json` (raíz) y `frontend/_old_vanilla/`.
- **M3**: convertir magic numbers en constantes nombradas en el tope del módulo.
- **M4**: log warning y excluir del cómputo cuando `_parse_ts` falle.
- **M6**: test que verifique `Pipeline-CV ROC-AUC ≤ non-Pipeline ROC-AUC` como regresión anti-leak.

---

## 🛡️ Prevención a Futuro

### Validaciones (ingesta)
- **Schema contract**: Pydantic + `Strict` en `models.py` debe fallar ante tipos inesperados (no convertir silenciosamente).
- **Assertion de invariantes post-transform**: `assert all(p.cumplida in (True, False) for p in promesas)`; `assert len(interacciones) == n_raw`.
- **Validación de cobertura temporal**: antes de ingestar, comprobar que `min_ts < CUTOFF_DATE < max_ts` → fail-fast si el cutoff no parte el dataset.

### Testing
- **Anti data-leakage test**: entrenar con `Pipeline(scaler, model)` y con `scaler.fit_transform + model`; las métricas deben bajar en el primer caso. Si no bajan, hay leakage en otro lado.
- **Snapshot tests de endpoints**: fixtures JSON determinísticas + asserts estructurales (no numéricos exactos por ruido de CV).
- **Integration test con Graphiti real**: docker-compose up de prueba, ingestar mini-dataset, golpear `/analytics/dashboard`, comparar contra valores esperados.
- **Property tests**: Hypothesis para `_before_cutoff`, `transform`, asegurando que re-ingestas idempotentes dan el mismo grafo.

### Patrones de diseño
- **Repository pattern** para acceso al grafo: `ClienteRepository`, `InteraccionRepository`. Oculta si el backend es Neo4j o SQLite detrás de una interfaz. Hoy ambos conviven mezclados.
- **Event-driven updates**: cada `Pago` emite evento → handler actualiza `CUMPLE_PROMESA`. Desacopla ingesta batch de mantenimiento de estado.
- **CQRS lite**: write-side (ingesta normalizada en grafo) / read-side (proyecciones denormalizadas para dashboards y ML).

### Reglas de arquitectura
- **Ningún modelo se entrena dentro de un handler HTTP**. Training = offline job. Serving = load + predict.
- **Ninguna fecha relativa al "ahora" se almacena como entero estático**. Si un campo depende de la fecha actual, se calcula on-read o se recomputa diariamente con timestamp explícito.
- **Ninguna regla de negocio se hardcodea en transform**. Toda constante operativa (días de gracia, umbral z, etc.) se parametriza vía `.env` o config centralizado.
- **Toda transformación ajustable entra en un `Pipeline`** que entra al CV — regla no negociable.

---

## 🏗️ Recomendaciones de Arquitectura

1. **Capas limpias**:
   ```
   routers/           → HTTP only, sin lógica de dominio
   services/          → orquestación, llaman a repositories y ml
   repositories/      → único punto de acceso a Graphiti/Neo4j
   ml/                → features, train, inference — puro, sin I/O de DB
   ingesta/           → pipeline de hidratación offline
   ```
   Hoy `analytics_service.py` mezcla capa de datos (SQL directo) con orquestación.

2. **Model serving aparte**: un subproceso `api/ml/serve.py` que carga el modelo `joblib` al startup y lo expone vía dependency injection de FastAPI (`Depends`).

3. **Feature store ligero**: persistir la matriz `X` pre-computada y versionada, para que inference no recalcule features desde cero por request.

4. **Graphiti como fuente única**: eliminar el SQLite de producción. Si se quiere modo desarrollo sin Neo4j, envolver con un `FakeGraphitiClient` en-memoria detrás del mismo interface del repository.

5. **Observabilidad**: agregar logging estructurado (`structlog`), métricas (Prometheus: latencia por endpoint, errores, cache hit rate), trazas distribuidas (OpenTelemetry → Jaeger) — hoy no hay nada de esto.

6. **Config management**: `pydantic-settings` ya está siendo usado (`api/config.py`) — extenderlo para todas las constantes de negocio hoy hardcoded.

---

## ⚡ Consideraciones de Escalabilidad (100 k → 1 M+ clientes)

### Lo que **no escala** tal cual está

| Componente | Problema | Impacto @ 1 M |
|---|---|---|
| `_load_all_data()` | full-scan de 5 labels, JSON parse por fila | OOM, latencia > 5 min |
| `predictor` | 3 modelos × CV × calibración en cada miss de cache | CPU pegado, timeouts |
| `SIGUIENTE` | N-1 aristas por cliente | 10 M aristas extra; ingesta 10× más lenta |
| `dias_hasta_vencimiento` | recalculable diariamente sobre 100 k+ promesas | reingesta nocturna pesada |
| `/grafo/nodos` + `/grafo/relaciones` | devuelven todo (o limit=200, arbitrario) | inútil a escala; visualización colapsa |
| KPIs del dashboard | recalculados por request | pegan Neo4j cada carga del dashboard |

### Qué debería ser "predict-on-write" (precomputado)
- `tasa_cumplimiento`, `total_pagado`, `monto_pendiente` por cliente (agregados)
- `tasa_promesa`, `tasa_pago_inmediato` por agente
- KPIs del dashboard (cacheables en Redis con invalidación por evento de ingesta) — TTL ≥ 1 h.
- Feature matrix para ML (guardada como parquet versionado por día).
- Clusters de segmentación (no tiene sentido recalcular KMeans por request).

### Qué debería ser "compute-on-read" (dinámico)
- `dias_hasta_vencimiento`, `promesa_vencida_hoy` — función de la fecha actual.
- `cumplida` si no se resuelve event-driven.
- Cualquier filtro temporal que el usuario elija en el dashboard.

### Patrones específicos recomendados
1. **Batch materialized views** en Neo4j: `MATCH (c:Cliente) … SET c.total_pagado = …`. Corren nocturnos.
2. **Incremental training**: modelo ML se reentrena semanalmente/nocturno sobre features parquet. Un día completo cabe en un job de 30 min.
3. **Sharding temporal** de `Interaccion`: partición por `YYYY-MM`. Permite purgar antiguos y queries más rápidas.
4. **Redis cache** con `cache-aside` para dashboard / predicciones por cliente. TTL de 5-15 min.
5. **Paginación real** en `/clientes`, `/grafo/nodos`, `/grafo/relaciones`: `cursor`-based, no `offset` (degrada O(n) en Neo4j).
6. **CDN/edge caching** del frontend React build (ya hay `nginx.conf` — bien).
7. **Backpressure / rate limiting** en endpoints ML (token bucket por IP).

### Métricas de salud que deberían existir antes de escalar
- Latencia p95/p99 por endpoint.
- Tamaño del grafo por label, crecimiento diario.
- % cache hit para dashboard y predicciones.
- Tiempo del job de entrenamiento; drift del modelo (PSI entre ejecuciones).
- Invariantes de consistencia: `sum(Pago.monto) == sum(Cliente.total_pagado)`.

---

## ✅ Checklist Accionable para el Modelo Implementador

Prioridad descendente; bloques B* son **must-do antes de declarar production-ready**:

1. [ ] **B2** — envolver scaler+modelo en `Pipeline` dentro de CV en `api/ml/train.py`.
2. [ ] **B4** — quitar `_TODAY_UTC` como constante de módulo en `ingesta/transforms.py`.
3. [ ] **B3** — derivar `CUTOFF_DATE` de los datos, no hardcodear.
4. [ ] **B1** — cablear `api/services/graphiti_service.py` como fuente real de la API; aislar SQLite a fallback de desarrollo.
5. [ ] **B5** — arreglar CORS: listar orígenes o quitar `allow_credentials`.
6. [ ] **B6** — actualizar README al flujo React/Vite real; borrar `_old_vanilla/`.
7. [ ] **C2/C9** — mover entrenamiento ML a job offline; persistir modelo; servir via `Depends`.
8. [ ] **C3** — calcular `dias_hasta_vencimiento` on-read; eliminar la propiedad estática.
9. [ ] **C1** — reemplazar `_load_all_data` por queries específicas + paginación.
10. [ ] **C7** — `method="sigmoid"` para n<1000.
11. [ ] **C6** — `GRACE_DAYS` a `.env`.
12. [ ] **C5** — decidir si `SIGUIENTE` se elimina o se documenta su trade-off.
13. [ ] **M1/M2/M7** — borrar `interacciones_clientes 2.json` (raíz) y `_old_vanilla/`.
14. [ ] **M3** — constantes nombradas para magic numbers.
15. [ ] **M6** — añadir test anti-leakage en `api/tests/test_ml/`.

---

*Fin del documento. Revisión realizada bajo el estándar "sistemas financieros / cobranza crítica".*
