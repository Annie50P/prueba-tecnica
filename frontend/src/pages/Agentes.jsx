import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getAgentes } from '../api/client';

function RingChart({ value, max = 100, size = 48, stroke = 4, color = '#00d4ff' }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(value / max, 1);
  return (
    <svg width={size} height={size} className="flex-shrink-0">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
        strokeDasharray={`${circ * pct} ${circ * (1 - pct)}`}
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

export default function Agentes() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({ queryKey: ['agentes'], queryFn: getAgentes });

  const agentes = Array.isArray(data) ? data : (data?.agentes ?? []);

  if (isLoading) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-40" />)}
        </div>
      </div>
    );
  }

  // Sort by total_llamadas desc
  const sorted = [...agentes].sort((a, b) => (b.total_llamadas ?? 0) - (a.total_llamadas ?? 0));

  return (
    <div className="poll-container poll-space">
      <div>
        <h1 className="text-lg font-bold text-slate-800">
          Agentes
          <span className="ml-2 text-sm font-normal text-slate-400">({agentes.length})</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">Rendimiento de cada agente de cobranza. Haz clic para ver detalle</p>
      </div>

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
                  {(a.nombre ?? a.id ?? '?').replace('agente_0', '').replace('agente_', '').slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-slate-800 group-hover:text-blue-700 transition-colors truncate">{a.nombre ?? a.id}</h3>
                  <p className="text-[11px] text-slate-400">{a.id} &middot; {a.total_llamadas ?? 0} llamadas</p>
                </div>
                {idx === 0 && (
                  <span className="text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">TOP</span>
                )}
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

      {agentes.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <p className="text-sm">No se encontraron agentes</p>
        </div>
      )}
    </div>
  );
}
