/**
 * GrafoViewer.js — Graph Explorer view with D3.js force simulation
 */

import { getGrafoNodos, getGrafoRelaciones, getClientes } from '../api.js';
import { renderGrafoD3, NODE_COLORS } from '../components/GrafoD3.js';

// ----------------------------------------------------------------
// State
// ----------------------------------------------------------------
let graphControls = null;
let allClientes   = [];

const ALL_NODE_TYPES = ['Cliente', 'Agente', 'Interaccion', 'PromesaPago', 'Pago', 'PlanPago'];
const ALL_REL_TYPES  = [
  'TIENE_INTERACCION', 'CONDUJO', 'GENERO_PROMESA', 'PROMESA_DE',
  'GENERO_PAGO', 'PAGO_DE', 'GENERO_PLAN', 'PLAN_DE',
  'CUMPLE_PROMESA', 'SIGUIENTE',
];

const REL_LABELS = {
  TIENE_INTERACCION: 'Tiene Interacción',
  CONDUJO:           'Condujo',
  GENERO_PROMESA:    'Generó Promesa',
  PROMESA_DE:        'Promesa de',
  GENERO_PAGO:       'Generó Pago',
  PAGO_DE:           'Pago de',
  GENERO_PLAN:       'Generó Plan',
  PLAN_DE:           'Plan de',
  CUMPLE_PROMESA:    'Cumple Promesa',
  SIGUIENTE:         'Siguiente',
};

// ----------------------------------------------------------------
// Main render
// ----------------------------------------------------------------
export async function renderGrafoViewer() {
  const container = document.getElementById('view-container');
  container.style.padding = '0';

  container.innerHTML = `
    <div class="grafo-layout" style="height:calc(100vh - 0px);margin:0">

      <!-- Left Filter Sidebar -->
      <div class="grafo-sidebar card" style="padding:16px;overflow-y:auto">
        <div style="font-weight:700;font-size:15px;margin-bottom:16px">🔽 Filtros</div>

        <!-- Node Types -->
        <div class="filter-section">
          <div class="filter-title">Tipos de Nodo</div>
          ${ALL_NODE_TYPES.map(t => `
            <label class="filter-checkbox">
              <input type="checkbox" class="node-type-cb" value="${t}" checked />
              <span class="node-color-dot" style="background:${NODE_COLORS[t] ?? '#adb5bd'}"></span>
              <span>${t}</span>
            </label>
          `).join('')}
        </div>

        <!-- Relationship Types -->
        <div class="filter-section">
          <div class="filter-title">Tipos de Relación</div>
          ${ALL_REL_TYPES.map(t => `
            <label class="filter-checkbox">
              <input type="checkbox" class="rel-type-cb" value="${t}" checked />
              <span>${REL_LABELS[t] ?? t}</span>
            </label>
          `).join('')}
        </div>

        <!-- Client Filter -->
        <div class="filter-section">
          <div class="filter-title">Filtrar por Cliente</div>
          <select id="grafo-client-select" style="width:100%;padding:6px 8px;border:1px solid #dee2e6;border-radius:6px;font-size:13px">
            <option value="">Todos los clientes</option>
          </select>
        </div>

        <!-- Depth Slider -->
        <div class="filter-section">
          <div class="filter-title">Profundidad: <strong id="depth-val">2</strong></div>
          <input type="range" id="depth-slider" class="depth-slider" min="1" max="3" value="2" />
          <div style="display:flex;justify-content:space-between;font-size:11px;color:#adb5bd">
            <span>1</span><span>2</span><span>3</span>
          </div>
        </div>

        <button id="apply-filters-btn" class="btn btn-primary" style="width:100%">
          Aplicar Filtros
        </button>
      </div>

      <!-- Graph Canvas -->
      <div class="grafo-main">
        <!-- Loading overlay -->
        <div class="grafo-loading" id="grafo-loading">
          <div class="spinner" style="width:48px;height:48px;border-width:4px"></div>
          <span>Cargando grafo...</span>
        </div>

        <!-- Controls -->
        <div class="grafo-controls">
          <button id="center-btn" class="btn btn-sm btn-outline">⊕ Centrar</button>
          <button id="freeze-btn" class="btn btn-sm btn-outline">❄️ Congelar</button>
          <button id="reset-zoom-btn" class="btn btn-sm btn-outline">🔍 Reset</button>
        </div>

        <!-- SVG -->
        <svg id="grafo-svg" class="grafo-canvas"></svg>

        <!-- Counters -->
        <div class="grafo-counters">
          <span class="counter-badge" id="node-count-badge">Nodos: —</span>
          <span class="counter-badge" id="edge-count-badge">Aristas: —</span>
        </div>
      </div>

      <!-- Right Info Panel -->
      <div class="grafo-info-panel">
        <div class="card" style="margin-bottom:0;height:100%">
          <div class="card-header">Información del Nodo</div>
          <div class="card-body" id="node-info-panel">
            <div class="empty-state" style="min-height:200px">
              <div class="empty-icon">🖱️</div>
              <p style="font-size:13px">Haz clic en un nodo para ver sus propiedades</p>
            </div>
          </div>
        </div>

        <!-- Legend -->
        <div class="card" style="margin-top:16px">
          <div class="card-header">Leyenda</div>
          <div class="card-body" style="padding:12px 16px">
            ${ALL_NODE_TYPES.map(t => `
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:13px">
                <span style="width:14px;height:14px;border-radius:50%;background:${NODE_COLORS[t]};display:inline-block;flex-shrink:0"></span>
                <span>${t}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    </div>
  `;

  // Load clients for the selector
  try {
    const res = await getClientes();
    allClientes = Array.isArray(res) ? res : (res?.clientes ?? res?.data ?? []);
    populateClientSelect();
  } catch { /* ignore, clients selector is optional */ }

  // Depth slider label
  const depthSlider = document.getElementById('depth-slider');
  const depthVal    = document.getElementById('depth-val');
  depthSlider.addEventListener('input', () => { depthVal.textContent = depthSlider.value; });

  // Apply filters
  document.getElementById('apply-filters-btn').addEventListener('click', () => loadGraph());

  // Initial graph load
  await loadGraph();

  // Return cleanup
  return () => {
    if (graphControls) { try { graphControls.destroy(); } catch {} }
    container.style.padding = '24px';
    // Remove d3 tooltip if present
    const tip = document.querySelector('.d3-tooltip');
    if (tip) tip.remove();
  };
}

// ----------------------------------------------------------------
// Load graph data and render
// ----------------------------------------------------------------
async function loadGraph() {
  const loadingEl = document.getElementById('grafo-loading');
  if (loadingEl) loadingEl.style.display = 'flex';

  // Destroy previous graph
  if (graphControls) {
    try { graphControls.destroy(); } catch {}
    graphControls = null;
  }

  // Gather filter values
  const selectedNodeTypes = [...document.querySelectorAll('.node-type-cb:checked')].map(cb => cb.value);
  const selectedRelTypes  = [...document.querySelectorAll('.rel-type-cb:checked')].map(cb => cb.value);
  const clienteId = document.getElementById('grafo-client-select')?.value || null;
  const depth     = Number(document.getElementById('depth-slider')?.value ?? 2);

  try {
    const [nodesResult, edgesResult] = await Promise.all([
      getGrafoNodos(selectedNodeTypes.length < ALL_NODE_TYPES.length ? selectedNodeTypes : null, 800),
      getGrafoRelaciones({
        tipos_relacion: selectedRelTypes.length < ALL_REL_TYPES.length ? selectedRelTypes : null,
        cliente_id: clienteId || null,
        profundidad: depth,
      }),
    ]);

    const nodes = Array.isArray(nodesResult)
      ? nodesResult
      : (nodesResult?.nodos ?? nodesResult?.data ?? []);

    const edges = Array.isArray(edgesResult)
      ? edgesResult
      : (edgesResult?.enlaces ?? edgesResult?.relaciones ?? edgesResult?.data ?? []);

    if (loadingEl) loadingEl.style.display = 'none';

    const svgEl = document.getElementById('grafo-svg');
    if (!svgEl) return;

    // Wait two animation frames so the browser has computed layout
    // before D3 reads getBoundingClientRect() for forceCenter dimensions.
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

    graphControls = renderGrafoD3(svgEl, nodes, edges, onNodeClick);

    // Update counters
    const nc = document.getElementById('node-count-badge');
    const ec = document.getElementById('edge-count-badge');
    if (nc) nc.textContent = `Nodos: ${graphControls.nodeCount}`;
    if (ec) ec.textContent = `Aristas: ${graphControls.edgeCount}`;

    // Wire up control buttons
    setupControlButtons();

  } catch (err) {
    if (loadingEl) loadingEl.style.display = 'none';

    // Restore the grafo-main structure so retrying works.
    // Replacing innerHTML removes the SVG, so we keep the SVG but add an overlay.
    const grafoMain = document.querySelector('.grafo-main');
    if (grafoMain) {
      // Remove any previous error overlay
      const prev = grafoMain.querySelector('.grafo-error-overlay');
      if (prev) prev.remove();

      const errDiv = document.createElement('div');
      errDiv.className = 'grafo-error-overlay';
      errDiv.style.cssText = 'position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;background:rgba(255,255,255,.9);z-index:25';
      errDiv.innerHTML = `
        <div style="font-size:2rem">⚠️</div>
        <h3 style="margin:0;font-size:1rem">Error al cargar el grafo</h3>
        <p style="margin:0;font-size:.85rem;color:#666;max-width:320px;text-align:center">${err.message}</p>
        <button class="btn btn-primary" id="grafo-retry-btn">Reintentar</button>
      `;
      grafoMain.appendChild(errDiv);
      document.getElementById('grafo-retry-btn')?.addEventListener('click', () => {
        errDiv.remove();
        loadGraph();
      });
    }
  }
}

// ----------------------------------------------------------------
// Control buttons
// ----------------------------------------------------------------
let frozen = false;

function setupControlButtons() {
  const centerBtn    = document.getElementById('center-btn');
  const freezeBtn    = document.getElementById('freeze-btn');
  const resetZoomBtn = document.getElementById('reset-zoom-btn');

  if (centerBtn) {
    const newCenter = centerBtn.cloneNode(true);
    centerBtn.parentNode.replaceChild(newCenter, centerBtn);
    newCenter.addEventListener('click', () => { graphControls?.center?.(); });
  }

  if (freezeBtn) {
    const newFreeze = freezeBtn.cloneNode(true);
    freezeBtn.parentNode.replaceChild(newFreeze, freezeBtn);
    frozen = false;
    newFreeze.addEventListener('click', () => {
      if (!graphControls) return;
      if (frozen) {
        graphControls.unfreeze();
        newFreeze.textContent = '❄️ Congelar';
        newFreeze.classList.remove('btn-primary');
        newFreeze.classList.add('btn-outline');
      } else {
        graphControls.freeze();
        newFreeze.textContent = '▶️ Reanudar';
        newFreeze.classList.remove('btn-outline');
        newFreeze.classList.add('btn-primary');
      }
      frozen = !frozen;
    });
  }

  if (resetZoomBtn) {
    const newReset = resetZoomBtn.cloneNode(true);
    resetZoomBtn.parentNode.replaceChild(newReset, resetZoomBtn);
    newReset.addEventListener('click', () => {
      if (!graphControls?.zoom) return;
      const svg = d3.select('#grafo-svg');
      svg.transition().duration(500).call(graphControls.zoom.transform, d3.zoomIdentity);
    });
  }
}

// ----------------------------------------------------------------
// Node click → info panel
// ----------------------------------------------------------------
function onNodeClick(node, connections) {
  const panel = document.getElementById('node-info-panel');
  if (!panel) return;

  const tipo = node.tipo ?? node.labels?.[0] ?? node.type ?? 'Desconocido';
  const color = NODE_COLORS[tipo] ?? '#adb5bd';

  const skip = new Set(['x', 'y', 'vx', 'vy', 'fx', 'fy', 'index']);
  const props = Object.entries(node)
    .filter(([k, v]) => !skip.has(k) && v !== null && v !== undefined);

  const labels = {
    id:              'ID',
    tipo:            'Tipo',
    nombre:          'Nombre',
    telefono:        'Teléfono',
    monto:           'Monto',
    fecha:           'Fecha',
    estado:          'Estado',
    sentimiento:     'Sentimiento',
    tipo_deuda:      'Tipo Deuda',
    agente_id:       'Agente ID',
    cliente_id:      'Cliente ID',
  };

  panel.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">
      <span style="width:16px;height:16px;border-radius:50%;background:${color};display:inline-block;flex-shrink:0"></span>
      <div class="node-detail-title" style="margin:0">${tipo}</div>
    </div>
    <div class="stat-row" style="background:#f8f9fa;padding:6px 10px;border-radius:6px;margin-bottom:10px">
      <span class="stat-label">Conexiones</span>
      <span class="stat-value">${connections}</span>
    </div>
    ${props.map(([k, v]) => {
      let displayVal = typeof v === 'object' ? JSON.stringify(v) : String(v);
      if (displayVal.length > 60) displayVal = displayVal.slice(0, 58) + '…';
      return `
        <div class="node-prop-row">
          <span class="node-prop-key">${labels[k] ?? k}</span>
          <span class="node-prop-val">${displayVal}</span>
        </div>
      `;
    }).join('')}
  `;
}

// ----------------------------------------------------------------
// Populate client selector
// ----------------------------------------------------------------
function populateClientSelect() {
  const sel = document.getElementById('grafo-client-select');
  if (!sel) return;

  allClientes.forEach(c => {
    const id = c.id ?? c.cliente_id ?? c._id;
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = c.nombre ?? c.name ?? `Cliente ${id}`;
    sel.appendChild(opt);
  });
}
