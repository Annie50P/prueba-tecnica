import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as d3 from 'd3';
import { getGrafoNodos, getGrafoRelaciones, getClientes } from '../api/client';
import { renderGrafoD3, NODE_COLORS } from '../components/GrafoD3';

const ALL_NODE_TYPES = ['Cliente', 'Agente', 'Interaccion', 'PromesaPago', 'Pago', 'PlanPago'];

const REL_TYPE_OPTIONS = [
  { value: 'TIENE_INTERACCION', label: 'Interacciones' },
  { value: 'CONDUJO',           label: 'Agente atendió' },
  { value: 'GENERO_PROMESA',    label: 'Promesas' },
  { value: 'GENERO_PAGO',       label: 'Pagos' },
  { value: 'GENERO_PLAN',       label: 'Planes' },
  { value: 'CUMPLE_PROMESA',    label: 'Cumplimientos' },
  { value: 'SIGUIENTE',         label: 'Secuencia' },
];

const REL_GROUP_MAP = {
  TIENE_INTERACCION: ['TIENE_INTERACCION'],
  CONDUJO:           ['CONDUJO'],
  GENERO_PROMESA:    ['GENERO_PROMESA', 'PROMESA_DE'],
  GENERO_PAGO:       ['GENERO_PAGO', 'PAGO_DE'],
  GENERO_PLAN:       ['GENERO_PLAN', 'PLAN_DE'],
  CUMPLE_PROMESA:    ['CUMPLE_PROMESA'],
  SIGUIENTE:         ['SIGUIENTE'],
};

const RESULTADO_OPTIONS = [
  { value: 'promesa_pago',     label: 'Promesa de pago' },
  { value: 'pago_inmediato',   label: 'Pago inmediato' },
  { value: 'sin_respuesta',    label: 'Sin respuesta' },
  { value: 'se_niega_pagar',   label: 'Se niega a pagar' },
  { value: 'renegociacion',    label: 'Renegociación' },
  { value: 'disputa',          label: 'Disputa' },
  { value: 'llamada_saliente', label: 'Llamada saliente' },
  { value: 'llamada_entrante', label: 'Llamada entrante' },
  { value: 'pago_recibido',    label: 'Pago recibido' },
  { value: 'email',            label: 'Email' },
  { value: 'sms',              label: 'SMS' },
];

const NODE_DESC = {
  Cliente:     'Deudor',
  Agente:      'Cobrador',
  Interaccion: 'Llamada / contacto',
  PromesaPago: 'Promesa de pago',
  Pago:        'Pago realizado',
  PlanPago:    'Plan de cuotas',
};

export default function Grafo() {
  const svgRef = useRef(null);
  const controlsRef = useRef(null);

  const [nodeTypes, setNodeTypes] = useState(new Set(ALL_NODE_TYPES));
  const [relTypes, setRelTypes]   = useState(new Set(REL_TYPE_OPTIONS.map(r => r.value)));
  const [clienteId, setClienteId] = useState('');
  const [resultado, setResultado] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [frozen, setFrozen]         = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [counts, setCounts]     = useState({ nodes: 0, edges: 0 });
  const [summary, setSummary]   = useState(null);

  const PROFUNDIDAD = 2;

  const [appliedFilters, setAppliedFilters] = useState({
    nodeTypes: ALL_NODE_TYPES,
    relTypes:  REL_TYPE_OPTIONS.map(r => r.value),
    clienteId: null,
    resultado: '',
    fechaDesde: '',
    fechaHasta: '',
  });

  const { data: clientesData } = useQuery({ queryKey: ['clientes'], queryFn: getClientes });
  const clientes = Array.isArray(clientesData) ? clientesData : (clientesData?.clientes ?? []);

  const expandedRelTypes = appliedFilters.relTypes
    ? appliedFilters.relTypes.flatMap(r => REL_GROUP_MAP[r] ?? [r])
    : null;
  const allExpanded = REL_TYPE_OPTIONS.flatMap(r => REL_GROUP_MAP[r.value]);
  const relFiltered = expandedRelTypes && expandedRelTypes.length < allExpanded.length ? expandedRelTypes : null;

  const { data: nodesData, isLoading: l1 } = useQuery({
    queryKey: ['grafo-nodos', appliedFilters.nodeTypes, !!appliedFilters.clienteId],
    queryFn: () => getGrafoNodos(
      appliedFilters.nodeTypes?.length < ALL_NODE_TYPES.length ? appliedFilters.nodeTypes : null,
      appliedFilters.clienteId ? 2000 : 800
    ),
  });

  const { data: edgesData, isLoading: l2 } = useQuery({
    queryKey: ['grafo-relaciones', relFiltered, appliedFilters.clienteId],
    queryFn: () => getGrafoRelaciones({
      tipos_relacion: relFiltered,
      cliente_id: appliedFilters.clienteId || null,
      profundidad: PROFUNDIDAD,
    }),
  });

  const rawNodes = nodesData?.nodos ?? [];
  const rawEdges = appliedFilters.relTypes.length === 0 ? [] : (edgesData?.enlaces ?? []);
  const loading  = l1 || l2;

  const ROOT_TYPES = new Set(['Cliente', 'Agente']);

  const { nodes, edges } = useMemo(() => {
    const { clienteId: cid, fechaDesde: fd, fechaHasta: fh, resultado: res } = appliedFilters;

    let base = rawNodes;
    if (cid) {
      const subgraphIds = new Set([cid]);
      rawEdges.forEach(e => {
        if (e.source) subgraphIds.add(e.source);
        if (e.target) subgraphIds.add(e.target);
      });
      base = rawNodes.filter(n => subgraphIds.has(n.id));
    }

    if (fd || fh || res) {
      base = base.filter(n => {
        const p  = n.propiedades ?? {};
        const ts = p.timestamp ?? p.fecha ?? p.fecha_promesa ?? p.fecha_inicio ?? '';
        if (fd && ts && ts.slice(0, 10) < fd) return false;
        if (fh && ts && ts.slice(0, 10) > fh) return false;
        if (res && n.tipo === 'Interaccion') {
          const match = (p.resultado ?? '') === res || (p.tipo ?? '') === res;
          if (!match) return false;
        }
        return true;
      });
    }

    const visibleIds = new Set(base.map(n => n.id));
    let filteredEdges = rawEdges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));

    if (fd || fh || res) {
      const connectedIds = new Set();
      filteredEdges.forEach(e => { connectedIds.add(e.source); connectedIds.add(e.target); });
      base = base.filter(n => {
        if (cid && n.id === cid) return true;
        if (ROOT_TYPES.has(n.tipo)) return connectedIds.has(n.id);
        return connectedIds.has(n.id);
      });
      const finalIds = new Set(base.map(n => n.id));
      filteredEdges = filteredEdges.filter(e => finalIds.has(e.source) && finalIds.has(e.target));
    }

    return { nodes: base, edges: filteredEdges };
  }, [rawNodes, rawEdges, appliedFilters]);

  const onNodeClick = useCallback((node, connections) => {
    setSelectedNode({ ...node, connections });
  }, []);

  useEffect(() => {
    if (!svgRef.current || loading || !nodes.length) return;
    if (controlsRef.current) {
      try { controlsRef.current.destroy(); } catch {}
      controlsRef.current = null;
    }
    let cancelled = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (cancelled || !svgRef.current) return;
        const controls = renderGrafoD3(svgRef.current, nodes, edges, onNodeClick);
        controlsRef.current = controls;
        setCounts({ nodes: controls.nodeCount, edges: controls.edgeCount });
        setSummary(controls.summary ?? null);
        setFrozen(false);
      });
    });
    return () => {
      cancelled = true;
      if (controlsRef.current) {
        try { controlsRef.current.destroy(); } catch {}
        controlsRef.current = null;
      }
    };
  }, [nodes, edges, loading, onNodeClick]);

  function applyFilters() {
    setAppliedFilters({
      nodeTypes: [...nodeTypes],
      relTypes:  [...relTypes],
      clienteId: clienteId || null,
      resultado,
      fechaDesde,
      fechaHasta,
    });
  }

  function clearFilters() {
    const def = {
      nodeTypes: ALL_NODE_TYPES,
      relTypes:  REL_TYPE_OPTIONS.map(r => r.value),
      clienteId: null,
      resultado: '',
      fechaDesde: '',
      fechaHasta: '',
    };
    setNodeTypes(new Set(ALL_NODE_TYPES));
    setRelTypes(new Set(REL_TYPE_OPTIONS.map(r => r.value)));
    setClienteId('');
    setResultado('');
    setFechaDesde('');
    setFechaHasta('');
    setAppliedFilters(def);
  }

  function toggleNodeType(t) {
    setNodeTypes(prev => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });
  }

  function toggleRelType(t) {
    setRelTypes(prev => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });
  }

  return (
    <div className="grafo-shell">
      {/* Toolbar top */}
      <div className="grafo-toolbar">
        <select
          value={clienteId}
          onChange={e => setClienteId(e.target.value)}
          className="ds-select"
          style={{ minWidth: 160 }}
        >
          <option value="">Todos los clientes</option>
          {clientes.map(c => (
            <option key={c.id} value={c.id}>{c.nombre ?? c.id}</option>
          ))}
        </select>

        <select
          value={resultado}
          onChange={e => setResultado(e.target.value)}
          className="ds-select"
        >
          <option value="">Resultado: todos</option>
          <optgroup label="Resultado">
            {RESULTADO_OPTIONS.filter(r => ['promesa_pago','pago_inmediato','sin_respuesta','se_niega_pagar','renegociacion','disputa'].includes(r.value)).map(r => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </optgroup>
          <optgroup label="Tipo">
            {RESULTADO_OPTIONS.filter(r => ['llamada_saliente','llamada_entrante','pago_recibido','email','sms'].includes(r.value)).map(r => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </optgroup>
        </select>

        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Desde:</span>
          <input
            type="month"
            value={fechaDesde ? fechaDesde.slice(0, 7) : ''}
            onChange={e => setFechaDesde(e.target.value ? e.target.value + '-01' : '')}
            className="ds-input"
            style={{ width: 130, padding: '5px 8px' }}
          />
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Hasta:</span>
          <input
            type="month"
            value={fechaHasta ? fechaHasta.slice(0, 7) : ''}
            onChange={e => {
              if (!e.target.value) { setFechaHasta(''); return; }
              const [y, m] = e.target.value.split('-').map(Number);
              const lastDay = new Date(y, m, 0).getDate();
              setFechaHasta(`${e.target.value}-${String(lastDay).padStart(2, '0')}`);
            }}
            className="ds-input"
            style={{ width: 130, padding: '5px 8px' }}
          />
        </div>

        <button className="ds-btn ds-btn-primary" onClick={applyFilters}>
          Aplicar
        </button>
        <button className="ds-btn ds-btn-ghost" onClick={clearFilters}>
          Limpiar
        </button>

        {summary && !loading && (
          <div className="grafo-summary-bar" style={{ marginLeft: 'auto', border: 'none', padding: 0, background: 'transparent' }}>
            {summary.clientes > 0    && <span className="grafo-summary-count"><strong>{summary.clientes}</strong> clientes</span>}
            {summary.agentes > 0     && <span className="grafo-summary-count"><strong>{summary.agentes}</strong> agentes</span>}
            {summary.interacciones > 0 && <span className="grafo-summary-count"><strong>{summary.interacciones}</strong> interacc.</span>}
            {summary.promesas > 0    && <span className="grafo-summary-count"><strong>{summary.promesas}</strong> promesas</span>}
            {summary.pagos > 0       && <span className="grafo-summary-count"><strong>{summary.pagos}</strong> pagos</span>}
            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{counts.nodes} nodos · {counts.edges} aristas</span>
          </div>
        )}
      </div>

      {/* Body: legend | canvas | info */}
      <div className="grafo-body">
        {/* Legend left */}
        <div className="grafo-legend">
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
            Tipos de nodo
          </div>
          {ALL_NODE_TYPES.map(t => (
            <label
              key={t}
              style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', cursor: 'pointer' }}
            >
              <input
                type="checkbox"
                className="ds-checkbox"
                checked={nodeTypes.has(t)}
                onChange={() => toggleNodeType(t)}
              />
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: NODE_COLORS[t], flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t}</span>
            </label>
          ))}

          <div style={{ marginTop: 16, borderTop: '1px solid var(--border-soft)', paddingTop: 12 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10 }}>
              Relaciones
            </div>
            {REL_TYPE_OPTIONS.map(r => (
              <label
                key={r.value}
                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', cursor: 'pointer' }}
              >
                <input
                  type="checkbox"
                  className="ds-checkbox"
                  checked={relTypes.has(r.value)}
                  onChange={() => toggleRelType(r.value)}
                />
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{r.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Canvas */}
        <div className="grafo-canvas">
          {loading && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: 'rgba(10,15,30,0.7)', zIndex: 20,
            }}>
              <div style={{
                width: 36, height: 36, border: '3px solid var(--border-medium)',
                borderTopColor: 'var(--accent-primary)', borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }} />
            </div>
          )}

          {/* Canvas controls */}
          <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <button
              className="ds-btn ds-btn-ghost"
              onClick={() => controlsRef.current?.center?.()}
              title="Centrar"
            >
              ⊕
            </button>
            <button
              className={`ds-btn ${frozen ? 'ds-btn-active' : 'ds-btn-ghost'}`}
              onClick={() => {
                if (!controlsRef.current) return;
                if (frozen) controlsRef.current.unfreeze();
                else controlsRef.current.freeze();
                setFrozen(f => !f);
              }}
              title={frozen ? 'Reanudar' : 'Congelar'}
            >
              {frozen ? '▶' : '⏸'}
            </button>
            <button
              className="ds-btn ds-btn-ghost"
              onClick={() => {
                if (!controlsRef.current?.zoom) return;
                const svg = d3.select(svgRef.current);
                svg.transition().duration(500).call(controlsRef.current.zoom.transform, d3.zoomIdentity);
              }}
              title="Reset zoom"
            >
              ↺
            </button>
          </div>

          <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />

          {!loading && nodes.length === 0 && (
            <div className="ds-empty" style={{ position: 'absolute', inset: 0 }}>
              <svg className="ds-empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
              <div className="ds-empty-title">Sin resultados</div>
              <div className="ds-empty-desc">Ajusta los filtros para visualizar el grafo</div>
            </div>
          )}
        </div>

        {/* Right panel: node info */}
        <div className="grafo-info">
          <div className="grafo-info-inner">
            {selectedNode ? (
              <NodeInfoPanel node={selectedNode} />
            ) : (
              <div className="ds-empty" style={{ padding: '32px 12px' }}>
                <svg className="ds-empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                </svg>
                <div className="ds-empty-desc">Clic en un nodo para ver sus propiedades</div>
              </div>
            )}

            {/* Legend descriptions */}
            <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border-soft)' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
                Leyenda
              </div>
              {ALL_NODE_TYPES.map(t => (
                <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
                  <span style={{ width: 10, height: 10, borderRadius: '50%', background: NODE_COLORS[t], flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t}</span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{NODE_DESC[t]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ── Node info panel ───────────────────────────────────────────
function InfoRow({ label, value }) {
  if (value == null || value === '') return null;
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', gap: 8,
      fontSize: 12, padding: '6px 0', borderBottom: '1px solid var(--border-soft)',
    }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ color: 'var(--text-primary)', fontWeight: 500, textAlign: 'right', wordBreak: 'break-all' }}>{value}</span>
    </div>
  );
}

function money(v) {
  if (v == null) return null;
  return `$${Number(v).toLocaleString('es', { minimumFractionDigits: 0 })}`;
}
function pct(v) {
  if (v == null) return null;
  return `${(Number(v) * 100).toFixed(1)}%`;
}
function fmtDate(ts) {
  if (!ts) return null;
  try { return new Date(ts).toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' }); }
  catch { return ts; }
}

function NodeInfoPanel({ node }) {
  const tipo  = node.tipo ?? '?';
  const p     = node.propiedades ?? {};
  const color = NODE_COLORS[tipo] ?? '#4a5568';

  let rows;
  switch (tipo) {
    case 'Cliente':
      rows = (<>
        <InfoRow label="Nombre"        value={p.nombre} />
        <InfoRow label="Teléfono"      value={p.telefono} />
        <InfoRow label="Tipo deuda"    value={p.tipo_deuda} />
        <InfoRow label="Deuda inicial" value={money(p.monto_deuda_inicial)} />
        <InfoRow label="Total pagado"  value={money(p.total_pagado)} />
        <InfoRow label="Pendiente"     value={money(p.monto_pendiente)} />
        <InfoRow label="Cumplimiento"  value={pct(p.tasa_cumplimiento)} />
      </>);
      break;
    case 'Agente':
      rows = (<>
        <InfoRow label="ID"             value={node.id} />
        <InfoRow label="Total llamadas" value={p.total_llamadas} />
        <InfoRow label="Tasa promesa"   value={pct(p.tasa_promesa)} />
        <InfoRow label="Tasa pago inm." value={pct(p.tasa_pago_inmediato)} />
      </>);
      break;
    case 'Interaccion':
      rows = (<>
        <InfoRow label="Tipo"       value={p.tipo} />
        <InfoRow label="Fecha"      value={fmtDate(p.timestamp)} />
        <InfoRow label="Resultado"  value={p.resultado} />
        <InfoRow label="Sentimiento" value={p.sentimiento} />
        <InfoRow label="Duración"   value={p.duracion_segundos != null ? `${p.duracion_segundos}s` : null} />
        <InfoRow label="Agente"     value={p.agente_id} />
        <InfoRow label="Hora"       value={p.hora_del_dia != null ? `${p.hora_del_dia}:00` : null} />
      </>);
      break;
    case 'Pago':
      rows = (<>
        <InfoRow label="Monto"       value={money(p.monto)} />
        <InfoRow label="Método"      value={p.metodo_pago} />
        <InfoRow label="Fecha"       value={fmtDate(p.timestamp)} />
        <InfoRow label="Pago completo" value={p.pago_completo ? 'Sí' : 'No'} />
        <InfoRow label="Cliente"     value={p.cliente_id} />
      </>);
      break;
    case 'PromesaPago':
      rows = (<>
        <InfoRow label="Monto prometido"  value={money(p.monto_prometido)} />
        <InfoRow label="Fecha promesa"    value={p.fecha_promesa} />
        <InfoRow label="Cumplida"         value={p.cumplida ? 'Sí' : 'No'} />
        <InfoRow label="Días vencimiento" value={p.dias_hasta_vencimiento} />
        <InfoRow label="Cliente"          value={p.cliente_id} />
      </>);
      break;
    case 'PlanPago':
      rows = (<>
        <InfoRow label="Cuotas"       value={p.cuotas} />
        <InfoRow label="Monto mensual" value={money(p.monto_mensual)} />
        <InfoRow label="Total plan"   value={money(p.monto_total_plan)} />
        <InfoRow label="Fecha inicio" value={fmtDate(p.fecha_inicio)} />
        <InfoRow label="Cliente"      value={p.cliente_id} />
      </>);
      break;
    default:
      rows = <InfoRow label="ID" value={node.id} />;
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ width: 12, height: 12, borderRadius: '50%', background: color, flexShrink: 0 }} />
        <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{tipo}</span>
      </div>
      <div style={{
        background: 'var(--bg-elevated)', borderRadius: 8, padding: '8px 12px',
        fontSize: 12, marginBottom: 12,
      }}>
        <span style={{ color: 'var(--text-muted)' }}>Conexiones: </span>
        <strong style={{ color: 'var(--text-primary)' }}>{node.connections ?? 0}</strong>
      </div>
      <div>{rows}</div>
    </div>
  );
}
