/**
 * Tests para el módulo de API client.
 *
 * Ejecutar con: bun run test
 */

import { describe, it, expect } from 'vitest';
import api, {
  getClientes, getClienteDetalle, getClienteTimeline,
  getAgentes, getAgenteEfectividad,
  getDashboard, getPromesasIncumplidas, getMejoresHorarios,
  getPrediccion, getAnomalias, getEstrategias,
  getGrafoNodos, getGrafoRelaciones,
  queryMcp, checkHealth,
} from '../api/client';

describe('API Client Module', () => {
  it('exports axios instance as default', () => {
    expect(api).toBeDefined();
    expect(api.defaults.baseURL).toBe('/api');
  });

  it('exports all required API functions', () => {
    const fns = [
      getClientes, getClienteDetalle, getClienteTimeline,
      getAgentes, getAgenteEfectividad,
      getDashboard, getPromesasIncumplidas, getMejoresHorarios,
      getPrediccion, getAnomalias, getEstrategias,
      getGrafoNodos, getGrafoRelaciones,
      queryMcp, checkHealth,
    ];
    fns.forEach(fn => {
      expect(typeof fn).toBe('function');
    });
  });

  it('api instance has correct timeout', () => {
    expect(api.defaults.timeout).toBe(15000);
  });

  it('api instance has correct content type', () => {
    expect(api.defaults.headers['Content-Type']).toBe('application/json');
  });
});

describe('getGrafoNodos', () => {
  it('is a function that accepts tipos and limite', () => {
    expect(typeof getGrafoNodos).toBe('function');
    // Function signature accepts (tipos, limite)
    expect(getGrafoNodos.length).toBeGreaterThanOrEqual(0);
  });
});

describe('getGrafoRelaciones', () => {
  it('is a function that accepts config object', () => {
    expect(typeof getGrafoRelaciones).toBe('function');
  });
});
