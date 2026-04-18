/**
 * GrafoD3.js — D3.js v7 force-directed graph renderer (React-compatible)
 */

import * as d3 from 'd3';

// ----------------------------------------------------------------
// Constants
// ----------------------------------------------------------------
export const NODE_COLORS = {
  Cliente:     '#3b82f6',
  Agente:      '#10b981',
  Interaccion: '#f59e0b',
  PromesaPago: '#8b5cf6',
  Pago:        '#06b6d4',
  PlanPago:    '#f97316',
  default:     '#4a5568',
};

const EDGE_COLORS = {
  TIENE_INTERACCION: '#3b82f6',
  CONDUJO:           '#10b981',
  GENERO_PROMESA:    '#8b5cf6',
  PROMESA_DE:        '#a78bfa',
  GENERO_PAGO:       '#06b6d4',
  PAGO_DE:           '#22d3ee',
  GENERO_PLAN:       '#f97316',
  PLAN_DE:           '#fb923c',
  CUMPLE_PROMESA:    '#10b981',
  SIGUIENTE:         '#374151',
  default:           '#374151',
};

const EDGE_LABELS = {
  TIENE_INTERACCION:  'interaccion',
  CONDUJO:            'atendio',
  GENERO_PROMESA:     'promesa',
  PROMESA_DE:         'promesa de',
  GENERO_PAGO:        'pago',
  PAGO_DE:            'pago de',
  GENERO_PLAN:        'plan',
  PLAN_DE:            'plan de',
  CUMPLE_PROMESA:     'cumple',
  SIGUIENTE:          'siguiente',
};

const MAX_NODES = 800;

// ----------------------------------------------------------------
// Main render function
// ----------------------------------------------------------------
export function renderGrafoD3(svgEl, rawNodes, rawEdges, onNodeClick) {
  const nodes = rawNodes.slice(0, MAX_NODES).map(n => ({
    ...n,
    id: String(n.id ?? n.elemento_id ?? n._id ?? Math.random()),
  }));

  const nodeIds = new Set(nodes.map(n => n.id));

  const links = rawEdges
    .filter(e => {
      const src = String(e.source ?? e.origen ?? e.from);
      const tgt = String(e.target ?? e.destino ?? e.to);
      return nodeIds.has(src) && nodeIds.has(tgt);
    })
    .map(e => ({
      ...e,
      source: String(e.source ?? e.origen ?? e.from),
      target: String(e.target ?? e.destino ?? e.to),
      type:   e.type ?? e.tipo ?? e.relacion ?? 'default',
    }));

  const degreeMap = {};
  links.forEach(l => {
    degreeMap[l.source] = (degreeMap[l.source] ?? 0) + 1;
    degreeMap[l.target] = (degreeMap[l.target] ?? 0) + 1;
  });

  const svg = d3.select(svgEl);
  svg.selectAll('*').remove();

  const bbox = svgEl.getBoundingClientRect();
  const W = bbox.width  || 800;
  const H = bbox.height || 600;

  const container = svg.append('g').attr('class', 'graph-container');

  const zoom = d3.zoom()
    .scaleExtent([0.1, 8])
    .on('zoom', (event) => container.attr('transform', event.transform));

  svg.call(zoom).on('dblclick.zoom', null);

  // Arrow markers
  const defs = svg.append('defs');
  const markerTypes = [...new Set(links.map(l => l.type))];
  markerTypes.forEach(type => {
    const color = EDGE_COLORS[type] ?? EDGE_COLORS.default;
    defs.append('marker')
      .attr('id', `arrow-${type}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 18).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', color);
  });

  // Force simulation
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(100).strength(0.4))
    .force('charge', d3.forceManyBody().strength(-250))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(d => nodeRadius(d, degreeMap) + 6));

  // ── Edges ──
  const linkGroup = container.append('g').attr('class', 'links');
  const link = linkGroup.selectAll('line')
    .data(links).join('line')
    .attr('stroke', d => EDGE_COLORS[d.type] ?? EDGE_COLORS.default)
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.6)
    .attr('marker-end', d => `url(#arrow-${d.type})`);

  // ── Edge labels ──
  const edgeLabelGroup = container.append('g').attr('class', 'edge-labels');
  const edgeLabel = edgeLabelGroup.selectAll('text')
    .data(links).join('text')
    .attr('text-anchor', 'middle')
    .attr('font-size', '8px')
    .attr('fill', '#999')
    .attr('pointer-events', 'none')
    .text(d => EDGE_LABELS[d.type] ?? d.type);

  // ── Nodes ──
  const nodeGroup = container.append('g').attr('class', 'nodes');
  const node = nodeGroup.selectAll('g.node-g')
    .data(nodes).join('g')
    .attr('class', 'node-g')
    .style('cursor', 'pointer')
    .call(drag(simulation));

  node.append('circle')
    .attr('r', d => nodeRadius(d, degreeMap))
    .attr('fill', d => nodeColor(d))
    .attr('stroke', 'rgba(255,255,255,0.12)')
    .attr('stroke-width', 1.5);

  // ── Node labels (human-readable) ──
  node.append('text')
    .attr('dy', d => nodeRadius(d, degreeMap) + 12)
    .attr('text-anchor', 'middle')
    .attr('font-size', '10px')
    .attr('fill', '#94a3b8')
    .attr('font-weight', d => (d.tipo === 'Cliente' || d.tipo === 'Agente') ? '600' : '400')
    .attr('pointer-events', 'none')
    .text(d => humanLabel(d));

  // ── Tooltip ──
  let tooltipEl = d3.select('body').select('.d3-tooltip');
  if (tooltipEl.empty()) {
    tooltipEl = d3.select('body').append('div').attr('class', 'd3-tooltip').style('opacity', 0);
  }

  node
    .on('mouseover', function(event, d) {
      tooltipEl.transition().duration(150).style('opacity', 1);
      tooltipEl.html(buildTooltipHtml(d, degreeMap))
        .style('left', `${event.clientX + 12}px`)
        .style('top',  `${event.clientY - 10}px`);
    })
    .on('mousemove', function(event) {
      tooltipEl.style('left', `${event.clientX + 12}px`).style('top', `${event.clientY - 10}px`);
    })
    .on('mouseout', function() {
      tooltipEl.transition().duration(200).style('opacity', 0);
    })
    .on('click', function(event, d) {
      event.stopPropagation();
      node.select('circle')
        .attr('stroke', n => n.id === d.id ? '#3b82f6' : 'rgba(255,255,255,0.12)')
        .attr('stroke-width', n => n.id === d.id ? 2.5 : 1.5);
      if (typeof onNodeClick === 'function') onNodeClick(d, degreeMap[d.id] ?? 0);
    });

  svg.on('click', () => {
    node.select('circle').attr('stroke', 'rgba(255,255,255,0.12)').attr('stroke-width', 1.5);
  });

  // ── Tick ──
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);

    edgeLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 4);

    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  // ── Controls ──
  function centerGraph() {
    const padding = 40;
    const xs = nodes.map(n => n.x).filter(Boolean);
    const ys = nodes.map(n => n.y).filter(Boolean);
    if (!xs.length) return;
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const graphW = maxX - minX || 1;
    const graphH = maxY - minY || 1;
    const scale = Math.min(0.9, (W - padding * 2) / graphW, (H - padding * 2) / graphH);
    const tx = W / 2 - (minX + graphW / 2) * scale;
    const ty = H / 2 - (minY + graphH / 2) * scale;
    svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  }

  function freeze() {
    simulation.stop();
    nodes.forEach(n => { n.fx = n.x; n.fy = n.y; });
  }
  function unfreeze() {
    nodes.forEach(n => { n.fx = null; n.fy = null; });
    simulation.alpha(0.3).restart();
  }
  function destroy() {
    simulation.stop();
    svg.selectAll('*').remove();
    tooltipEl.remove();
  }

  // ── Summary counts (returned so Grafo.jsx can show them) ──
  const summary = {
    clientes: nodes.filter(n => n.tipo === 'Cliente').length,
    agentes: nodes.filter(n => n.tipo === 'Agente').length,
    interacciones: nodes.filter(n => n.tipo === 'Interaccion').length,
    promesas: nodes.filter(n => n.tipo === 'PromesaPago').length,
    pagos: nodes.filter(n => n.tipo === 'Pago').length,
    planes: nodes.filter(n => n.tipo === 'PlanPago').length,
  };

  return { freeze, unfreeze, center: centerGraph, destroy, simulation, zoom, nodeCount: nodes.length, edgeCount: links.length, summary };
}

// ----------------------------------------------------------------
// Human-readable node label (shown below the circle)
// ----------------------------------------------------------------
function humanLabel(d) {
  const tipo = d.tipo ?? '';
  const p = d.propiedades ?? {};

  switch (tipo) {
    case 'Cliente':
      return p.nombre ?? d.label ?? d.id;

    case 'Agente':
      return `Agente ${(d.id ?? '').replace('agente_0', '').replace('agente_', '')}`;

    case 'Interaccion': {
      const tipoInt = p.tipo ?? p.resultado ?? 'llamada';
      const fecha = formatShortDate(p.timestamp);
      return fecha ? `${capitalize(tipoInt)} · ${fecha}` : capitalize(tipoInt);
    }

    case 'Pago': {
      const monto = p.monto != null ? `$${Number(p.monto).toLocaleString('es')}` : '';
      return monto ? `Pago · ${monto}` : 'Pago';
    }

    case 'PromesaPago': {
      const monto = p.monto_prometido != null ? `$${Number(p.monto_prometido).toLocaleString('es')}` : '';
      return monto ? `Promesa · ${monto}` : 'Promesa';
    }

    case 'PlanPago': {
      const cuotas = p.cuotas ?? '?';
      return `Plan · ${cuotas} cuotas`;
    }

    default:
      return d.label ?? d.id ?? '';
  }
}

// ----------------------------------------------------------------
// Tooltip (shown on hover) — human-readable, not JSON dump
// ----------------------------------------------------------------
function buildTooltipHtml(d, degreeMap) {
  const tipo = d.tipo ?? '?';
  const p = d.propiedades ?? {};
  const connections = degreeMap[d.id] ?? 0;
  const color = NODE_COLORS[tipo] ?? NODE_COLORS.default;

  const header = `<div style="font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:6px">
    <span style="width:10px;height:10px;border-radius:50%;background:${color};display:inline-block"></span>
    ${tipo} <span style="opacity:.5;font-weight:400">(${connections} conexiones)</span>
  </div>`;

  let body = '';

  switch (tipo) {
    case 'Cliente':
      body = tooltipRows([
        ['Nombre', p.nombre],
        ['Telefono', p.telefono],
        ['Tipo deuda', p.tipo_deuda],
        ['Deuda inicial', money(p.monto_deuda_inicial)],
        ['Pagado', money(p.total_pagado)],
        ['Pendiente', money(p.monto_pendiente)],
      ]);
      break;

    case 'Agente':
      body = tooltipRows([
        ['ID', d.id],
        ['Total llamadas', p.total_llamadas],
        ['Tasa promesa', pct(p.tasa_promesa)],
        ['Tasa pago inm.', pct(p.tasa_pago_inmediato)],
      ]);
      break;

    case 'Interaccion':
      body = tooltipRows([
        ['Tipo', p.tipo],
        ['Fecha', formatLongDate(p.timestamp)],
        ['Resultado', p.resultado],
        ['Sentimiento', p.sentimiento],
        ['Duracion', p.duracion_segundos != null ? `${p.duracion_segundos}s` : null],
        ['Agente', p.agente_id],
      ]);
      break;

    case 'Pago':
      body = tooltipRows([
        ['Monto', money(p.monto)],
        ['Metodo', p.metodo_pago],
        ['Fecha', formatLongDate(p.timestamp)],
        ['Completo', p.pago_completo ? 'Si' : 'No'],
      ]);
      break;

    case 'PromesaPago':
      body = tooltipRows([
        ['Monto prometido', money(p.monto_prometido)],
        ['Fecha promesa', p.fecha_promesa],
        ['Cumplida', p.cumplida ? 'Si' : 'No'],
        ['Dias vencimiento', p.dias_hasta_vencimiento],
      ]);
      break;

    case 'PlanPago':
      body = tooltipRows([
        ['Cuotas', p.cuotas],
        ['Monto mensual', money(p.monto_mensual)],
        ['Total plan', money(p.monto_total_plan)],
        ['Inicio', formatLongDate(p.fecha_inicio)],
      ]);
      break;

    default:
      body = `<div style="color:#999;font-size:12px">ID: ${d.id}</div>`;
  }

  return header + body;
}

// ----------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------
function nodeRadius(d, degreeMap) {
  const deg = degreeMap[d.id] ?? 0;
  return Math.max(8, Math.min(24, 8 + deg * 1.5));
}

function nodeColor(d) {
  const tipo = d.tipo ?? d.labels?.[0] ?? d.type ?? '';
  return NODE_COLORS[tipo] ?? NODE_COLORS.default;
}

function formatShortDate(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('es', { day: 'numeric', month: 'short' });
  } catch { return ''; }
}

function formatLongDate(ts) {
  if (!ts) return null;
  try {
    const d = new Date(ts);
    return d.toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return ts; }
}

function money(v) {
  if (v == null) return null;
  return `$${Number(v).toLocaleString('es', { minimumFractionDigits: 0 })}`;
}

function pct(v) {
  if (v == null) return null;
  return `${(Number(v) * 100).toFixed(1)}%`;
}

function capitalize(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ');
}

function tooltipRows(pairs) {
  return pairs
    .filter(([, v]) => v != null && v !== '' && v !== undefined)
    .map(([label, val]) => `<div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;line-height:1.6">
      <span style="color:#888">${label}</span>
      <span style="font-weight:500;text-align:right">${val}</span>
    </div>`)
    .join('');
}

function drag(simulation) {
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x; d.fy = event.y;
  }
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
  }
  return d3.drag().on('start', dragstarted).on('drag', dragged).on('end', dragended);
}

export default { renderGrafoD3, NODE_COLORS };
