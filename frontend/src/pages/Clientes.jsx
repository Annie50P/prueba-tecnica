import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getClientes } from '../api/client';

const SORT_OPTIONS = [
  { key: 'nombre',                  label: 'Nombre' },
  { key: 'monto_deuda_inicial',     label: 'Deuda' },
  { key: 'monto_pendiente',         label: 'Pendiente' },
  { key: 'tasa_cumplimiento',       label: 'Cumplimiento' },
  { key: 'dias_sin_contacto',       label: 'Sin contacto' },
  { key: 'total_llamadas',          label: 'Llamadas' },
];

const TIPO_COLORS = {
  auto:               'bg-blue-50 text-blue-700 border-blue-200',
  hipoteca:           'bg-violet-50 text-violet-700 border-violet-200',
  prestamo_personal:  'bg-amber-50 text-amber-700 border-amber-200',
  tarjeta_credito:    'bg-rose-50 text-rose-700 border-rose-200',
};

const SENT_COLORS = {
  cooperativo: 'text-emerald-600',
  neutral:     'text-slate-500',
  frustrado:   'text-amber-600',
  hostil:      'text-red-600',
};

// Estado enriquecido: ratio deuda + días sin contacto + tasa cumplimiento
function getStatus(c) {
  const pend  = c.monto_pendiente ?? 0;
  const ini   = c.monto_deuda_inicial ?? 1;
  const ratio = pend / ini;
  const dias  = c.dias_sin_contacto ?? 0;
  const cumpl = c.tasa_cumplimiento ?? 1;

  if (pend === 0)
    return { label: 'Liquidado',       cls: 'bg-emerald-50 text-emerald-700' };
  if (ratio < 0.3)
    return { label: 'Casi liquidado',  cls: 'bg-blue-50 text-blue-700' };
  if (ratio >= 0.5 && cumpl < 0.25 && (c.total_llamadas ?? 0) > 2)
    return { label: 'Alto riesgo',     cls: 'bg-red-100 text-red-800' };
  if (dias > 60 && ratio >= 0.5)
    return { label: 'Sin gestión',     cls: 'bg-orange-50 text-orange-700' };
  if (ratio < 0.7)
    return { label: 'En proceso',      cls: 'bg-amber-50 text-amber-700' };
  return   { label: 'Pendiente alto',  cls: 'bg-red-50 text-red-700' };
}

const ALL_ESTADOS = ['Liquidado', 'Casi liquidado', 'En proceso', 'Pendiente alto', 'Sin gestión', 'Alto riesgo'];
const ALL_TIPOS   = ['auto', 'hipoteca', 'prestamo_personal', 'tarjeta_credito'];

function diasLabel(d) {
  if (d == null) return '--';
  if (d === 0)   return 'Hoy';
  if (d === 1)   return 'Ayer';
  if (d < 7)     return `${d}d`;
  if (d < 30)    return `${Math.floor(d / 7)}sem`;
  return `${Math.floor(d / 30)}m`;
}

function diasColor(d) {
  if (d == null || d <= 7)  return 'text-emerald-600';
  if (d <= 30)              return 'text-amber-600';
  return 'text-red-500';
}

export default function Clientes() {
  const navigate = useNavigate();
  const [search,     setSearch]     = useState('');
  const [sortKey,    setSortKey]    = useState('nombre');
  const [sortAsc,    setSortAsc]    = useState(true);
  const [filterEstado, setFilterEstado] = useState('');
  const [filterTipo,   setFilterTipo]   = useState('');

  const { data, isLoading } = useQuery({ queryKey: ['clientes'], queryFn: getClientes });
  const clientes = Array.isArray(data) ? data : (data?.clientes ?? []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    let list = clientes.filter(c => {
      const matchSearch =
        (c.nombre ?? '').toLowerCase().includes(q) ||
        (c.id ?? '').toLowerCase().includes(q) ||
        (c.telefono ?? '').toLowerCase().includes(q) ||
        (c.tipo_deuda ?? '').toLowerCase().includes(q);
      const matchEstado = !filterEstado || getStatus(c).label === filterEstado;
      const matchTipo   = !filterTipo   || c.tipo_deuda === filterTipo;
      return matchSearch && matchEstado && matchTipo;
    });
    list.sort((a, b) => {
      let va = a[sortKey] ?? '', vb = b[sortKey] ?? '';
      if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
      return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
    return list;
  }, [clientes, search, sortKey, sortAsc, filterEstado, filterTipo]);

  function handleSort(key) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  }

  // Conteos por estado para el resumen
  const estadoCounts = useMemo(() =>
    clientes.reduce((acc, c) => {
      const s = getStatus(c).label;
      acc[s] = (acc[s] ?? 0) + 1;
      return acc;
    }, {}),
  [clientes]);

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto space-y-4">
        {[...Array(8)].map((_, i) => <div key={i} className="skeleton h-14" />)}
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-bold text-slate-800">
            Clientes
            <span className="ml-2 text-sm font-normal text-slate-400">({clientes.length})</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">Haz clic en cualquier fila para ver el detalle completo</p>
        </div>
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Buscar nombre, ID, teléfono..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm w-72 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300 bg-white transition-shadow"
          />
        </div>
      </div>

      {/* Resumen por estado (chips clickables como filtro rápido) */}
      <div className="flex flex-wrap gap-2">
        {ALL_ESTADOS.map(est => {
          const n = estadoCounts[est] ?? 0;
          if (n === 0) return null;
          const active = filterEstado === est;
          return (
            <button
              key={est}
              onClick={() => setFilterEstado(active ? '' : est)}
              className={`text-xs px-3 py-1 rounded-full border font-medium transition-colors ${
                active
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
              }`}
            >
              {est} <span className={active ? 'text-slate-300' : 'text-slate-400'}>{n}</span>
            </button>
          );
        })}
        {/* Filtro tipo deuda */}
        <div className="ml-auto flex gap-1">
          <select
            value={filterTipo}
            onChange={e => setFilterTipo(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2 py-1 bg-white text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            <option value="">Todos los tipos</option>
            {ALL_TIPOS.map(t => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
          {(filterEstado || filterTipo) && (
            <button
              onClick={() => { setFilterEstado(''); setFilterTipo(''); }}
              className="text-xs px-2 py-1 text-slate-400 hover:text-slate-700 border border-slate-200 rounded-lg bg-white"
            >
              ✕ Limpiar
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/60">
                {[
                  { key: 'nombre',              label: 'Cliente',        align: 'left'   },
                  { key: null,                  label: 'Tipo Deuda',     align: 'left'   },
                  { key: 'monto_deuda_inicial', label: 'Deuda Inicial',  align: 'right'  },
                  { key: null,                  label: 'Pagado',         align: 'right'  },
                  { key: 'monto_pendiente',     label: 'Pendiente',      align: 'right'  },
                  { key: 'tasa_cumplimiento',   label: 'Cumplimiento',   align: 'right'  },
                  { key: 'total_llamadas',      label: 'Llamadas',       align: 'center' },
                  { key: 'dias_sin_contacto',   label: 'Último contacto',align: 'center' },
                  { key: null,                  label: 'Sentimiento',    align: 'center' },
                  { key: null,                  label: 'Estado',         align: 'center' },
                ].map((col, i) => (
                  <th
                    key={i}
                    onClick={col.key ? () => handleSort(col.key) : undefined}
                    className={`px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide whitespace-nowrap ${
                      col.align === 'right'  ? 'text-right'  :
                      col.align === 'center' ? 'text-center' : 'text-left'
                    } ${col.key ? 'cursor-pointer hover:text-slate-700 select-none' : ''}`}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {col.key && sortKey === col.key && (
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d={sortAsc ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
                        </svg>
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => {
                const status = getStatus(c);
                const cumpl  = (c.tasa_cumplimiento ?? 0) * 100;
                const sent   = c.sentimiento_predominante;
                return (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/clientes/${c.id}`)}
                    className="border-t border-slate-100/80 hover:bg-blue-50/40 cursor-pointer transition-colors group"
                  >
                    {/* Cliente */}
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-800 group-hover:text-blue-700 transition-colors whitespace-nowrap">{c.nombre ?? '--'}</p>
                      <p className="text-[11px] text-slate-400 font-mono">{c.id} · {c.telefono ?? ''}</p>
                    </td>

                    {/* Tipo deuda */}
                    <td className="px-4 py-3">
                      <span className={`text-[11px] font-medium px-2 py-0.5 rounded border whitespace-nowrap ${TIPO_COLORS[c.tipo_deuda] ?? 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                        {(c.tipo_deuda ?? '--').replace(/_/g, ' ')}
                      </span>
                    </td>

                    {/* Deuda inicial */}
                    <td className="px-4 py-3 text-right font-medium text-slate-700 tabular-nums">
                      ${(c.monto_deuda_inicial ?? 0).toLocaleString('es')}
                    </td>

                    {/* Pagado */}
                    <td className="px-4 py-3 text-right text-emerald-600 font-medium tabular-nums">
                      ${(c.total_pagado ?? 0).toLocaleString('es')}
                    </td>

                    {/* Pendiente */}
                    <td className="px-4 py-3 text-right text-red-500 font-medium tabular-nums">
                      ${(c.monto_pendiente ?? 0).toLocaleString('es')}
                    </td>

                    {/* Cumplimiento */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2.5">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all ${cumpl >= 50 ? 'bg-emerald-500' : cumpl > 0 ? 'bg-amber-400' : 'bg-red-400'}`}
                            style={{ width: `${Math.min(100, cumpl)}%` }}
                          />
                        </div>
                        <span className={`font-semibold text-xs tabular-nums ${cumpl >= 50 ? 'text-emerald-600' : cumpl > 0 ? 'text-amber-600' : 'text-red-500'}`}>
                          {cumpl.toFixed(0)}%
                        </span>
                      </div>
                    </td>

                    {/* Llamadas */}
                    <td className="px-4 py-3 text-center">
                      <span className="text-sm font-semibold text-slate-700">{c.total_llamadas ?? 0}</span>
                    </td>

                    {/* Último contacto */}
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-semibold ${diasColor(c.dias_sin_contacto)}`}>
                        {diasLabel(c.dias_sin_contacto)}
                      </span>
                    </td>

                    {/* Sentimiento predominante */}
                    <td className="px-4 py-3 text-center">
                      {sent ? (
                        <span className={`text-xs font-medium capitalize ${SENT_COLORS[sent] ?? 'text-slate-500'}`}>
                          {sent}
                        </span>
                      ) : (
                        <span className="text-slate-300 text-xs">--</span>
                      )}
                    </td>

                    {/* Estado */}
                    <td className="px-4 py-3 text-center">
                      <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${status.cls}`}>
                        {status.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <svg className="w-12 h-12 mx-auto mb-3 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-sm font-medium">No se encontraron clientes</p>
            <p className="text-xs mt-1">Intenta con otro término de búsqueda o limpia los filtros</p>
          </div>
        )}
      </div>

      {/* Pie: total filtrado */}
      {filtered.length > 0 && filtered.length < clientes.length && (
        <p className="text-xs text-slate-400 text-right">
          Mostrando {filtered.length} de {clientes.length} clientes
        </p>
      )}
    </div>
  );
}
