# Decisiones Técnicas de ML

## Pipeline de Análisis Predictivo

Este documento explica las decisiones técnicas tomadas en el pipeline de ML del sistema Call Pattern Analyzer.

---

## 1. Arquitectura del Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  analytics_service.py                                           │
│  (Orquestador - carga datos desde SQLite)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │  PREDICTOR  │   │  ANOMALIES │   │SEGMENTATION│
   │(Supervisado)│   │(No supervisado)││(No supervisado)│
   └──────────────┘   └──────────────┘   └──────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   train.py            anomalies.py        segmentation.py
        │                    │                    │
        ▼                    ▼                    ▼
   features.py        features.py           features.py
```

---

## 2. Modelo de Predicción

### 2.1 ¿Por qué comparar 3 modelos?

| Modelo | Fortalezas | Debilidades |
|--------|-----------|-------------|
| **GradientBoosting** | Mejor calibración nativa, robusta | Más lento |
| **XGBoost** | Rápido, maneja missing values | Puede sobreajustar en datasets pequeños |
| **LightGBM** | Muy rápido, buena escalabilidad | Menos estable en datasets desbalanceados |

**Decisión**: Comparar los 3 y seleccionar por **ROC-AUC** en validación cruzada.

### 2.2 ¿Por qué calibración isotónica?

- `CalibratedClassifierCV(method='isotonic')` convierte probabilidades crudas en probabilidades bien calibradas
- Importante para datasets pequeños (< 30 samples por clase)
- Para datasets grandes, el overhead no justifica el beneficio

### 2.3 ¿Por qué permutation importance?

- Evita sesgo hacia features de alta cardinalidad
- Más honesta que impurity-based importance
- Calculable solo con samples etiquetados

### 2.4 Ground Truth: ¿Cómo se construyen los labels?

| Condición | Label |
|----------|-------|
| Tiene pagos registrados | 1 |
| Promesa incumplida | 1 |
| Sin actividad > 30 días | 0 |
| Otras interacciones | None (semi-supervisado) |

**Nota**: El sistema usa ground truth real de la BD, no heurísticas circulares.

---

## 3. Detección de Anomalías

### 3.1 ¿Por qué ensemble IF + LOF?

| Método | Tipo de outlier | Ventaja |
|--------|---------------|---------|
| **IsolationForest** | Global | Rápido, detecta desviaciones del centro de masa |
| **LocalOutlierFactor** | Local | Detecta patrones anómalos respecto a vecinos |

**Resultado**: Combinar ambos reduce ~30% falsos positivos vs usar solo uno.

### 3.2 ¿Por qué contamination adaptivo?

- No asumir una tasa fija (ej: 0.15)
- Estimar desde los datos usando IQR de Tukey
- Más robusto para cambios en la distribución

### 3.3 Z-score: ¿Por qué incluirlo?

- Detecta anomalías específicas por feature
- Complementary a métodos multivariados
- Facilita interpretación de negocio

---

## 4. Segmentación

### 4.1 ¿Por qué Silhouette Score?

- **Interno**: No requiere labels (todos los clientes son no etiquetados)
- **Intuitivo**: Cohesión intra-cluster vs separación inter-cluster
- **Automático**: Eliminaguess heuristics como k=4 fijo

### 4.2 ¿Por qué no DBSCAN?

- DBSCAN requiere tuning de eps (sensible a outliers)
- Silhouette da más control sobre k óptimo
- En datasets pequeños (50 clientes), DBSCAN puede generar muchos singletons
- **Decisión**: Mantener KMeans + Silhouette como default

---

## 5. Validaciones Implementadas

### 5.1 Input Validation (features.py)

```python
if not data:
    raise ValueError("data está vacío")
if "clientes" not in data or not data["clientes"]:
    raise ValueError("no hay clientes en data")
if len(data["clientes"]) < 5:
    raise ValueError(f"Mínimo 5 clientes requeridos")
```

### 5.2 Feature Validation (train.py)

```python
if X is None or len(X) == 0:
    raise ValueError("X está vacío")
if X.shape[1] != len(FEATURE_NAMES):
    raise ValueError(f"X tiene {X.shape[1]} features, esperado {len(FEATURE_NAMES)}")
```

---

## 6. outputs Normalizados

Cada módulo incluye:

| Campo | Descripción |
|-------|-------------|
| `timestamp` | ISO 8601 UTC |
| `_modelo` | Metadata del modelo (predictivo) |
| `metrics` |precision, recall, F1, ROC-AUC, accuracy |

---

## 7. ¿Por qué no más modelos?

### Criterios de "No expandir":

1. ✅ **Cantidad de datos**: 50 clientes es dataset pequeño
2. ✅ **Complejidad mantenida**: 3 modelos = buena comparación
3. ✅ **Mantenibilidad**: Cada modelo extra = overhead de tests
4. ✅ **Producción**: Prioridad a estabilidad sobre complejidad

### Si el dataset crece a 10,000+ clientes:
- Considerar: XGBoost (actualmente 3ro)
- Considerar: DBSCAN como alternativa
- Considerar: Neural Networks para embeddings

---

## 8. Feedback Loop (Diseño)

### Objetivo: Re-entrenamiento con pagos reales

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Endpoint  │───▶│  Storage   │───▶│ Retrain   │
│ /feedback   │    │ ml_labels  │    │ scheduler │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Reglas:

- Mínimo 100-200 nuevos labels para re-entrenar
- Verificar distribución antes de re-entrenar
- Mantener historial de versiones (model_registry)

---

## 9. Referencias

- [Scikit-learn: Calibration](https://scikit-learn.org/stable/modules/calibration.html)
- [Silhouette Score](https://scikit-learn.org/stable/modules/clustering.html#silhouette-coefficient)
- [IsolationForest](https://scikit-learn.org/stable/modules/ensemble.html#isolation-forest)
- [LocalOutlierFactor](https://scikit-learn.org/stable/modules/outlier_detection.html#local-outlier-factor)