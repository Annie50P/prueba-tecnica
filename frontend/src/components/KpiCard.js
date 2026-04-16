/**
 * KpiCard.js — Reusable KPI card component
 */

/**
 * Creates a KPI card HTML element
 * @param {Object} config
 * @param {string} config.label - Card title
 * @param {string|number} config.value - Main value to display
 * @param {string} [config.sub] - Subtitle / secondary info
 * @param {string} [config.icon] - Emoji icon
 * @param {string} [config.color] - CSS color for the top bar (default: --color-primary)
 * @param {string} [config.valueClass] - Extra CSS class for value (e.g. 'text-success')
 * @returns {HTMLElement}
 */
export function createKpiCard({ label, value, sub, icon, color, valueClass = '' }) {
  const card = document.createElement('div');
  card.className = 'kpi-card';
  if (color) card.style.setProperty('--kpi-color', color);

  card.innerHTML = `
    ${icon ? `<span class="kpi-icon">${icon}</span>` : ''}
    <div class="kpi-label">${label}</div>
    <div class="kpi-value ${valueClass}">${value ?? '—'}</div>
    ${sub ? `<div class="kpi-sub">${sub}</div>` : ''}
  `;

  return card;
}

/**
 * Renders multiple KPI cards into a container element
 * @param {HTMLElement} container
 * @param {Array} cards - Array of KPI card config objects
 */
export function renderKpiGrid(container, cards) {
  const grid = document.createElement('div');
  grid.className = 'kpi-grid';
  cards.forEach(cfg => grid.appendChild(createKpiCard(cfg)));
  container.appendChild(grid);
  return grid;
}

// ----------------------------------------------------------------
// Formatting helpers used by multiple views
// ----------------------------------------------------------------
export function formatCurrency(amount) {
  if (amount == null || isNaN(amount)) return '—';
  return new Intl.NumberFormat('es-PA', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(value, decimals = 1) {
  if (value == null || isNaN(value)) return '—';
  return `${Number(value).toFixed(decimals)}%`;
}

export function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Intl.DateTimeFormat('es-PA', { dateStyle: 'medium' }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Intl.DateTimeFormat('es-PA', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}
