# Agente 3 — Frontend Web (Visualización)

## Contexto
Eres el agente de frontend de un sistema de análisis de cobros.
Tu trabajo es crear una SPA (Single Page Application) en HTML/CSS/JS vanilla
que consuma la API REST del sistema y presente tres vistas: Dashboard, Cliente Individual y Grafo.
No tienes contexto de ninguna sesión previa. Todo lo que necesitas está en disco.

---

## Inputs (verificar existencia antes de ejecutar)

```
PLAN.md                 ← endpoints disponibles, estructura de carpetas
api/api_verificada.json ← confirma que la API está disponible
```

**Validación de inputs — DETENTE si alguno falla:**
1. `PLAN.md` existe
2. `api/api_verificada.json` existe y tiene `"status": "ok"`
3. La API responde en la URL indicada en `api_verificada.json`: `GET {url_base}/health` → `{"status": "ok"}`

---

## Responsabilidad

Crear el módulo `frontend/` completo: una SPA sin framework de build que funcione
abriendo `frontend/index.html` directamente en el browser (o con `python -m http.server`).

---

## Las Tres Vistas Requeridas

### Vista 1 — Dashboard General (`#/dashboard`)

**KPI Cards** (4 cards en fila):
- Total Deuda Inicial (USD)
- Total Recuperado (USD)
- Tasa de Recuperación (%)
- Promesas Cumplidas / Total Promesas

**Gráfico 1 — Distribución de Tipos de Deuda** (donut chart con Chart.js):
- Sectores: `hipoteca`, `tarjeta_credito`, `prestamo_personal`, `auto`
- Leyenda con conteo y porcentaje

**Gráfico 2 — Actividad por Día** (line chart con Chart.js):
- Eje X: fecha (últimos 90 días)
- Eje Y: número de interacciones
- Dos líneas: "Llamadas" y "Pagos"

**Tabla — Promesas Incumplidas Recientes** (top 10):
- Columnas: Cliente, Monto Prometido, Fecha Promesa, Días Vencida
- Ordenada por días vencida (descendente)

**Datos de**: `GET /analytics/dashboard` + `GET /analytics/promesas-incumplidas`

---

### Vista 2 — Cliente Individual (`#/clientes/:id`)

**Header del cliente**:
- Nombre, teléfono, tipo de deuda
- Barra de progreso: `total_pagado / monto_deuda_inicial`
- Badge de estado: "Al día" / "Con deuda pendiente" / "Promesa activa"

**Timeline interactivo**:
- Lista vertical cronológica de todas las interacciones del cliente
- Cada item muestra: fecha, tipo (con icono), resultado, sentimiento, monto (si aplica)
- Iconos diferenciados por tipo: 📞 llamada, 📧 email, 💬 sms, 💰 pago
- Color por sentimiento: verde=cooperativo, amarillo=neutral, naranja=frustrado, rojo=hostil
- Click en un item expande detalles (monto_prometido, agente, duración, etc.)

**Panel lateral — Métricas del cliente**:
- Total llamadas recibidas vs realizadas
- Número de promesas hechas vs cumplidas
- Último contacto (fecha + tipo)
- Plan de pago activo (si existe): cuotas, monto mensual

**Selector de clientes** (dropdown o buscador):
- Permite cambiar de cliente sin recargar la página
- Muestra nombre + tipo de deuda en el listado

**Datos de**: `GET /clientes` (listado) + `GET /clientes/{id}/timeline`

---

### Vista 3 — Explorador de Grafo (`#/grafo`)

**Visualización force-directed con D3.js v7**:
- Nodos por tipo con colores distintos:
  - Cliente → azul oscuro `#1e3a5f`
  - Agente → verde `#2d6a4f`
  - Interaccion → gris `#6c757d`
  - PromesaPago → naranja `#e76f51`
  - Pago → verde claro `#52b788`
  - PlanPago → púrpura `#7b2d8b`
- Tamaño de nodo proporcional al número de conexiones
- Etiqueta visible en hover (tooltip con propiedades clave)
- Zoom y pan con rueda del mouse
- Click en nodo: panel lateral con todas sus propiedades
- Aristas con color por tipo de relación

**Panel de filtros** (sidebar izquierdo):
- Checkboxes para mostrar/ocultar tipos de nodo
- Checkboxes para mostrar/ocultar tipos de relación
- Selector de cliente (carga subgrafo del cliente seleccionado)
- Slider "profundidad": 1 = solo conexiones directas, 2 = 2 saltos, 3 = 3 saltos
- Botón "Resetear filtros"

**Controles del grafo**:
- Botón "Centrar" (resetea zoom)
- Botón "Congelar/Liberar" (pausa/reanuda la simulación de fuerzas)
- Contador de nodos y aristas visibles

**Datos de**: `GET /grafo/nodos` + `GET /grafo/relaciones`

---

## Estructura de Archivos a Crear

```
frontend/
├── index.html              ← SPA shell con navegación entre vistas
├── src/
│   ├── api.js              ← cliente HTTP (fetch wrapper con base URL configurable)
│   ├── router.js           ← hash-based router (#/dashboard, #/clientes/:id, #/grafo)
│   ├── views/
│   │   ├── Dashboard.js    ← Vista 1
│   │   ├── ClienteDetalle.js ← Vista 2
│   │   └── GrafoViewer.js  ← Vista 3
│   └── components/
│       ├── KpiCard.js
│       ├── Timeline.js
│       └── GrafoD3.js      ← componente D3.js reutilizable
├── styles/
│   └── main.css
└── package.json            ← solo para documentar dependencias CDN usadas
```

### CDN a usar en `index.html` (no npm):
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script src="https://d3js.org/d3.v7.min.js"></script>
```

### `frontend/src/api.js` debe:
- Leer `API_BASE_URL` desde `window.API_CONFIG.baseUrl` (configurable sin rebuild)
- Exponer funciones: `getClientes()`, `getClienteTimeline(id)`, `getDashboard()`,
  `getPromesasIncumplidas()`, `getMejoresHorarios()`, `getGrafoNodos(tipos, limite)`, `getGrafoRelaciones(params)`
- Manejar errores de red con mensaje amigable en consola

### `frontend/index.html` debe incluir:
```html
<script>
  window.API_CONFIG = { baseUrl: "http://localhost:8001" };
</script>
```
(configurable sin recompilar)

---

## Diseño Visual

- Paleta: fondo blanco `#ffffff`, texto `#212529`, primario `#0d6efd`, bordes `#dee2e6`
- Tipografía: sistema (`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`)
- Layout: sidebar de navegación izquierda (200px) + área principal
- Responsive: funciona en 1024px+
- No usar frameworks CSS — CSS vanilla con variables `--color-*`

---

## Criterio de Éxito

El frontend termina **correctamente** cuando:

1. `frontend/index.html` abre en browser sin errores en consola
2. Dashboard carga KPIs con valores numéricos reales (no "0" ni "NaN")
3. Gráfico de distribución de deuda muestra los 4 tipos
4. Vista de Cliente Individual carga el timeline de `cliente_000` con al menos 5 items
5. Explorador de Grafo renderiza al menos 20 nodos conectados
6. Los filtros del Grafo (mostrar/ocultar tipos) funcionan sin recargar la página
7. La navegación entre las 3 vistas funciona sin recarga (hash routing)

Escribe `frontend/frontend_verificado.json`:
```json
{
  "status": "ok",
  "vistas_implementadas": ["dashboard", "cliente_detalle", "grafo"],
  "dependencias_cdn": ["chart.js@4", "d3.v7"]
}
```

---

## Cómo Ejecutar

```bash
# Opción 1 — abrir directamente
open frontend/index.html

# Opción 2 — servidor local (evita problemas de CORS con módulos ES)
cd frontend
python -m http.server 3000
# Luego abrir http://localhost:3000
```

---

## Notas de Implementación

- Usar módulos ES (`type="module"`) para separar archivos JS sin bundler
- El router hash-based evita problemas de server-side routing al servir archivos estáticos
- Para el grafo D3.js: limitar a 200 nodos máximo para rendimiento en browser
- Los tooltips del grafo deben mostrarse al hacer hover, no al hacer click
- En la Vista de Cliente, el dropdown de clientes debe ser buscable (filtro por nombre)
- Estado de la app en memoria (no localStorage) — cada recarga trae datos frescos
