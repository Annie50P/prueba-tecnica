import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as d3 from 'd3';
import { getGrafoNodos, getGrafoRelaciones, getClientes } from '../api/client';
import { renderGrafoD3, NODE_COLORS } from '../components/GrafoD3';

const ALL_NODE_TYPES = ['Cliente', 'Agente', 'Interaccion', 'PromesaPago', 'Pago', 'PlanPago'];

const REL_TYPE_OPTIONS = [
  { value: 'TIENE_INTERACCION', label: 'Interacciones' },
  { value: 'CONDUJO',           label: 'Agente atendio' },
  { value: 'GENERO_PROMESA',    label: 'Promesas' },
  { value: 'GENERO_PAGO',       label: 'Pagos' },
  { value: 'GENERO_PLAN',       label: 'Planes' },
  { value: 'CUMPLE_PROMESA',    label: 'Cumplimientos' },
  { value: 'SIGUIENTE',         label: 'Secuencia temporal' },
];
// Backend rel types that correspond to each option (include the inverse)
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
  { value: 'promesa_pago',    label: 'Promesa de pago' },
  { value: 'pago_inmediato',  label: 'Pago inmediato' },
  { value: 'sin_respuesta',   label: 'Sin respuesta' },
  { value: 'se_niega_pagar',  label: 'Se niega a pagar' },
  { value: 'renegociacion',   label: 'Renegociacion' },
  { value: 'disputa',         label: 'Disputa' },
  { value: 'llamada_saliente', label: 'Llamada saliente' },
  { value: 'llamada_entrante', label: 'Llamada entrante' },
  { value: 'pago_recibido',   label: 'Pago recibido' },
  { value: 'email',           label: 'Email' },
  { value: 'sms',             label: 'SMS' },
];

export default function Grafo() {
  const svgRef = useRef(null);
  const controlsRef = useRef(null);

  const [nodeTypes, setNodeTypes] = useState(new Set(ALL_NODE_TYPES));
  const [relTypes, setRelTypes] = useState(new Set(REL_TYPE_OPTIONS.map(r => r.value)));
  const [clienteId, setClienteId] = useState('');
  const [profundidad, setProfundidad] = useState(2);
  const [resultado, setResultado] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [frozen, setFrozen] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [counts, setCounts] = useState({ nodes: 0, edges: 0 });
  const [summary, setSummary] = useState(null);

  const [appliedFilters, setAppliedFilters] = useState({
    nodeTypes: ALL_NODE_TYPES,
    relTypes: REL_TYPE_OPTIONS.map(r => r.value),
    clienteId: null,
    profundidad: 2,
    resultado: '',
    fechaDesde: '',
    fechaHasta: '',
  });

  const { data: clientesData } = useQuery({ queryKey: ['clientes'], queryFn: getClientes });
  const clientes = Array.isArray(clientesData) ? clientesData : (clientesData?.clientes ?? []);

  // Expand selected rel groups to actual backend types
  const expandedRelTypes = appliedFilters.relTypes
    ? appliedFilters.relTypes.flatMap(r => REL_GROUP_MAP[r] ?? [r])
    : null;
  const allExpanded = REL_TYPE_OPTIONS.flatMap(r => REL_GROUP_MAP[r.value]);
  const relFiltered = expandedRelTypes && expandedRelTypes.length < allExpanded.length ? expandedRelTypes : null;

  const { data: nodesData, isLoading: l1 } = useQuery({
    queryKey: ['grafo-nodos', appliedFilters.nodeTypes],
    queryFn: () => getGrafoNodos(
      appliedFilters.nodeTypes?.length < ALL_NODE_TYPES.length ? appliedFilters.nodeTypes : null,
      800
    ),
  });

  const { data: edgesData, isLoading: l2 } = useQuery({
    queryKey: ['grafo-relaciones', relFiltered, appliedFilters.clienteId, appliedFilters.profundidad],
    queryFn: () => getGrafoRelaciones({
      tipos_relacion: relFiltered,
      cliente_id: appliedFilters.clienteId || null,
      profundidad: appliedFilters.profundidad,
    }),
  });

  // Client-side filters: periodo and resultado (applied on nodes before rendering)
  const rawNodes = nodesData?.nodos ?? [];
  const rawEdges = edgesData?.enlaces ?? [];
  const loading = l1 || l2;

  const nodes = useMemo(() => {
    const { fechaDesde: fd, fechaHasta: fh, resultado: res } = appliedFilters;
    if (!fd && !fh && !res) return rawNodes;

    return rawNodes.filter(n => {
      const p = n.propiedades ?? {};
      const ts = p.timestamp ?? p.fecha ?? p.fecha_promesa ?? p.fecha_inicio ?? '';

      // Period filter: only apply to nodes that have a date
      if (fd && ts && ts.slice(0, 10) < fd) return false;
      if (fh && ts && ts.slice(0, 10) > fh) return false;

      // Resultado filter: only apply to Interaccion nodes
      if (res && n.tipo === 'Interaccion') {
        const val = (p.resultado ?? p.tipo ?? '').toLowerCase();
        if (!val.includes(res.toLowerCase())) return false;
      }

      return true;
    });
  }, [rawNodes, appliedFilters.fechaDesde, appliedFilters.fechaHasta, appliedFilters.resultado]);

  const edges = useMemo(() => rawEdges, [rawEdges]);

  const onNodeClick = useCallback((node, connections) => {
    setSelectedNode({ ...node, connections });
  }, []);

  // Render D3 graph
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
      relTypes: [...relTypes],
      clienteId: clienteId || null,
      profundidad,
      resultado,
      fechaDesde,
      fechaHasta,
    });
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
    <div className="flex h-full">
      {/* Left sidebar - Filters */}
      <div className="w-56 bg-white border-r border-slate-200/80 p-4 overflow-y-auto flex-shrink-0 space-y-4">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          <h3 className="font-bold text-sm text-slate-700">Filtros</h3>
        </div>

        {/* Client filter */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase">Cliente</p>
          <select
            value={clienteId}
            onChange={e => setClienteId(e.target.value)}
            className="w-full text-xs border border-gray-200 rounded-md px-2 py-1.5"
          >
            <option value="">Todos</option>
            {clientes.map(c => (
              <option key={c.id} value={c.id}>{c.nombre ?? c.id}</option>
            ))}
          </select>
        </div>

        {/* Depth */}
        {clienteId && (
          <div>
            <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase">Profundidad: {profundidad}</p>
            <input
              type="range" min={1} max={3} value={profundidad}
              onChange={e => setProfundidad(Number(e.target.value))}
              className="w-full"
            />
          </div>
        )}

        {/* Tipo de relacion */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase">Tipo de Relacion</p>
          {REL_TYPE_OPTIONS.map(r => (
            <label key={r.value} className="flex items-center gap-2 text-xs py-0.5 cursor-pointer">
              <input type="checkbox" checked={relTypes.has(r.value)} onChange={() => toggleRelType(r.value)} className="rounded" />
              <span className="text-slate-600">{r.label}</span>
            </label>
          ))}
        </div>

        {/* Periodo */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase">Periodo</p>
          <div className="space-y-1.5">
            <label className="block">
              <span className="text-[10px] text-gray-400">Desde</span>
              <input
                type="date"
                value={fechaDesde}
                onChange={e => setFechaDesde(e.target.value)}
                className="w-full text-xs border border-gray-200 rounded-md px-2 py-1.5"
              />
            </label>
            <label className="block">
              <span className="text-[10px] text-gray-400">Hasta</span>
              <input
                type="date"
                value={fechaHasta}
                onChange={e => setFechaHasta(e.target.value)}
                className="w-full text-xs border border-gray-200 rounded-md px-2 py-1.5"
              />
            </label>
          </div>
        </div>

        {/* Resultado */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase">Resultado</p>
          <select
            value={resultado}
            onChange={e => setResultado(e.target.value)}
            className="w-full text-xs border border-gray-200 rounded-md px-2 py-1.5"
          >
            <option value="">Todos</option>
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
        </div>

        {/* Node types */}
        <div>
          <p className="text-xs font-semibold text-gray-500 mb-1.5 uppercase">Mostrar</p>
          {ALL_NODE_TYPES.map(t => (
            <label key={t} className="flex items-center gap-2 text-xs py-0.5 cursor-pointer">
              <input type="checkbox" checked={nodeTypes.has(t)} onChange={() => toggleNodeType(t)} className="rounded" />
              <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: NODE_COLORS[t] }} />
              <span className="text-slate-700">{t}</span>
            </label>
          ))}
        </div>

        <button onClick={applyFilters} className="w-full bg-gradient-to-br from-slate-700 to-slate-800 text-white text-sm py-2.5 rounded-lg hover:from-slate-600 hover:to-slate-700 transition-all shadow-sm font-medium">
          Aplicar Filtros
        </button>
        <button
          onClick={() => {
            setNodeTypes(new Set(ALL_NODE_TYPES));
            setRelTypes(new Set(REL_TYPE_OPTIONS.map(r => r.value)));
            setClienteId('');
            setProfundidad(2);
            setResultado('');
            setFechaDesde('');
            setFechaHasta('');
            setAppliedFilters({
              nodeTypes: ALL_NODE_TYPES,
              relTypes: REL_TYPE_OPTIONS.map(r => r.value),
              clienteId: null,
              profundidad: 2,
              resultado: '',
              fechaDesde: '',
              fechaHasta: '',
            });
          }}
          className="w-full text-xs text-gray-500 hover:text-slate-700 py-1 transition-colors"
        >
          Limpiar filtros
        </button>
      </div>

      {/* Graph area */}
      <div className="flex-1 relative bg-gray-50 flex flex-col">
        {/* Summary bar */}
        {summary && !loading && (
          <div className="bg-white border-b border-gray-200 px-4 py-2.5 flex items-center gap-4 text-xs text-slate-600 flex-shrink-0">
            {clienteId && (
              <span className="font-semibold text-slate-800">
                {clientes.find(c => c.id === clienteId)?.nombre ?? clienteId}
              </span>
            )}
            {summary.clientes > 0 && <span><span className="font-medium text-slate-800">{summary.clientes}</span> clientes</span>}
            {summary.agentes > 0 && <span><span className="font-medium text-slate-800">{summary.agentes}</span> agentes</span>}
            {summary.interacciones > 0 && <span><span className="font-medium text-slate-800">{summary.interacciones}</span> interacciones</span>}
            {summary.promesas > 0 && <span><span className="font-medium text-slate-800">{summary.promesas}</span> promesas</span>}
            {summary.pagos > 0 && <span><span className="font-medium text-slate-800">{summary.pagos}</span> pagos</span>}
            {summary.planes > 0 && <span><span className="font-medium text-slate-800">{summary.planes}</span> planes</span>}
            <span className="text-gray-400 ml-auto">{counts.nodes} nodos · {counts.edges} aristas</span>
          </div>
        )}

        <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-20">
            <div className="animate-spin w-10 h-10 border-4 border-slate-200 border-t-slate-700 rounded-full" />
          </div>
        )}

        {/* Controls */}
        <div className="absolute top-3 left-3 z-10 flex gap-2">
          <button
            onClick={() => controlsRef.current?.center?.()}
            className="bg-white border border-gray-200 text-xs px-3 py-1.5 rounded-md shadow-sm hover:bg-gray-50"
          >
            Centrar
          </button>
          <button
            onClick={() => {
              if (!controlsRef.current) return;
              if (frozen) { controlsRef.current.unfreeze(); } else { controlsRef.current.freeze(); }
              setFrozen(!frozen);
            }}
            className={`border text-xs px-3 py-1.5 rounded-md shadow-sm ${frozen ? 'bg-slate-800 text-white border-slate-800' : 'bg-white border-gray-200 hover:bg-gray-50'}`}
          >
            {frozen ? 'Reanudar' : 'Congelar'}
          </button>
          <button
            onClick={() => {
              if (!controlsRef.current?.zoom) return;
              const svg = d3.select(svgRef.current);
              svg.transition().duration(500).call(controlsRef.current.zoom.transform, d3.zoomIdentity);
            }}
            className="bg-white border border-gray-200 text-xs px-3 py-1.5 rounded-md shadow-sm hover:bg-gray-50"
          >
            Reset Zoom
          </button>
        </div>

        <svg ref={svgRef} className="w-full h-full" />

        {/* Empty state */}
        {!loading && nodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400">
            <svg className="w-16 h-16 mb-3 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <p className="text-sm font-medium">Sin resultados</p>
            <p className="text-xs mt-1">Ajusta los filtros para visualizar el grafo</p>
          </div>
        )}
        </div>
      </div>

      {/* Right panel - Node info */}
      <div className="w-64 bg-white border-l border-slate-200/80 p-4 overflow-y-auto flex-shrink-0">
        {selectedNode ? (
          <NodeInfoPanel node={selectedNode} />
        ) : (
          <div className="flex flex-col items-center justify-center h-48 text-center text-gray-400">
            <svg className="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" /></svg>
            <p className="text-sm">Clic en un nodo para ver sus propiedades</p>
          </div>
        )}

        {/* Legend */}
        <div className="mt-6 pt-4 border-t border-gray-100">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Leyenda</h4>
          {[
            { type: 'Cliente', desc: 'Deudor' },
            { type: 'Agente', desc: 'Cobrador' },
            { type: 'Interaccion', desc: 'Llamada/contacto' },
            { type: 'PromesaPago', desc: 'Promesa' },
            { type: 'Pago', desc: 'Pago realizado' },
            { type: 'PlanPago', desc: 'Plan de cuotas' },
          ].map(({ type, desc }) => (
            <div key={type} className="flex items-center gap-2 py-0.5">
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: NODE_COLORS[type] }} />
              <span className="text-xs text-slate-600">{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------
// Node info panel — human-readable, not JSON
// ----------------------------------------------------------------
function InfoRow({ label, value }) {
  if (value == null || value === '') return null;
  return (
    <div className="flex justify-between gap-2 text-xs py-1 border-b border-gray-50">
      <span className="text-gray-500">{label}</span>
      <span className="text-slate-700 font-medium text-right">{value}</span>
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
  try {
    return new Date(ts).toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return ts; }
}

function NodeInfoPanel({ node }) {
  const tipo = node.tipo ?? '?';
  const p = node.propiedades ?? {};
  const color = NODE_COLORS[tipo] ?? '#adb5bd';

  let rows = null;

  switch (tipo) {
    case 'Cliente':
      rows = (
        <>
          <InfoRow label="Nombre" value={p.nombre} />
          <InfoRow label="Telefono" value={p.telefono} />
          <InfoRow label="Tipo deuda" value={p.tipo_deuda} />
          <InfoRow label="Fecha prestamo" value={p.fecha_prestamo} />
          <InfoRow label="Deuda inicial" value={money(p.monto_deuda_inicial)} />
          <InfoRow label="Total pagado" value={money(p.total_pagado)} />
          <InfoRow label="Pendiente" value={money(p.monto_pendiente)} />
          <InfoRow label="Cumplimiento" value={pct(p.tasa_cumplimiento)} />
        </>
      );
      break;

    case 'Agente':
      rows = (
        <>
          <InfoRow label="ID" value={node.id} />
          <InfoRow label="Total llamadas" value={p.total_llamadas} />
          <InfoRow label="Tasa promesa" value={pct(p.tasa_promesa)} />
          <InfoRow label="Tasa pago inm." value={pct(p.tasa_pago_inmediato)} />
        </>
      );
      break;

    case 'Interaccion':
      rows = (
        <>
          <InfoRow label="Tipo" value={p.tipo} />
          <InfoRow label="Fecha" value={fmtDate(p.timestamp)} />
          <InfoRow label="Resultado" value={p.resultado} />
          <InfoRow label="Sentimiento" value={p.sentimiento} />
          <InfoRow label="Duracion" value={p.duracion_segundos != null ? `${p.duracion_segundos}s` : null} />
          <InfoRow label="Agente" value={p.agente_id} />
          <InfoRow label="Hora" value={p.hora_del_dia != null ? `${p.hora_del_dia}:00` : null} />
        </>
      );
      break;

    case 'Pago':
      rows = (
        <>
          <InfoRow label="Monto" value={money(p.monto)} />
          <InfoRow label="Metodo" value={p.metodo_pago} />
          <InfoRow label="Fecha" value={fmtDate(p.timestamp)} />
          <InfoRow label="Pago completo" value={p.pago_completo ? 'Si' : 'No'} />
          <InfoRow label="Cliente" value={p.cliente_id} />
        </>
      );
      break;

    case 'PromesaPago':
      rows = (
        <>
          <InfoRow label="Monto prometido" value={money(p.monto_prometido)} />
          <InfoRow label="Fecha promesa" value={p.fecha_promesa} />
          <InfoRow label="Cumplida" value={p.cumplida ? 'Si' : 'No'} />
          <InfoRow label="Dias vencimiento" value={p.dias_hasta_vencimiento} />
          <InfoRow label="Cliente" value={p.cliente_id} />
        </>
      );
      break;

    case 'PlanPago':
      rows = (
        <>
          <InfoRow label="Cuotas" value={p.cuotas} />
          <InfoRow label="Monto mensual" value={money(p.monto_mensual)} />
          <InfoRow label="Total plan" value={money(p.monto_total_plan)} />
          <InfoRow label="Fecha inicio" value={fmtDate(p.fecha_inicio)} />
          <InfoRow label="Cliente" value={p.cliente_id} />
        </>
      );
      break;

    default:
      rows = <InfoRow label="ID" value={node.id} />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="w-4 h-4 rounded-full flex-shrink-0" style={{ background: color }} />
        <h3 className="font-bold text-sm text-slate-800">{tipo}</h3>
      </div>
      <div className="bg-gray-50 rounded-md px-3 py-2 text-sm">
        <span className="text-gray-500">Conexiones:</span>{' '}
        <span className="font-medium">{node.connections ?? 0}</span>
      </div>
      <div>{rows}</div>
    </div>
  );
}
