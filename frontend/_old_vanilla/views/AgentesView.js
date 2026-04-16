/**
 * AgentesView.js — Agents list + detail panel
 * Shows all agents with metrics; clicking one loads full efectividad detail.
 */

import { getAgentes, getAgenteEfectividad } from '../api.js';
import { renderKpiGrid, formatPercent } from '../components/KpiCard.js';

// ----------------------------------------------------------------
// State
// ----------------------------------------------------------------
let allAgentes = [];
let selectedAgenteId = null;
let detailChart = null;

// ----------------------------------------------------------------
// Main render
// ----------------------------------------------------------------
export async function renderAgentesView() {
  const container = document.getElementById('view-container');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Agentes</h1>
        <p class="page-subtitle">Desempeño y métricas de los agentes de cobro</p>
      </div>
      <button id="refresh-btn" class="btn btn-outline">🔄 Actualizar</button>
    </div>

    <div id="kpi-agentes"></div>

    <div class="agentes-layout" id="agentes-layout">
      <div class="card" id="agentes-list-card">
        <div class="card-header">
          <span>Agentes</span>
          <span class="badge badge-secondary" id="agentes-count">—</span>
        </div>
        <div class="card-body" style="padding:0">
          <div class="loading-screen"><div class="spinner"></div><p>Cargando...</p></div>
        </div>
      </div>

      <div id="agente-detail-panel">
        <div class="empty-state" style="margin-top:0">
          <div class="empty-icon">👥</div>
          <p>Selecciona un agente para ver su detalle</p>
        </div>
      </div>
    </div>
  `;

  document.getElementById('refresh-btn').addEventListener('click', () => {
    destroyChart();
    selectedAgenteId = null;
    renderAgentesView();
  });

  try {
    const result = await getAgentes();
    allAgentes = Array.isArray(result) ? result : (result?.agentes ?? result?.data ?? []);
  } catch (err) {
    container.innerHTML = buildErrorState(err, '#/agentes');
    return;
  }

  renderGlobalKpis();
  renderAgentesList();

  return () => destroyChart();
}

// ----------------------------------------------------------------
// Global KPIs (averages across all agents)
// ----------------------------------------------------------------
function renderGlobalKpis() {
  const kpiContainer = document.getElementById('kpi-agentes');
  if (!kpiContainer || allAgentes.length === 0) return;

  const totalLlamadas = allAgentes.reduce((s, a) => s + (a.total_llamadas ?? 0), 0);
  const avgPromesa    = allAgentes.reduce((s, a) => s + (a.tasa_promesa ?? 0), 0) / allAgentes.length;
  const avgPago       = allAgentes.reduce((s, a) => s + (a.tasa_pago_inmediato ?? 0), 0) / allAgentes.length;
  const bestAgent     = allAgentes.reduce((best, a) =>
    (a.tasa_promesa ?? 0) > (best.tasa_promesa ?? 0) ? a : best, allAgentes[0]);

  renderKpiGrid(kpiContainer, [
    {
      label: 'Total Agentes',
      value: allAgentes.length,
      icon: '👥',
      color: '#0d6efd',
      sub: 'Activos en el sistema',
    },
    {
      label: 'Total Llamadas',
      value: totalLlamadas.toLocaleString('es-PA'),
      icon: '📞',
      color: '#6f42c1',
      sub: 'Entre todos los agentes',
    },
    {
      label: 'Tasa Promesa Media',
      value: formatPercent(avgPromesa * 100),
      icon: '🤝',
      color: '#198754',
      valueClass: 'text-success',
      sub: 'Promedio del equipo',
    },
    {
      label: 'Mejor Agente',
      value: bestAgent?.id ?? '—',
      icon: '🏆',
      color: '#ffc107',
      sub: `Tasa promesa: ${formatPercent((bestAgent?.tasa_promesa ?? 0) * 100)}`,
    },
  ]);
}

// ----------------------------------------------------------------
// Agents list table
// ----------------------------------------------------------------
function renderAgentesList() {
  const card = document.getElementById('agentes-list-card');
  if (!card) return;

  document.getElementById('agentes-count').textContent = allAgentes.length;

  const sorted = [...allAgentes].sort((a, b) => (b.tasa_promesa ?? 0) - (a.tasa_promesa ?? 0));

  const bodyEl = card.querySelector('.card-body');
  if (!bodyEl) return;

  if (sorted.length === 0) {
    bodyEl.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">👥</div>
        <p>No se encontraron agentes</p>
      </div>`;
    return;
  }

  bodyEl.innerHTML = `
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Agente</th>
            <th class="text-right">Llamadas</th>
            <th class="text-right">Tasa Promesa</th>
            <th class="text-right">Pago Inmediato</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="agentes-tbody">
          ${sorted.map(a => buildAgentRow(a)).join('')}
        </tbody>
      </table>
    </div>
  `;

  document.querySelectorAll('.agente-row').forEach(row => {
    row.addEventListener('click', () => {
      const id = row.dataset.id;
      document.querySelectorAll('.agente-row').forEach(r => r.classList.remove('selected'));
      row.classList.add('selected');
      loadAgenteDetail(id);
    });
  });

  // Auto-select first agent
  const firstRow = document.querySelector('.agente-row');
  if (firstRow) firstRow.click();
}

function buildAgentRow(a) {
  const pctPromesa = (a.tasa_promesa ?? 0) * 100;
  const pctPago    = (a.tasa_pago_inmediato ?? 0) * 100;
  const color      = pctPromesa >= 30 ? 'badge-success' : pctPromesa >= 20 ? 'badge-warning' : 'badge-danger';

  return `
    <tr class="agente-row" data-id="${a.id}" style="cursor:pointer">
      <td><strong>${a.id}</strong></td>
      <td class="text-right">${(a.total_llamadas ?? 0).toLocaleString('es-PA')}</td>
      <td class="text-right">
        <span class="badge ${color}">${formatPercent(pctPromesa)}</span>
      </td>
      <td class="text-right">${formatPercent(pctPago)}</td>
      <td class="text-right" style="color:#adb5bd">›</td>
    </tr>
  `;
}

// ----------------------------------------------------------------
// Agent detail panel
// ----------------------------------------------------------------
async function loadAgenteDetail(agenteId) {
  if (selectedAgenteId === agenteId) return;
  selectedAgenteId = agenteId;

  const panel = document.getElementById('agente-detail-panel');
  if (!panel) return;

  destroyChart();
  panel.innerHTML = `<div class="loading-screen" style="min-height:200px"><div class="spinner"></div><p>Cargando...</p></div>`;

  let data;
  try {
    data = await getAgenteEfectividad(agenteId);
  } catch (err) {
    panel.innerHTML = `
      <div class="error-state">
        <div class="error-icon">⚠️</div>
        <p>${err.message}</p>
      </div>`;
    return;
  }

  panel.innerHTML = buildDetailHTML(data);

  // Render results bar chart
  const canvas = document.getElementById('resultados-chart');
  if (canvas && data.distribucion_resultados) {
    const labels = Object.keys(data.distribucion_resultados);
    const values = Object.values(data.distribucion_resultados);
    const colors = labels.map((_, i) => [
      '#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1', '#fd7e14',
    ][i % 6]);

    destroyChart();
    detailChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels.map(l => l.replace(/_/g, ' ')),
        datasets: [{
          label: 'Llamadas',
          data: values,
          backgroundColor: colors,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 } } },
          y: { beginAtZero: true, grid: { color: '#f0f0f0' }, ticks: { stepSize: 1 } },
        },
      },
    });
  }
}

function buildDetailHTML(d) {
  const pctPromesa = (d.tasa_promesa ?? 0) * 100;
  const pctPago    = (d.tasa_pago_inmediato ?? 0) * 100;
  const sents      = d.distribucion_sentimientos ?? {};
  const sentOrder  = ['cooperativo', 'neutral', 'frustrado', 'hostil',
    ...Object.keys(sents).filter(k => !['cooperativo','neutral','frustrado','hostil'].includes(k))
  ];

  return `
    <div class="card">
      <div class="card-header">
        <span>${d.id}</span>
        <span class="badge ${pctPromesa >= 30 ? 'badge-success' : pctPromesa >= 20 ? 'badge-warning' : 'badge-danger'}">
          ${formatPercent(pctPromesa)} promesas
        </span>
      </div>
      <div class="card-body">

        <!-- KPIs del agente -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:16px">
          ${statBox('📞 Llamadas', d.total_llamadas ?? 0)}
          ${statBox('🤝 Tasa Promesa', formatPercent(pctPromesa))}
          ${statBox('💳 Pago Inmediato', formatPercent(pctPago))}
        </div>

        ${d.mejor_horario ? `
          <div class="stat-row" style="background:#f8f9fa;padding:8px 12px;border-radius:6px;margin-bottom:16px">
            <span class="stat-label">⏰ Mejor horario</span>
            <span class="stat-value"><strong>${d.mejor_horario}</strong></span>
          </div>
        ` : ''}

        <!-- Distribución de resultados -->
        ${d.distribucion_resultados && Object.keys(d.distribucion_resultados).length > 0 ? `
          <div style="margin-bottom:16px">
            <div class="card-header" style="padding:8px 0;border:none;font-size:13px;color:#6c757d">
              Distribución de Resultados
            </div>
            <div class="chart-canvas-wrapper" style="height:160px">
              <canvas id="resultados-chart"></canvas>
            </div>
          </div>
        ` : ''}

        <!-- Sentimientos -->
        ${Object.keys(sents).length > 0 ? `
          <div>
            <div style="font-size:12px;color:#6c757d;margin-bottom:8px;font-weight:600;text-transform:uppercase;letter-spacing:.5px">
              Sentimientos de Clientes
            </div>
            ${sentOrder.filter(k => sents[k] != null).map(k => {
              const total = Object.values(sents).reduce((a, b) => a + b, 0);
              const pct   = total > 0 ? ((sents[k] / total) * 100).toFixed(0) : 0;
              return `
                <div style="margin-bottom:8px">
                  <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
                    <span>${capitalize(k)}</span>
                    <span>${sents[k]} (${pct}%)</span>
                  </div>
                  <div style="background:#f0f0f0;border-radius:4px;height:6px">
                    <div style="background:${sentColor(k)};width:${pct}%;height:6px;border-radius:4px"></div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        ` : ''}

      </div>
    </div>
  `;
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------
function statBox(label, value) {
  return `
    <div style="background:#f8f9fa;border-radius:8px;padding:10px 12px;text-align:center">
      <div style="font-size:11px;color:#6c757d;margin-bottom:4px">${label}</div>
      <div style="font-size:16px;font-weight:700;color:#212529">${value}</div>
    </div>
  `;
}

function sentColor(s) {
  return { cooperativo: '#198754', neutral: '#ffc107', frustrado: '#fd7e14', hostil: '#dc3545' }[s] ?? '#6c757d';
}

function capitalize(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

function destroyChart() {
  if (detailChart) { detailChart.destroy(); detailChart = null; }
}

function buildErrorState(err, retryHash) {
  return `
    <div class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>Error al cargar agentes</h3>
      <p>${err.message ?? 'No se pudo conectar con la API'}</p>
      <button class="btn btn-primary mt-3" onclick="window.location.hash='${retryHash}'">
        Reintentar
      </button>
    </div>
  `;
}
