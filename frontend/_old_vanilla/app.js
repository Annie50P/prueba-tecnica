/**
 * app.js — Application bootstrap
 * Initializes router, API health checks, and global UI behaviors
 */

import { initRouter } from './router.js';
import { checkApiHealth } from './api.js';

// ----------------------------------------------------------------
// API Status Indicator
// ----------------------------------------------------------------
const DOT  = () => document.querySelector('.status-dot');
const TEXT = () => document.querySelector('.status-text');
const BANNER = () => document.getElementById('api-banner');
const RETRY  = () => document.getElementById('retry-btn');

let apiAvailable = null;
let healthCheckInterval = null;

async function updateApiStatus() {
  const dot  = DOT();
  const text = TEXT();
  if (dot) { dot.className = 'status-dot checking'; }
  if (text) text.textContent = 'Conectando...';

  const ok = await checkApiHealth();
  apiAvailable = ok;

  if (dot) dot.className = `status-dot ${ok ? 'online' : 'offline'}`;
  if (text) text.textContent = ok ? 'API conectada' : 'API no disponible';

  const banner = BANNER();
  if (banner) banner.classList.toggle('hidden', ok);

  return ok;
}

function startHealthChecks() {
  // Initial check
  updateApiStatus();

  // Periodic checks every 30 seconds
  healthCheckInterval = setInterval(updateApiStatus, 30000);
}

// ----------------------------------------------------------------
// Retry button
// ----------------------------------------------------------------
function setupRetryButton() {
  const btn = RETRY();
  if (!btn) return;
  btn.addEventListener('click', async () => {
    btn.textContent = 'Verificando...';
    btn.disabled = true;
    await updateApiStatus();
    btn.textContent = 'Reintentar';
    btn.disabled = false;
    if (apiAvailable) {
      // Reload current view
      const event = new HashChangeEvent('hashchange');
      window.dispatchEvent(event);
    }
  });
}

// ----------------------------------------------------------------
// Bootstrap
// ----------------------------------------------------------------
function bootstrap() {
  startHealthChecks();
  setupRetryButton();
  initRouter();
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
