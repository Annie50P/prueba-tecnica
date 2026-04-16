/**
 * Dashboard.js — Main dashboard view
 * Shows KPIs, donut chart, line chart, and unfulfilled promises table
 */

import { getDashboard, getPromesasIncumplidas } from '../api.js';
import { renderKpiGrid, formatCurrency, formatPercent, formatDate } from '../components/KpiCard.js';

// Track Chart.js instances for cleanup
let donutChart = null;
let lineChart = null;

export async function renderDashboard() {
  const container = document.getElementById('view-container');

  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Resumen general de recuperación de deuda</p>
      </div>
      <button id="refresh-btn" class="btn btn-outline">🔄 Actualizar</button>
    </div>
    <div id="kpi-container"></div>
    <div class="charts-grid" id="charts-grid">
      <div class="card chart-container" id="donut-card">
        <div class="card-header">Distribución por Tipo de Deuda</div>
        <div class="card-body">
          <div class="chart-canvas-wrapper">
            <canvas id="donut-canvas"></canvas>
          </div>
        </div>
      </div>
      <div class="card chart-container" id="line-card">
        <div class="card-header">Actividad Diaria</div>
        <div class="card-body">
          <div class="chart-canvas-wrapper">
            <canvas id="line-canvas"></canvas>
          </div>
        </div>
      </div>
    </div>
    <div class="card" id="promises-card">
      <div class="card-header">
        <span>Top 10 Promesas Incumplidas</span>
        <span class="badge badge-danger" id="promises-count">0</span>
      </div>
      <div class="card-body" style="padding:0">
        <div class="table-wrapper" id="promises-table-container">
          <div class="loading-screen"><div class="spinner"></div><p>Cargando...</p></div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('refresh-btn').addEventListener('click', () => {
    destroyCharts();
    renderDashboard();
  });

  // Fetch data concurrently
  let dashData, promesasData;

  try {
    [dashData, promesasData] = await Promise.all([
      getDashboard(),
      getPromesasIncumplidas(),
    ]);
  } catch (err) {
    container.innerHTML = buildErrorState(err);
    return;
  }

  // --- KPI Cards ---
  const kpiContainer = document.getElementById('kpi-container');
  const stats = dashData?.estadisticas_globales ?? dashData ?? {};

  const totalDeuda    = stats.total_deuda_inicial ?? stats.monto_total ?? 0;
  const totalRecup    = stats.total_recuperado ?? stats.monto_recuperado ?? 0;
  const tasaRecup     = stats.tasa_recuperacion ?? (totalDeuda ? (totalRecup / totalDeuda) * 100 : 0);
  const promesasCump  = stats.promesas_cumplidas ?? 0;
  const promesasTotal = stats.total_promesas ?? stats.promesas_totales ?? 0;

  renderKpiGrid(kpiContainer, [
    {
      label: 'Total Deuda Inicial',
      value: formatCurrency(totalDeuda),
      icon: '💳',
      color: '#0d6efd',
      sub: 'Deuda total del portafolio',
    },
    {
      label: 'Total Recuperado',
      value: formatCurrency(totalRecup),
      icon: '✅',
      color: '#198754',
      valueClass: 'text-success',
      sub: 'Pagos efectivamente recibidos',
    },
    {
      label: 'Tasa de Recuperación',
      value: formatPercent(tasaRecup),
      icon: '📈',
      color: tasaRecup >= 50 ? '#198754' : tasaRecup >= 25 ? '#ffc107' : '#dc3545',
      valueClass: tasaRecup >= 50 ? 'text-success' : tasaRecup >= 25 ? 'text-warning' : 'text-danger',
      sub: `${formatCurrency(totalRecup)} de ${formatCurrency(totalDeuda)}`,
    },
    {
      label: 'Promesas Cumplidas',
      value: `${promesasCump} / ${promesasTotal}`,
      icon: '🤝',
      color: '#6c757d',
      sub: promesasTotal ? `${formatPercent((promesasCump / promesasTotal) * 100)} tasa de cumplimiento` : 'Sin datos',
    },
  ]);

  // --- Donut Chart ---
  const donutCanvas = document.getElementById('donut-canvas');
  if (donutCanvas) {
    const distribution = dashData?.distribucion_tipo_deuda ?? dashData?.por_tipo_deuda ?? {};
    const debtLabels = {
      hipoteca:         'Hipoteca',
      tarjeta_credito:  'Tarjeta Crédito',
      prestamo_personal:'Préstamo Personal',
      auto:             'Auto',
    };
    const DONUT_COLORS = ['#0d6efd', '#e76f51', '#52b788', '#ffc107'];
    const keys   = Object.keys(distribution);
    const values = Object.values(distribution);

    destroyCharts();
    donutChart = new Chart(donutCanvas, {
      type: 'doughnut',
      data: {
        labels: keys.map(k => debtLabels[k] ?? k),
        datasets: [{
          data: values,
          backgroundColor: DONUT_COLORS.slice(0, keys.length),
          borderWidth: 2,
          borderColor: '#fff',
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { padding: 14, font: { size: 12 } } },
          tooltip: {
            callbacks: {
              label: ctx => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const pct = total ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
              },
            },
          },
        },
        cutout: '60%',
      },
    });
  }

  // --- Line Chart ---
  const lineCanvas = document.getElementById('line-canvas');
  if (lineCanvas) {
    const actividad = dashData?.actividad_diaria ?? dashData?.llamadas_por_dia ?? [];
    const pagos     = dashData?.pagos_diarios ?? dashData?.pagos_por_dia ?? [];

    // Normalize to array of { fecha, llamadas, pagos }
    let dias = [];
    if (Array.isArray(actividad) && actividad.length > 0) {
      dias = actividad.map((item, i) => ({
        fecha:   item.fecha ?? item.date ?? `Día ${i + 1}`,
        llamadas: item.llamadas ?? item.total ?? item.count ?? 0,
        pagos:    pagos[i]?.total ?? pagos[i]?.count ?? pagos[i]?.pagos ?? 0,
      }));
    } else if (typeof actividad === 'object' && actividad !== null) {
      dias = Object.entries(actividad).map(([fecha, val]) => ({
        fecha,
        llamadas: typeof val === 'number' ? val : val.llamadas ?? 0,
        pagos:    0,
      }));
    }

    // Use last 30 entries
    const recent = dias.slice(-30);

    lineChart = new Chart(lineCanvas, {
      type: 'line',
      data: {
        labels: recent.map(d => {
          try { return new Intl.DateTimeFormat('es-PA', { month: 'short', day: 'numeric' }).format(new Date(d.fecha)); }
          catch { return d.fecha; }
        }),
        datasets: [
          {
            label: 'Llamadas',
            data: recent.map(d => d.llamadas),
            borderColor: '#0d6efd',
            backgroundColor: 'rgba(13,110,253,.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
          },
          {
            label: 'Pagos',
            data: recent.map(d => d.pagos),
            borderColor: '#52b788',
            backgroundColor: 'rgba(82,183,136,.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { padding: 14, font: { size: 12 } } },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
          y: { beginAtZero: true, grid: { color: '#f0f0f0' } },
        },
      },
    });
  }

  // --- Promises Table ---
  const tableContainer = document.getElementById('promises-table-container');
  const promises = Array.isArray(promesasData) ? promesasData : (promesasData?.promesas ?? promesasData?.data ?? []);
  const top10 = promises.slice(0, 10);

  document.getElementById('promises-count').textContent = promises.length;

  if (top10.length === 0) {
    tableContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🎉</div>
        <p>No hay promesas incumplidas</p>
      </div>
    `;
  } else {
    tableContainer.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Cliente</th>
            <th>Monto</th>
            <th>Fecha Promesa</th>
            <th>Días Vencida</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          ${top10.map(p => {
            const dias = p.dias_vencida ?? p.dias_vencido ?? calcDaysOverdue(p.fecha_promesa);
            return `
              <tr>
                <td><strong>${p.cliente_nombre ?? p.nombre ?? p.cliente ?? '—'}</strong></td>
                <td class="text-right">${formatCurrency(p.monto ?? p.monto_prometido)}</td>
                <td>${formatDate(p.fecha_promesa ?? p.fecha)}</td>
                <td>
                  <span class="badge ${dias > 30 ? 'badge-danger' : dias > 7 ? 'badge-warning' : 'badge-secondary'}">
                    ${dias != null ? `${dias} días` : '—'}
                  </span>
                </td>
                <td><span class="badge badge-danger">${p.estado ?? 'Incumplida'}</span></td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;
  }

  return () => destroyCharts();
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------
function destroyCharts() {
  if (donutChart) { donutChart.destroy(); donutChart = null; }
  if (lineChart)  { lineChart.destroy();  lineChart  = null; }
}

function calcDaysOverdue(dateStr) {
  if (!dateStr) return null;
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    return Math.max(0, Math.floor(diff / 86400000));
  } catch { return null; }
}

function buildErrorState(err) {
  return `
    <div class="error-state">
      <div class="error-icon">⚠️</div>
      <h3>Error al cargar datos</h3>
      <p>${err.message ?? 'No se pudo conectar con la API'}</p>
      <button class="btn btn-primary mt-3" onclick="window.location.hash='#/dashboard'">
        Reintentar
      </button>
    </div>
  `;
}
