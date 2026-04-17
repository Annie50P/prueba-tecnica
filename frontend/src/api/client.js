import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Clientes ─────────────────────────────────────────────
export const getClientes = () => api.get('/clientes').then(r => r.data);
export const getClienteDetalle = (id) => api.get(`/clientes/${id}`).then(r => r.data);
export const getClienteTimeline = (id) => api.get(`/clientes/${id}/timeline`).then(r => r.data);

// ── Agentes ──────────────────────────────────────────────
export const getAgentes = () => api.get('/agentes').then(r => r.data);
export const getAgenteEfectividad = (id) => api.get(`/agentes/${id}/efectividad`).then(r => r.data);

// ── Analytics ────────────────────────────────────────────
export const getDashboard = () => api.get('/analytics/dashboard').then(r => r.data);
export const getPromesasIncumplidas = () => api.get('/analytics/promesas-incumplidas').then(r => r.data);
export const getMejoresHorarios = () => api.get('/analytics/mejores-horarios').then(r => r.data);

// ── Grafo ────────────────────────────────────────────────
export const getGrafoNodos = (tipos = null, limite = 800) => {
  const params = new URLSearchParams();
  if (tipos?.length) tipos.forEach(t => params.append('tipos', t));
  params.set('limite', limite);
  return api.get(`/grafo/nodos?${params}`).then(r => r.data);
};

export const getGrafoRelaciones = ({ tipos_relacion, cliente_id, profundidad } = {}) => {
  const params = new URLSearchParams();
  if (tipos_relacion?.length) tipos_relacion.forEach(t => params.append('tipos_relacion', t));
  if (cliente_id) params.set('cliente_id', cliente_id);
  if (profundidad) params.set('profundidad', profundidad);
  return api.get(`/grafo/relaciones?${params}`).then(r => r.data);
};

// ── Analytics Avanzado (ML — may take longer) ───────────
export const getPrediccion = () => api.get('/analytics/prediccion', { timeout: 30000 }).then(r => r.data);
export const getAnomalias = () => api.get('/analytics/anomalias', { timeout: 30000 }).then(r => r.data);
export const getEstrategias = () => api.get('/analytics/estrategias', { timeout: 30000 }).then(r => r.data);

// ── MCP / Chat ───────────────────────────────────────────
export const queryMcp = (query) =>
  api.post('/mcp/query', { query }, { timeout: 60000 }).then(r => r.data);

// ── Health ───────────────────────────────────────────────
export const checkHealth = () => api.get('/health').then(r => r.data).catch(() => null);

export default api;
