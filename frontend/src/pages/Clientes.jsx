import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getClientes } from '../api/client';
import Badge from '../components/ui/Badge';
import MiniBar from '../components/ui/MiniBar';
import DataCard from '../components/ui/DataCard';

const TIPO_LABEL = {
  auto:              'Auto',
  hipoteca:          'Hipoteca',
  prestamo_personal: 'Personal',
  tarjeta_credito:   'T. Crédito',
};

const SENT_COLOR = {
  cooperativo: 'var(--state-success)',
  neutral:     'var(--text-muted)',
  frustrado:   'var(--state-warning)',
  hostil:      'var(--state-danger)',
};

function getStatus(c) {
  const rec   = c.tasa_recuperacion ?? 0;
  const dias  = c.dias_sin_contacto ?? 0;
  const cumpl = c.tasa_cumplimiento;
  const tieneProm = cumpl !== null && cumpl !== undefined;

  if (rec >= 1)                              return 'Liquidado';
  if (rec >= 0.7)                            return 'Buen pagador';
  if (tieneProm && cumpl < 0.3 && rec < 0.5) return 'Alto riesgo';
  if (dias > 30 && rec < 0.7)               return 'Sin gestión';
  if (rec >= 0.3)                            return 'En proceso';
  return 'Pendiente alto';
}

function diasLabel(d) {
  if (d == null) return '--';
  if (d === 0)   return 'Hoy';
  if (d === 1)   return 'Ayer';
  if (d < 7)     return `${d}d`;
  if (d < 30)    return `${Math.floor(d / 7)}sem`;
  return `${Math.floor(d / 30)}m`;
}

function diasColor(d) {
  if (d == null || d <= 7) return 'var(--state-success)';
  if (d <= 30)             return 'var(--state-warning)';
  return 'var(--state-danger)';
}

function pct(n) {
  if (n == null) return '--';
  return `${(n * 100).toFixed(1)}%`;
}

const ALL_ESTADOS = ['Liquidado', 'Buen pagador', 'En proceso', 'Pendiente alto', 'Sin gestión', 'Alto riesgo'];
const ALL_TIPOS   = ['auto', 'hipoteca', 'prestamo_personal', 'tarjeta_credito'];

const SORT_COLS = [
  { key: 'nombre',              label: 'Cliente',         align: 'left'   },
  { key: null,                  label: 'Tipo',            align: 'left'   },
  { key: 'monto_deuda_inicial', label: 'Deuda',           align: 'right'  },
  { key: null,                  label: 'Pagado',          align: 'right'  },
  { key: 'monto_pendiente',     label: 'Pendiente',       align: 'right'  },
  { key: 'tasa_recuperacion',   label: 'Recuperación',    align: 'left',  width: 160 },
  { key: 'tasa_cumplimiento',   label: 'Promesas',        align: 'center' },
  { key: 'dias_sin_contacto',   label: 'Último contacto', align: 'center' },
  { key: null,                  label: 'Sentimiento',     align: 'center' },
  { key: null,                  label: 'Estado',          align: 'center' },
];

function ChevronIcon({ up }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d={up ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
    </svg>
  );
}

export default function Clientes() {
  const navigate = useNavigate();
  const [search,       setSearch]       = useState('');
  const [sortKey,      setSortKey]      = useState('nombre');
  const [sortAsc,      setSortAsc]      = useState(true);
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
        (c.tipo_deuda ?? '').replace(/_/g, ' ').toLowerCase().includes(q);
      const matchEstado = !filterEstado || getStatus(c) === filterEstado;
      const matchTipo   = !filterTipo   || c.tipo_deuda === filterTipo;
      return matchSearch && matchEstado && matchTipo;
    });
    list.sort((a, b) => {
      let va = a[sortKey] ?? '', vb = b[sortKey] ?? '';
      if (typeof va === 'number') return sortAsc ? va - vb : vb - va;
      return sortAsc
        ? String(va).localeCompare(String(vb), 'es', { sensitivity: 'base' })
        : String(vb).localeCompare(String(va), 'es', { sensitivity: 'base' });
    });
    return list;
  }, [clientes, search, sortKey, sortAsc, filterEstado, filterTipo]);

  function handleSort(key) {
    if (!key) return;
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(true); }
  }

  const estadoCounts = useMemo(() =>
    clientes.reduce((acc, c) => {
      const s = getStatus(c);
      acc[s] = (acc[s] ?? 0) + 1;
      return acc;
    }, {}),
  [clientes]);

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-7xl mx-auto">
        <div className="ds-skeleton h-10" />
        {[...Array(8)].map((_, i) => <div key={i} className="ds-skeleton h-14" />)}
      </div>
    );
  }

  const hasFilters = filterEstado || filterTipo || search;

  return (
    <div className="space-y-4 max-w-7xl mx-auto">
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        {/* Search */}
        <div style={{ position: 'relative', flex: '1 1 220px', maxWidth: 320 }}>
          <svg
            style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', width: 14, height: 14, color: 'var(--text-muted)' }}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar nombre, ID o tipo..."
            className="ds-input"
            style={{ paddingLeft: 32 }}
          />
        </div>

        {/* Estado filter */}
        <select
          value={filterEstado}
          onChange={e => setFilterEstado(e.target.value)}
          className="ds-select"
        >
          <option value="">Estado: todos</option>
          {ALL_ESTADOS.filter(e => estadoCounts[e]).map(e => (
            <option key={e} value={e}>{e} ({estadoCounts[e] ?? 0})</option>
          ))}
        </select>

        {/* Tipo filter */}
        <select
          value={filterTipo}
          onChange={e => setFilterTipo(e.target.value)}
          className="ds-select"
        >
          <option value="">Tipo: todos</option>
          {ALL_TIPOS.map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>

        {hasFilters && (
          <button
            className="ds-btn ds-btn-ghost"
            onClick={() => { setSearch(''); setFilterEstado(''); setFilterTipo(''); }}
          >
            ✕ Limpiar
          </button>
        )}

        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          {filtered.length === clientes.length
            ? `${clientes.length} clientes`
            : `${filtered.length} de ${clientes.length}`}
        </span>
      </div>

      {/* Status chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {ALL_ESTADOS.filter(e => estadoCounts[e]).map(est => (
          <button
            key={est}
            onClick={() => setFilterEstado(filterEstado === est ? '' : est)}
            className={`ds-btn ${filterEstado === est ? 'ds-btn-active' : 'ds-btn-ghost'}`}
            style={{ fontSize: 11, padding: '4px 10px' }}
          >
            {est}
            <span style={{ opacity: 0.6, marginLeft: 4 }}>{estadoCounts[est] ?? 0}</span>
          </button>
        ))}
      </div>

      {/* Table */}
      <DataCard flush>
        <div className="ds-table-wrap">
          <table className="ds-table">
            <thead>
              <tr>
                {SORT_COLS.map((col, i) => (
                  <th
                    key={i}
                    onClick={col.key ? () => handleSort(col.key) : undefined}
                    className={col.key ? 'ds-th-sortable' : ''}
                    style={{ width: col.width }}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      {col.label}
                      {col.key && sortKey === col.key && (
                        <ChevronIcon up={sortAsc} />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => {
                const status = getStatus(c);
                const sent   = c.sentimiento_predominante;
                const cumpl  = c.tasa_cumplimiento;

                return (
                  <tr key={c.id} onClick={() => navigate(`/clientes/${c.id}`)}>
                    {/* Cliente */}
                    <td>
                      <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{c.nombre ?? '--'}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: 1 }}>
                        {c.id}
                      </div>
                    </td>

                    {/* Tipo */}
                    <td>
                      <span style={{
                        fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)',
                        background: 'var(--bg-elevated)', padding: '2px 8px', borderRadius: 4,
                      }}>
                        {TIPO_LABEL[c.tipo_deuda] ?? c.tipo_deuda ?? '--'}
                      </span>
                    </td>

                    {/* Deuda */}
                    <td className="right" style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                      ${(c.monto_deuda_inicial ?? 0).toLocaleString('es')}
                    </td>

                    {/* Pagado */}
                    <td className="right" style={{ color: 'var(--state-success)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                      ${(c.total_pagado ?? 0).toLocaleString('es')}
                    </td>

                    {/* Pendiente */}
                    <td className="right" style={{ color: 'var(--state-danger)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                      ${(c.monto_pendiente ?? 0).toLocaleString('es')}
                    </td>

                    {/* Recuperación */}
                    <td style={{ minWidth: 160 }}>
                      <MiniBar value={c.tasa_recuperacion} color="var(--state-success)" />
                    </td>

                    {/* Cumplimiento promesas */}
                    <td className="center">
                      {cumpl == null ? (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>
                      ) : (
                        <span style={{
                          fontSize: 12, fontWeight: 700, fontVariantNumeric: 'tabular-nums',
                          color: cumpl >= 0.5 ? 'var(--state-success)' : cumpl > 0 ? 'var(--state-warning)' : 'var(--state-danger)',
                        }}>
                          {pct(cumpl)}
                        </span>
                      )}
                    </td>

                    {/* Último contacto */}
                    <td className="center">
                      <span style={{
                        fontSize: 12, fontWeight: 600,
                        color: diasColor(c.dias_sin_contacto),
                      }}>
                        {diasLabel(c.dias_sin_contacto)}
                      </span>
                    </td>

                    {/* Sentimiento */}
                    <td className="center">
                      {sent ? (
                        <span style={{ fontSize: 12, color: SENT_COLOR[sent] ?? 'var(--text-muted)', fontWeight: 500 }}>
                          {sent}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>

                    {/* Estado */}
                    <td className="center">
                      <Badge label={status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="ds-empty">
              <svg className="ds-empty-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <div className="ds-empty-title">No se encontraron clientes</div>
              <div className="ds-empty-desc">Intenta con otro término o limpia los filtros</div>
            </div>
          )}
        </div>
      </DataCard>
    </div>
  );
}
