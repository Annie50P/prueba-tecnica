import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getClientes } from '../api/client';

const SORT_OPTIONS = [
  { key: 'nombre',              label: 'Nombre' },
  { key: 'monto_deuda_inicial', label: 'Deuda Inicial' },
  { key: 'monto_pendiente',     label: 'Pendiente' },
  { key: 'tasa_cumplimiento',   label: 'Cumplimiento' },
];

const TIPO_COLORS = {
  auto:               'bg-blue-50 text-blue-700 border-blue-200',
  hipoteca:           'bg-violet-50 text-violet-700 border-violet-200',
  prestamo_personal:  'bg-amber-50 text-amber-700 border-amber-200',
  tarjeta_credito:    'bg-rose-50 text-rose-700 border-rose-200',
};

function getStatus(c) {
  const pend = c.monto_pendiente ?? 0;
  const ini = c.monto_deuda_inicial ?? 1;
  const ratio = pend / ini;
  if (pend === 0) return { label: 'Liquidado', cls: 'bg-emerald-50 text-emerald-700' };
  if (ratio < 0.3) return { label: 'Casi liquidado', cls: 'bg-blue-50 text-blue-700' };
  if (ratio < 0.7) return { label: 'En proceso', cls: 'bg-amber-50 text-amber-700' };
  return { label: 'Pendiente alto', cls: 'bg-red-50 text-red-700' };
}

export default function Clientes() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState('nombre');
  const [sortAsc, setSortAsc] = useState(true);

  const { data, isLoading } = useQuery({ queryKey: ['clientes'], queryFn: getClientes });
  const clientes = Array.isArray(data) ? data : (data?.clientes ?? []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    let list = clientes.filter(c =>
      (c.nombre ?? '').toLowerCase().includes(q) ||
      (c.id ?? '').toLowerCase().includes(q) ||
      (c.telefono ?? '').toLowerCase().includes(q) ||
      (c.tipo_deuda ?? '').toLowerCase().includes(q)
    );
    list.sort((a, b) => {
      let va = a[sortKey] ?? '', vb = b[sortKey] ?? '';
      if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
      return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
    return list;
  }, [clientes, search, sortKey, sortAsc]);

  function handleSort(key) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  }

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
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-bold text-slate-800">
            Clientes
            <span className="ml-2 text-sm font-normal text-slate-400">({clientes.length})</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">Haz clic en cualquier fila para ver el detalle completo del cliente</p>
        </div>

        {/* Search */}
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Buscar nombre, ID, telefono..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm w-72 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300 bg-white transition-shadow"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/60">
                {[
                  { key: 'nombre', label: 'Cliente', align: 'left' },
                  { key: null, label: 'Tipo Deuda', align: 'left' },
                  { key: 'monto_deuda_inicial', label: 'Deuda Inicial', align: 'right' },
                  { key: null, label: 'Pagado', align: 'right' },
                  { key: 'monto_pendiente', label: 'Pendiente', align: 'right' },
                  { key: 'tasa_cumplimiento', label: 'Cumplimiento', align: 'right' },
                  { key: null, label: 'Estado', align: 'center' },
                ].map((col, i) => (
                  <th
                    key={i}
                    onClick={col.key ? () => handleSort(col.key) : undefined}
                    className={`px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wide ${
                      col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
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
                const cumpl = ((c.tasa_cumplimiento ?? 0) * 100);
                return (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/clientes/${c.id}`)}
                    className="border-t border-slate-100/80 hover:bg-blue-50/40 cursor-pointer transition-colors group"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-800 group-hover:text-blue-700 transition-colors">{c.nombre ?? '--'}</p>
                        <p className="text-[11px] text-slate-400 font-mono">{c.id} &middot; {c.telefono ?? ''}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${TIPO_COLORS[c.tipo_deuda] ?? 'bg-slate-50 text-slate-600 border-slate-200'}`}>
                        {(c.tipo_deuda ?? '--').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-slate-700">${(c.monto_deuda_inicial ?? 0).toLocaleString('es')}</td>
                    <td className="px-4 py-3 text-right text-emerald-600 font-medium">${(c.total_pagado ?? 0).toLocaleString('es')}</td>
                    <td className="px-4 py-3 text-right text-red-500 font-medium">${(c.monto_pendiente ?? 0).toLocaleString('es')}</td>
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
                    <td className="px-4 py-3 text-center">
                      <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${status.cls}`}>
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
            <p className="text-xs mt-1">Intenta con otro termino de busqueda</p>
          </div>
        )}
      </div>
    </div>
  );
}
