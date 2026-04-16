import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAgenteEfectividad } from '../api/client';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';

const RESULT_COLORS = {
  promesa_pago: '#ff9100',
  pago_inmediato: '#00e676',
  renegociacion: '#00d4ff',
  sin_respuesta: '#b0bec5',
  se_niega_pagar: '#ff1744',
  disputa: '#d500f9',
};
const SENT_COLORS = {
  cooperativo: '#00e676',
  neutral: '#90a4ae',
  frustrado: '#ff9100',
  hostil: '#ff1744',
  'n/a': '#cfd8dc',
};

export default function AgenteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: agente, isLoading } = useQuery({
    queryKey: ['agente-efectividad', id],
    queryFn: () => getAgenteEfectividad(id),
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <div className="skeleton h-16" />
        <div className="grid grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <div key={i} className="skeleton h-20" />)}</div>
        <div className="grid grid-cols-2 gap-6"><div className="skeleton h-72" /><div className="skeleton h-72" /></div>
      </div>
    );
  }

  if (!agente) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-400">
        <p className="font-medium">Agente no encontrado</p>
        <button onClick={() => navigate('/agentes')} className="mt-3 text-blue-600 hover:underline text-sm">Volver</button>
      </div>
    );
  }

  const resultados = agente.distribucion_resultados
    ? Object.entries(agente.distribucion_resultados).map(([name, value]) => ({ name: name.replace(/_/g, ' '), value, fill: RESULT_COLORS[name] ?? '#94a3b8' }))
    : [];

  const sentimientos = agente.distribucion_sentimientos
    ? Object.entries(agente.distribucion_sentimientos).map(([name, value]) => ({ name, value, fill: SENT_COLORS[name] ?? '#94a3b8' }))
    : [];

  const totalResultados = resultados.reduce((s, r) => s + r.value, 0) || 1;

  return (
    <div className="poll-container poll-space">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button onClick={() => navigate('/agentes')} className="mt-1 text-slate-400 hover:text-slate-700 transition-colors p-1 -ml-1">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-white font-bold text-sm shadow-sm">
            {(agente.nombre ?? agente.id ?? '?').replace('agente_0', '').replace('agente_', '').slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">{agente.nombre ?? agente.id}</h1>
            <p className="text-xs text-slate-400">{agente.id} &middot; Efectividad y distribucion de resultados</p>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Llamadas', value: agente.total_llamadas ?? 0, color: 'text-slate-800' },
          { label: 'Tasa Promesa', value: `${((agente.tasa_promesa ?? 0) * 100).toFixed(1)}%`, color: 'text-amber-600' },
          { label: 'Tasa Pago Inm.', value: `${((agente.tasa_pago_inmediato ?? 0) * 100).toFixed(1)}%`, color: 'text-emerald-600' },
          { label: 'Mejor Horario', value: agente.mejor_horario ? `${agente.mejor_horario}:00 h` : '--', color: 'text-violet-600' },
        ].map((kpi, i) => (
          <div key={i} className="bg-slate-50/80 rounded-xl p-4 border border-slate-100">
            <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-1">{kpi.label}</p>
            <p className={`text-xl font-bold ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Resultados */}
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm">
          <div className="px-5 pt-5 pb-2">
            <h2 className="text-sm font-semibold text-slate-700">Distribucion de Resultados</h2>
            <p className="text-[11px] text-slate-400">{totalResultados} interacciones totales</p>
          </div>
          <div className="px-3 pb-4">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={resultados} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#64748b' }} width={120} />
                <Tooltip formatter={(v) => [v, 'Cantidad']} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {resultados.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sentimientos */}
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm">
          <div className="px-5 pt-5 pb-2">
            <h2 className="text-sm font-semibold text-slate-700">Distribucion de Sentimientos</h2>
            <p className="text-[11px] text-slate-400">Percepcion del cliente durante llamadas</p>
          </div>
          <div className="px-3 pb-4">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={sentimientos} cx="50%" cy="50%" innerRadius={55} outerRadius={95} dataKey="value" paddingAngle={2}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}>
                  {sentimientos.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
