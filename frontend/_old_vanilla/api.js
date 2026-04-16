/**
 * api.js — Fetch wrapper for the Call Pattern Analyzer API
 * Base URL is read from window.API_CONFIG.baseUrl
 */

const BASE_URL = () => window.API_CONFIG?.baseUrl ?? 'http://localhost:8001';

// ----------------------------------------------------------------
// Internal fetch helper
// ----------------------------------------------------------------
async function apiFetch(path, options = {}) {
  const url = `${BASE_URL()}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Error desconocido');
      throw new ApiError(response.status, errorText, path);
    }

    return await response.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) throw err;
    if (err.name === 'AbortError') throw new ApiError(0, 'Tiempo de espera agotado', path);
    throw new ApiError(0, 'No se pudo conectar con la API', path);
  }
}

// ----------------------------------------------------------------
// Custom error class
// ----------------------------------------------------------------
export class ApiError extends Error {
  constructor(status, message, path) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.path = path;
  }
}

// ----------------------------------------------------------------
// Health check
// ----------------------------------------------------------------
export async function checkApiHealth() {
  try {
    await apiFetch('/');
    return true;
  } catch {
    try {
      await apiFetch('/docs');
      return true;
    } catch {
      return false;
    }
  }
}

// ----------------------------------------------------------------
// Clientes
// ----------------------------------------------------------------

/** Returns list of all clients */
export async function getClientes() {
  return apiFetch('/clientes');
}

// ----------------------------------------------------------------
// Agentes
// ----------------------------------------------------------------

/** Returns list of all agents with metrics */
export async function getAgentes() {
  return apiFetch('/agentes');
}

/** Returns detailed performance metrics for a specific agent */
export async function getAgenteEfectividad(id) {
  return apiFetch(`/agentes/${encodeURIComponent(id)}/efectividad`);
}

/** Returns timeline interactions for a specific client */
export async function getClienteTimeline(id) {
  return apiFetch(`/clientes/${encodeURIComponent(id)}/timeline`);
}

// ----------------------------------------------------------------
// Analytics
// ----------------------------------------------------------------

/** Returns dashboard KPIs and aggregated stats */
export async function getDashboard() {
  return apiFetch('/analytics/dashboard');
}

/** Returns list of unfulfilled promises */
export async function getPromesasIncumplidas() {
  return apiFetch('/analytics/promesas-incumplidas');
}

/** Returns best call times per client/segment */
export async function getMejoresHorarios() {
  return apiFetch('/analytics/mejores-horarios');
}

// ----------------------------------------------------------------
// Graph
// ----------------------------------------------------------------

/**
 * Returns graph nodes
 * @param {string[]|null} tipos - Optional array of node types to filter
 * @param {number} limite - Max nodes to return (default 200 for perf)
 */
export async function getGrafoNodos(tipos = null, limite = 200) {
  const params = new URLSearchParams();
  if (tipos && tipos.length > 0) tipos.forEach(t => params.append('tipos', t));
  if (limite) params.set('limite', limite);
  const qs = params.toString();
  return apiFetch(`/grafo/nodos${qs ? `?${qs}` : ''}`);
}

/**
 * Returns graph relationships/edges
 * @param {Object} params - Optional filters { tipos_relacion, cliente_id, profundidad }
 */
export async function getGrafoRelaciones(params = {}) {
  const sp = new URLSearchParams();
  if (params.tipos_relacion) params.tipos_relacion.forEach(t => sp.append('tipos_relacion', t));
  if (params.cliente_id) sp.set('cliente_id', params.cliente_id);
  if (params.profundidad) sp.set('profundidad', params.profundidad);
  const qs = sp.toString();
  return apiFetch(`/grafo/relaciones${qs ? `?${qs}` : ''}`);
}

export default {
  getClientes,
  getClienteTimeline,
  getAgentes,
  getAgenteEfectividad,
  getDashboard,
  getPromesasIncumplidas,
  getMejoresHorarios,
  getGrafoNodos,
  getGrafoRelaciones,
  checkApiHealth,
};
