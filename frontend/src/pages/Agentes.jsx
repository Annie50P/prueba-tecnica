import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getAgentes } from '../api/client';

const SORT_OPTIONS = [
  { key: 'tasa_exito',         label: 'Tasa Éxito' },
  { key: 'tasa_promesa',       label: 'Promesa' },
  { key: 'tasa_pago_inmediato',label: 'Pago Inm.' },
  { key: 'total_llamadas',     label: 'Llamadas' },
];

function pct(n) { return n == null ? '--' : `${(n * 100).toFixed(1)}%`; }

function RingChart({ value, max = 100, size = 48, stroke = 4, color = '#00d4ff' }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const p = Math.min(value / max, 1);
  return (
    <svg width={size} height={size} className="flex-shrink-0">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeDasharray={`${circ * p} ${circ * (1 - p)}`}
        strokeLinecap="round" transform={`rotate(-90 ${size/2} ${size/2})`}
        className="transition-all duration-500"
      />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
        className="text-[10px] font-bold fill-slate-700">
        {value.toFixed(0)}%
      </text>
    </svg>
  );
}

// Barra de progreso horizontal para la tabla de ranking
function MiniBar({ value, color }) {
  const pct = Math.min((value ?? 0) * 100, 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-1.5 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-semibold text-slate-700 w-10 text-right">{pct.toFixed(1)}%</span>
    </div>
  );
}

const RANK_COLORS = ['#f59e0b', '#94a3b8', '#b45309'];
const RANK_LABELS = ['1°', '2°', '3°'];

export default function Agentes() {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState('tasa_exito');

  const { data, isLoading } = useQuery({ queryKey: ['agentes'], queryFn: getAgentes });
  const agentes = Array.isArray(data) ? data : (data?.agentes ?? []);

  if (isLoading) {
    return (
      <div className="p-6 max-w-6xl mx-auto space-y-4">
        <div className="skeleton h-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-40" />)}
        </div>
      </div>
    );
  }

  // Derivar tasa_exito para cada agente (suma de tasa_promesa + tasa_pago_inmediato, cap 1)
  const withExito = agentes.map((a) => ({
    ...a,
    tasa_exito: Math.min((a.tasa_promesa ?? 0) + (a.tasa_pago_inmediato ?? 0), 1),
  }));

  const sorted = [...withExito].sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0));

  return (
    <div className="poll-container poll-space">
      <div>
        <h1 className="text-lg font-bold text-slate-800">
          Agentes
          <span className="ml-2 text-sm font-normal text-slate-400">({agentes.length})</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">Ranking y rendimiento de cada agente. Haz clic en una fila o tarjeta para ver el detalle.</p>
      </div>

      {/* ── Ranking table ─────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
        {/* Cabecera con selector de métrica */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Ranking del Equipo</h2>
          <div className="flex gap-1">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setSortKey(opt.key)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                  sortKey === opt.key
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-500 hover:bg-slate-100'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tabla */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[11px] text-slate-400 uppercase tracking-wide bg-slate-50/60">
                <th className="px-5 py-2.5 text-left w-10">#</th>
                <th className="px-3 py-2.5 text-left">Agente</th>
                <th className="px-3 py-2.5 text-left min-w-[140px]">Tasa Éxito</th>
                <th className="px-3 py-2.5 text-left min-w-[120px]">Promesas</th>
                <th className="px-3 py-2.5 text-left min-w-[120px]">Pago Inm.</th>
                <th className="px-3 py-2.5 text-right">Llamadas</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {sorted.map((a, idx) => (
                <tr
                  key={a.id}
                  onClick={() => navigate(`/agentes/${a.id}`)}
                  className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                >
                  {/* Posición */}
                  <td className="px-5 py-3">
                    <span
                      className="text-xs font-bold"
                      style={{ color: RANK_COLORS[idx] ?? '#cbd5e1' }}
                    >
                      {RANK_LABELS[idx] ?? `${idx + 1}°`}
                    </span>
                  </td>

                  {/* Nombre */}
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-white font-bold text-[10px] flex-shrink-0">
                        {(a.nombre ?? a.id ?? '?')
                          .replace('agente_0', '').replace('agente_', '')
                          .slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-800 group-hover:text-blue-700 transition-colors text-xs leading-tight">
                          {a.nombre ?? a.id}
                        </p>
                        <p className="text-[10px] text-slate-400">{a.id}</p>
                      </div>
                    </div>
                  </td>

                  {/* Tasa éxito */}
                  <td className="px-3 py-3">
                    <MiniBar value={a.tasa_exito} color="#00e676" />
                  </td>

                  {/* Tasa promesa */}
                  <td className="px-3 py-3">
                    <MiniBar value={a.tasa_promesa} color="#ff9100" />
                  </td>

                  {/* Tasa pago inmediato */}
                  <td className="px-3 py-3">
                    <MiniBar value={a.tasa_pago_inmediato} color="#00d4ff" />
                  </td>

                  {/* Llamadas */}
                  <td className="px-3 py-3 text-right">
                    <span className="text-sm font-semibold text-slate-700">{a.total_llamadas ?? 0}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Cards ─────────────────────────────────────────── */}
      <div>
        <p className="text-xs text-slate-400 mb-3 font-medium uppercase tracking-wide">Vista de tarjetas</p>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sorted.map((a, idx) => {
            const tasaProm = (a.tasa_promesa ?? 0) * 100;
            const tasaPago = (a.tasa_pago_inmediato ?? 0) * 100;
            return (
              <div
                key={a.id}
                onClick={() => navigate(`/agentes/${a.id}`)}
                className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5 cursor-pointer card-hover group"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-white font-bold text-sm shadow-sm">
                    {(a.nombre ?? a.id ?? '?')
                      .replace('agente_0', '').replace('agente_', '')
                      .slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-800 group-hover:text-blue-700 transition-colors truncate">
                      {a.nombre ?? a.id}
                    </h3>
                    <p className="text-[11px] text-slate-400">{a.id} · {a.total_llamadas ?? 0} llamadas</p>
                  </div>
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                    style={{
                      color: RANK_COLORS[idx] ?? '#94a3b8',
                      borderColor: RANK_COLORS[idx] ?? '#e2e8f0',
                      backgroundColor: `${RANK_COLORS[idx] ?? '#94a3b8'}15`,
                    }}
                  >
                    {RANK_LABELS[idx] ?? `#${idx + 1}`}
                  </span>
                </div>

                <div className="flex items-center justify-around">
                  <div className="text-center">
                    <RingChart value={tasaProm} color="#ff9100" />
                    <p className="text-[10px] text-slate-500 mt-1">Promesas</p>
                  </div>
                  <div className="text-center">
                    <RingChart value={tasaPago} color="#00e676" />
                    <p className="text-[10px] text-slate-500 mt-1">Pago Inm.</p>
                  </div>
                  <div className="text-center">
                    <div className="w-12 h-12 flex items-center justify-center">
                      <span className="text-xl font-bold text-slate-700">{a.total_llamadas ?? 0}</span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-1">Llamadas</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {agentes.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <p className="text-sm">No se encontraron agentes</p>
        </div>
      )}
    </div>
  );
}
