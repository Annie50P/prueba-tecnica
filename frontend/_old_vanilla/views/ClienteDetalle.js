/**
 * ClienteDetalle.js — Client detail view with searchable selector + timeline
 */

import { getClientes, getClienteTimeline } from '../api.js';
import { renderTimeline } from '../components/Timeline.js';
import { formatCurrency, formatPercent, formatDate, formatDateTime } from '../components/KpiCard.js';

// ----------------------------------------------------------------
// State
// ----------------------------------------------------------------
let allClientes = [];
let selectedClienteId = null;

// ----------------------------------------------------------------
// Main render
// ----------------------------------------------------------------
export async function renderClienteDetalle(clienteId) {
  const container = document.getElementById('view-container');
  selectedClienteId = clienteId;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Detalle de Cliente</h1>
        <p class="page-subtitle">Historial de interacciones y estadísticas</p>
      </div>
    </div>

    <!-- Searchable client selector -->
    <div class="client-selector-wrapper" id="selector-wrapper">
      <span class="client-search-icon">🔍</span>
      <input
        type="text"
        id="client-search"
        class="client-search-input"
        placeholder="Buscar cliente por nombre..."
        autocomplete="off"
      />
      <div id="client-dropdown" class="client-dropdown"></div>
    </div>

    <div id="cliente-content">
      <div class="empty-state">
        <div class="empty-icon">👤</div>
        <p>Selecciona un cliente para ver su detalle</p>
      </div>
    </div>
  `;

  // Load client list
  try {
    const result = await getClientes();
    allClientes = Array.isArray(result) ? result : (result?.clientes ?? result?.data ?? []);
  } catch (err) {
    showError(container, err);
    return;
  }

  // Set up search
  setupClientSearch();

  // If a client ID was passed, load it directly
  if (clienteId) {
    const found = allClientes.find(c =>
      String(c.id ?? c.cliente_id ?? c._id) === String(clienteId)
    );
    if (found) {
      const nameInput = document.getElementById('client-search');
      if (nameInput) nameInput.value = found.nombre ?? found.name ?? '';
    }
    await loadClienteDetail(clienteId);
  }
}

// ----------------------------------------------------------------
// Searchable dropdown
// ----------------------------------------------------------------
function setupClientSearch() {
  const input    = document.getElementById('client-search');
  const dropdown = document.getElementById('client-dropdown');
  if (!input || !dropdown) return;

  let focused = false;

  input.addEventListener('focus', () => {
    focused = true;
    renderDropdown(input.value);
  });

  input.addEventListener('input', () => {
    renderDropdown(input.value);
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('#selector-wrapper')) {
      dropdown.classList.remove('open');
      focused = false;
    }
  });

  function renderDropdown(query) {
    const q = query.toLowerCase().trim();
    const filtered = q
      ? allClientes.filter(c => {
          const name = (c.nombre ?? c.name ?? '').toLowerCase();
          const phone = (c.telefono ?? c.phone ?? '').toLowerCase();
          return name.includes(q) || phone.includes(q);
        })
      : allClientes;

    const items = filtered.slice(0, 50);

    if (items.length === 0) {
      dropdown.innerHTML = `<div class="client-option" style="pointer-events:none;color:#adb5bd">Sin resultados</div>`;
    } else {
      dropdown.innerHTML = items.map(c => {
        const id  = c.id ?? c.cliente_id ?? c._id;
        const isSel = String(id) === String(selectedClienteId);
        return `
          <div class="client-option ${isSel ? 'selected' : ''}" data-id="${id}">
            <div>${c.nombre ?? c.name ?? id}</div>
            <div class="client-option-sub">${c.telefono ?? c.phone ?? ''} · ${debtTypeLabel(c.tipo_deuda)}</div>
          </div>
        `;
      }).join('');
    }

    dropdown.classList.add('open');

    dropdown.querySelectorAll('.client-option[data-id]').forEach(el => {
      el.addEventListener('click', async () => {
        const id = el.dataset.id;
        selectedClienteId = id;
        input.value = el.querySelector('div').textContent.trim();
        dropdown.classList.remove('open');
        // Update URL hash without triggering full re-render
        window.history.replaceState(null, '', `#/clientes/${encodeURIComponent(id)}`);
        await loadClienteDetail(id);
      });
    });
  }
}

// ----------------------------------------------------------------
// Load and render client detail
// ----------------------------------------------------------------
async function loadClienteDetail(id) {
  const content = document.getElementById('cliente-content');
  if (!content) return;

  content.innerHTML = `<div class="loading-screen"><div class="spinner"></div><p>Cargando cliente...</p></div>`;

  let timeline;
  let cliente = allClientes.find(c => String(c.id ?? c.cliente_id ?? c._id) === String(id));

  try {
    const timelineResult = await getClienteTimeline(id);
    timeline = Array.isArray(timelineResult)
      ? timelineResult
      : (timelineResult?.interacciones ?? timelineResult?.timeline ?? timelineResult?.data ?? []);

    // If client not in list, try to extract from timeline
    if (!cliente && timeline.length > 0) {
      cliente = {
        nombre: timeline[0].cliente_nombre ?? `Cliente ${id}`,
        id,
      };
    }
  } catch (err) {
    content.innerHTML = `
      <div class="error-state">
        <div class="error-icon">⚠️</div>
        <h3>Error al cargar datos del cliente</h3>
        <p>${err.message}</p>
      </div>
    `;
    return;
  }

  if (!cliente) {
    cliente = { nombre: `Cliente ${id}`, id };
  }

  // Compute stats from timeline
  const stats = computeStats(timeline, cliente);

  content.innerHTML = buildClienteHTML(cliente, stats);

  // Render timeline
  const timelineEl = document.getElementById('timeline-container');
  if (timelineEl) {
    renderTimeline(timelineEl, timeline);
  }
}

// ----------------------------------------------------------------
// Compute stats from timeline
// ----------------------------------------------------------------
function computeStats(timeline, cliente) {
  const llamadas    = timeline.filter(i => i.tipo?.toLowerCase() === 'llamada');
  const pagos       = timeline.filter(i => i.tipo?.toLowerCase() === 'pago');
  const promesas    = timeline.filter(i => i.tipo?.toLowerCase() === 'promesa');
  const cumplidas   = promesas.filter(i => i.estado?.toLowerCase() === 'cumplida');
  const totalPagado = pagos.reduce((s, p) => s + (Number(p.monto) || 0), 0);
  const lastContact = timeline.length > 0
    ? timeline.reduce((a, b) => new Date(a.fecha) > new Date(b.fecha) ? a : b)
    : null;

  // Sentiment distribution
  const sents = { cooperativo: 0, neutral: 0, frustrado: 0, hostil: 0 };
  llamadas.forEach(l => {
    const s = l.sentimiento?.toLowerCase();
    if (s && sents[s] !== undefined) sents[s]++;
  });

  // Payment plan
  const plan = cliente.plan_pago ?? cliente.plan_activo ?? null;

  return {
    totalInteracciones: timeline.length,
    totalLlamadas: llamadas.length,
    totalPagos: pagos.length,
    totalPromesas: promesas.length,
    promesasCumplidas: cumplidas.length,
    totalPagado,
    lastContact,
    sentimientos: sents,
    plan,
    duracionTotal: llamadas.reduce((s, l) => s + (Number(l.duracion_segundos) || 0), 0),
  };
}

// ----------------------------------------------------------------
// Build HTML
// ----------------------------------------------------------------
function buildClienteHTML(cliente, stats) {
  const montoDeuda  = Number(cliente.monto_deuda_inicial ?? cliente.monto_deuda ?? 0);
  const totalPagado = stats.totalPagado;
  const pct = montoDeuda > 0 ? Math.min(100, (totalPagado / montoDeuda) * 100) : 0;
  const estado = cliente.estado ?? (pct >= 100 ? 'pagado' : pct > 0 ? 'en_proceso' : 'pendiente');

  const statusBadge = {
    pagado:     'badge-success',
    en_proceso: 'badge-info',
    pendiente:  'badge-warning',
    moroso:     'badge-danger',
    default:    'badge-secondary',
  };

  const statusLabel = {
    pagado:     'Pagado',
    en_proceso: 'En Proceso',
    pendiente:  'Pendiente',
    moroso:     'Moroso',
  };

  const deuda = montoDeuda > 0 ? formatCurrency(montoDeuda) : '—';
  const pagado = formatCurrency(totalPagado);
  const pctStr = formatPercent(pct);

  const avgDur = stats.totalLlamadas > 0
    ? `${Math.floor(stats.duracionTotal / stats.totalLlamadas / 60)}m ${Math.round((stats.duracionTotal / stats.totalLlamadas) % 60)}s`
    : '—';

  return `
    <!-- Client Header -->
    <div class="cliente-header">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap">
        <div>
          <h2 class="cliente-name">${cliente.nombre ?? cliente.name ?? '—'}</h2>
          <div class="cliente-meta">
            ${cliente.telefono ? `<span>📞 ${cliente.telefono}</span>` : ''}
            ${cliente.email ? `<span>📧 ${cliente.email}</span>` : ''}
            <span>💳 ${debtTypeLabel(cliente.tipo_deuda)}</span>
            ${cliente.documento ? `<span>🪪 ${cliente.documento}</span>` : ''}
          </div>
        </div>
        <span class="badge ${statusBadge[estado] ?? statusBadge.default}" style="font-size:13px;padding:6px 12px">
          ${statusLabel[estado] ?? estado}
        </span>
      </div>
      ${montoDeuda > 0 ? `
        <div class="progress-label">
          <span>Recuperado: ${pagado}</span>
          <span>${pctStr} de ${deuda}</span>
        </div>
        <div class="progress">
          <div class="progress-bar" style="width:${pct}%;background:${pct >= 100 ? '#198754' : pct >= 50 ? '#0d6efd' : '#ffc107'}"></div>
        </div>
      ` : ''}
    </div>

    <!-- Layout: Timeline + Side Panel -->
    <div class="cliente-layout">
      <!-- Timeline -->
      <div>
        <div class="card">
          <div class="card-header">
            <span>Historial de Interacciones</span>
            <span class="badge badge-secondary">${stats.totalInteracciones}</span>
          </div>
          <div class="card-body">
            <div id="timeline-container"></div>
          </div>
        </div>
      </div>

      <!-- Side Panel -->
      <div class="side-panel">
        <!-- Call Stats -->
        <div class="card">
          <div class="card-header">Estadísticas</div>
          <div class="card-body" style="padding:0 18px">
            <div class="stat-row">
              <span class="stat-label">Total Llamadas</span>
              <span class="stat-value">📞 ${stats.totalLlamadas}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Duración Media</span>
              <span class="stat-value">${avgDur}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Pagos Registrados</span>
              <span class="stat-value">💰 ${stats.totalPagos}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Total Pagado</span>
              <span class="stat-value text-success">${pagado}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Último Contacto</span>
              <span class="stat-value">${stats.lastContact ? formatDate(stats.lastContact.fecha) : '—'}</span>
            </div>
          </div>
        </div>

        <!-- Promises -->
        <div class="card">
          <div class="card-header">Promesas de Pago</div>
          <div class="card-body" style="padding:0 18px">
            <div class="stat-row">
              <span class="stat-label">Total Promesas</span>
              <span class="stat-value">${stats.totalPromesas}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Cumplidas</span>
              <span class="stat-value text-success">✅ ${stats.promesasCumplidas}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Incumplidas</span>
              <span class="stat-value text-danger">❌ ${stats.totalPromesas - stats.promesasCumplidas}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Tasa Cumplimiento</span>
              <span class="stat-value">
                ${stats.totalPromesas > 0 ? formatPercent((stats.promesasCumplidas / stats.totalPromesas) * 100) : '—'}
              </span>
            </div>
          </div>
        </div>

        <!-- Sentiment -->
        <div class="card">
          <div class="card-header">Sentimientos (Llamadas)</div>
          <div class="card-body" style="padding:0 18px">
            ${Object.entries(stats.sentimientos).map(([k, v]) => `
              <div class="stat-row">
                <span class="stat-label">${capitalize(k)}</span>
                <span class="stat-value">
                  <span class="badge ${sentBadge(k)}">${v}</span>
                </span>
              </div>
            `).join('')}
          </div>
        </div>

        ${stats.plan ? `
          <div class="card">
            <div class="card-header">Plan de Pago Activo</div>
            <div class="card-body">
              <p style="font-size:13px;color:#6c757d">${JSON.stringify(stats.plan, null, 2)}</p>
            </div>
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------
function debtTypeLabel(tipo) {
  const map = {
    hipoteca:          'Hipoteca',
    tarjeta_credito:   'Tarjeta Crédito',
    prestamo_personal: 'Préstamo Personal',
    auto:              'Auto',
  };
  return map[tipo?.toLowerCase()] ?? tipo ?? 'Desconocido';
}

function sentBadge(s) {
  return { cooperativo: 'badge-success', neutral: 'badge-warning', frustrado: 'badge-orange', hostil: 'badge-danger' }[s] ?? 'badge-secondary';
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

function showError(container, err) {
  container.innerHTML = `
    <div class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>Error al cargar datos</h3>
      <p>${err.message ?? 'No se pudo conectar con la API'}</p>
      <button class="btn btn-primary mt-3" onclick="window.location.hash='#/clientes'">
        Reintentar
      </button>
    </div>
  `;
}
