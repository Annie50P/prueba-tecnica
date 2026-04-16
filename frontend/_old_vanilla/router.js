/**
 * router.js — Hash-based SPA router
 * Handles: #/dashboard, #/clientes/:id, #/grafo
 * Default route: #/dashboard
 */

import { renderDashboard } from './views/Dashboard.js';
import { renderClienteDetalle } from './views/ClienteDetalle.js';
import { renderGrafoViewer } from './views/GrafoViewer.js';
import { renderAgentesView } from './views/AgentesView.js';

// ----------------------------------------------------------------
// Route definitions
// ----------------------------------------------------------------
const ROUTES = [
  { pattern: /^#\/dashboard$/, view: 'dashboard', render: () => renderDashboard() },
  { pattern: /^#\/clientes\/(.+)$/, view: 'clientes', render: (m) => renderClienteDetalle(m[1]) },
  { pattern: /^#\/clientes$/, view: 'clientes', render: () => renderClienteDetalle(null) },
  { pattern: /^#\/agentes\/(.+)$/, view: 'agentes', render: (m) => renderAgentesView(m[1]) },
  { pattern: /^#\/agentes$/, view: 'agentes', render: () => renderAgentesView() },
  { pattern: /^#\/grafo$/, view: 'grafo', render: () => renderGrafoViewer() },
];

// ----------------------------------------------------------------
// State
// ----------------------------------------------------------------
let currentView = null;
let currentCleanup = null;

// ----------------------------------------------------------------
// Routing logic
// ----------------------------------------------------------------
function getContainer() {
  return document.getElementById('view-container');
}

function updateNavHighlight(viewName) {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.route === viewName);
  });
}

async function navigate(hash) {
  const h = hash || window.location.hash || '#/dashboard';

  // Clean up previous view if it has a cleanup function
  if (typeof currentCleanup === 'function') {
    try { currentCleanup(); } catch (e) { /* ignore */ }
    currentCleanup = null;
  }

  let matched = null;
  let matchResult = null;

  for (const route of ROUTES) {
    const m = h.match(route.pattern);
    if (m) {
      matched = route;
      matchResult = m;
      break;
    }
  }

  if (!matched) {
    // Redirect to default
    window.location.hash = '#/dashboard';
    return;
  }

  currentView = matched.view;
  updateNavHighlight(matched.view);

  const container = getContainer();
  container.innerHTML = '<div class="loading-screen"><div class="spinner"></div><p>Cargando...</p></div>';

  try {
    const cleanup = await matched.render(matchResult);
    if (typeof cleanup === 'function') {
      currentCleanup = cleanup;
    }
  } catch (err) {
    console.error('[Router] View render error:', err);
    container.innerHTML = `
      <div class="error-state">
        <div class="error-icon">⚠️</div>
        <h3>Error al cargar la vista</h3>
        <p>${err.message || 'Error desconocido'}</p>
        <button class="btn btn-primary mt-3" onclick="window.location.hash='#/dashboard'">
          Volver al Dashboard
        </button>
      </div>
    `;
  }
}

// ----------------------------------------------------------------
// Init
// ----------------------------------------------------------------
export function initRouter() {
  // Listen for hash changes
  window.addEventListener('hashchange', () => navigate(window.location.hash));

  // Handle initial load
  const initialHash = window.location.hash;
  if (!initialHash || initialHash === '#' || initialHash === '#/') {
    window.location.hash = '#/dashboard';
  } else {
    navigate(initialHash);
  }
}

export function getCurrentView() {
  return currentView;
}

// Programmatic navigation helper
export function navigateTo(path) {
  window.location.hash = path;
}

export default { initRouter, getCurrentView, navigateTo };
