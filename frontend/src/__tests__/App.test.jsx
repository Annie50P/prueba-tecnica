/**
 * Tests para verificar módulos de la app importan correctamente.
 */

import { describe, it, expect } from 'vitest';

describe('Page Modules', () => {
  it('Dashboard exports a default function', async () => {
    const mod = await import('../pages/Dashboard');
    expect(typeof mod.default).toBe('function');
  });

  it('Clientes exports a default function', async () => {
    const mod = await import('../pages/Clientes');
    expect(typeof mod.default).toBe('function');
  });

  it('Analisis exports a default function', async () => {
    const mod = await import('../pages/Analisis');
    expect(typeof mod.default).toBe('function');
  });

  it('Chat exports a default function', async () => {
    const mod = await import('../pages/Chat');
    expect(typeof mod.default).toBe('function');
  });
});

describe('Component Modules', () => {
  it('Layout exports a default function', async () => {
    const mod = await import('../components/Layout');
    expect(typeof mod.default).toBe('function');
  });

  it('GrafoD3 exports renderGrafoD3 and NODE_COLORS', async () => {
    const mod = await import('../components/GrafoD3');
    expect(typeof mod.renderGrafoD3).toBe('function');
    expect(mod.NODE_COLORS).toBeDefined();
    expect(typeof mod.NODE_COLORS.Cliente).toBe('string');
    expect(typeof mod.NODE_COLORS.Agente).toBe('string');
  });
});
