/**
 * Timeline.js — Vertical chronological interaction timeline component
 */

import { formatDateTime } from './KpiCard.js';

// ----------------------------------------------------------------
// Sentiment helpers
// ----------------------------------------------------------------
const SENTIMENT_CLASS = {
  cooperativo: 'cooperativo',
  neutral:     'neutral',
  frustrado:   'frustrado',
  hostil:      'hostil',
};

const SENTIMENT_LABEL = {
  cooperativo: 'Cooperativo',
  neutral:     'Neutral',
  frustrado:   'Frustrado',
  hostil:      'Hostil',
};

const SENTIMENT_BADGE = {
  cooperativo: 'badge-success',
  neutral:     'badge-warning',
  frustrado:   'badge-orange',
  hostil:      'badge-danger',
};

// ----------------------------------------------------------------
// Interaction type helpers
// ----------------------------------------------------------------
const TYPE_ICON = {
  llamada:    '📞',
  email:      '📧',
  sms:        '💬',
  pago:       '💰',
  promesa:    '🤝',
  visita:     '🏠',
  default:    '📋',
};

const TYPE_LABEL = {
  llamada:    'Llamada',
  email:      'Email',
  sms:        'SMS',
  pago:       'Pago',
  promesa:    'Promesa de Pago',
  visita:     'Visita',
};

function getIcon(tipo) {
  return TYPE_ICON[tipo?.toLowerCase()] ?? TYPE_ICON.default;
}

function getTypeLabel(tipo) {
  return TYPE_LABEL[tipo?.toLowerCase()] ?? tipo ?? 'Interacción';
}

function getSentimentKey(sentiment) {
  return SENTIMENT_CLASS[sentiment?.toLowerCase()] ?? null;
}

// ----------------------------------------------------------------
// Build detail rows from an interaction object
// ----------------------------------------------------------------
function buildDetailRows(item) {
  const skip = new Set(['id', 'tipo', 'fecha', 'sentimiento', 'resumen', 'cliente_id', 'cliente_nombre']);
  const rows = [];

  const fieldLabels = {
    duracion_segundos: 'Duración',
    agente_nombre:     'Agente',
    agente_id:         'ID Agente',
    resultado:         'Resultado',
    monto:             'Monto',
    monto_prometido:   'Monto prometido',
    fecha_promesa:     'Fecha promesa',
    notas:             'Notas',
    canal:             'Canal',
    transcripcion:     'Transcripción',
  };

  for (const [key, val] of Object.entries(item)) {
    if (skip.has(key) || val === null || val === undefined || val === '') continue;
    let displayVal = val;

    if (key === 'duracion_segundos') {
      const mins = Math.floor(val / 60);
      const secs = val % 60;
      displayVal = `${mins}m ${secs}s`;
    } else if (key === 'monto' || key === 'monto_prometido') {
      displayVal = `$${Number(val).toLocaleString('es-PA', { minimumFractionDigits: 2 })}`;
    } else if (key === 'fecha_promesa') {
      displayVal = formatDateTime(val);
    } else if (typeof val === 'boolean') {
      displayVal = val ? 'Sí' : 'No';
    } else if (typeof val === 'object') {
      displayVal = JSON.stringify(val);
    }

    rows.push({ label: fieldLabels[key] ?? key, value: displayVal });
  }

  return rows;
}

// ----------------------------------------------------------------
// Render single timeline item element
// ----------------------------------------------------------------
function createTimelineItem(item) {
  const sentKey = getSentimentKey(item.sentimiento);
  const icon = getIcon(item.tipo);
  const typeLabel = getTypeLabel(item.tipo);
  const sentimentLabel = sentKey ? SENTIMENT_LABEL[sentKey] : null;
  const sentimentBadge = sentKey ? SENTIMENT_BADGE[sentKey] : 'badge-secondary';
  const iconBgClass = sentKey ? `icon-bg-${sentKey}` : 'icon-bg-default';
  const detailRows = buildDetailRows(item);

  const wrapper = document.createElement('div');
  wrapper.className = 'timeline-item';

  wrapper.innerHTML = `
    <span class="timeline-icon ${iconBgClass}">${icon}</span>
    <div class="timeline-card ${sentKey ? `sentiment-${sentKey}` : ''}">
      <div class="timeline-header">
        <span class="timeline-type">${typeLabel}</span>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          ${sentimentLabel ? `<span class="badge ${sentimentBadge}">${sentimentLabel}</span>` : ''}
          <span class="timeline-date">${formatDateTime(item.fecha)}</span>
          <span style="font-size:18px;color:#adb5bd;cursor:pointer" class="expand-toggle">▾</span>
        </div>
      </div>
      ${item.resumen ? `<div class="timeline-summary">${item.resumen}</div>` : ''}
      <div class="timeline-details">
        ${detailRows.length > 0
          ? detailRows.map(r => `
            <div class="timeline-detail-row">
              <span class="timeline-detail-label">${r.label}</span>
              <span>${r.value}</span>
            </div>`).join('')
          : '<span class="text-muted">Sin detalles adicionales</span>'
        }
      </div>
    </div>
  `;

  // Toggle expand on click
  const card = wrapper.querySelector('.timeline-card');
  const toggle = wrapper.querySelector('.expand-toggle');

  card.addEventListener('click', () => {
    const isOpen = wrapper.classList.contains('open');
    wrapper.classList.toggle('open', !isOpen);
    card.classList.toggle('expanded', !isOpen);
    toggle.textContent = isOpen ? '▾' : '▴';
  });

  return wrapper;
}

// ----------------------------------------------------------------
// Render full timeline into container
// ----------------------------------------------------------------
export function renderTimeline(container, interactions) {
  container.innerHTML = '';

  if (!interactions || interactions.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📭</div>
        <p>Sin interacciones registradas</p>
      </div>
    `;
    return;
  }

  // Sort chronologically (newest first)
  const sorted = [...interactions].sort((a, b) => {
    return new Date(b.fecha) - new Date(a.fecha);
  });

  const timeline = document.createElement('div');
  timeline.className = 'timeline';

  sorted.forEach(item => {
    timeline.appendChild(createTimelineItem(item));
  });

  container.appendChild(timeline);
}

export default { renderTimeline };
