import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAgenteEfectividad, getAgentes } from '../api/client';
import {
  BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';

const RESULT_COLORS = {
  promesa_pago:    '#ff9100',
  pago_inmediato:  '#00e676',
  renegociacion:   '#00d4ff',
  sin_respuesta:   '#b0bec5',
  se_niega_pagar:  '#ff1744',
  disputa:         '#d500f9',
};
const SENT_COLORS = {
  cooperativo: '#00e676',
  neutral:     '#90a4ae',
  frustrado:   '#ff9100',
  hostil:      '#ff1744',
  'n/a':       '#cfd8dc',
};

function fmt(n, decimals = 1) {
  return n == null ? '--' : Number(n).toFixed(decimals);
}
function pct(n) {
  return n == null ? '--' : `${(n * 100).toFixed(1)}%`;
}
function money(n) {
  if (n == null) return '--';
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
}

function KpiCard({ label, value, color = 'text-slate-800', sub }) {
  return (
    <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-100">
      <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function ChartPanel({ title, sub, children }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm">
      <div className="px-5 pt-5 pb-2">
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        {sub && <p className="text-[11px] text-slate-400">{sub}</p>}
      </div>
      <div className="px-3 pb-4">{children}</div>
    </div>
  );
}

// Tooltip personalizado que muestra % sobre el total
function ResultTooltip({ active, payload, total }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0].payload;
  const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
  return (
    <div className="bg-white border border-slate-200 rounded-lg px-3 py-2 shadow text-xs">
      <p className="font-semibold text-slate-700">{name}</p>
      <p className="text-slate-500">{value} llamadas <span className="text-slate-400">({pct}%)</span></p>
    </div>
  );
}

export default function AgenteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: agente, isLoading } = useQuery({
    queryKey: ['agente-efectividad', id],
    queryFn: () => getAgenteEfectividad(id),
  });

  // Para calcular ranking comparativo
  const { data: todosAgentes } = useQuery({
    queryKey: ['agentes'],
    queryFn: getAgentes,
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

  // ── Datos derivados ──────────────────────────────────────
  const resultados = agente.distribucion_resultados
    ? Object.entries(agente.distribucion_resultados).map(([name, value]) => ({
        name: name.replace(/_/g, ' '),
        value,
        fill: RESULT_COLORS[name] ?? '#94a3b8',
      }))
    : [];

  const sentimientos = agente.distribucion_sentimientos
    ? Object.entries(agente.distribucion_sentimientos).map(([name, value]) => ({
        name,
        value,
        fill: SENT_COLORS[name] ?? '#94a3b8',
      }))
    : [];

  const totalResultados = resultados.reduce((s, r) => s + r.value, 0) || 1;

  // Ranking: posición en tasa_exito respecto al equipo
  let rankingLabel = null;
  if (todosAgentes?.length > 1) {
    const sorted = [...todosAgentes].sort(
      (a, b) =>
        (b.tasa_promesa + b.tasa_pago_inmediato) -
        (a.tasa_promesa + a.tasa_pago_inmediato)
    );
    const pos = sorted.findIndex((a) => a.id === id) + 1;
    rankingLabel = `#${pos} de ${sorted.length}`;
  }

  const actividadHoraria = agente.actividad_por_hora ?? [];
  const tendenciaSemanal = agente.tendencia_semanal ?? [];

  return (
    <div className="poll-container poll-space">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/agentes')}
          className="mt-1 text-slate-400 hover:text-slate-700 transition-colors p-1 -ml-1"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-slate-600 to-slate-800 flex items-center justify-center text-white font-bold text-sm shadow-sm">
            {(agente.nombre ?? agente.id ?? '?')
              .replace('agente_0', '')
              .replace('agente_', '')
              .slice(0, 2)
              .toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">{agente.nombre ?? agente.id}</h1>
            <p className="text-xs text-slate-400">{agente.id} · Rendimiento y análisis de llamadas</p>
          </div>
        </div>
      </div>

      {/* KPIs primarios */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Total Llamadas"   value={agente.total_llamadas ?? 0} />
        <KpiCard label="Tasa Éxito"       value={pct(agente.tasa_exito)}    color="text-emerald-600"
                 sub="promesa + pago inmediato" />
        <KpiCard label="Monto Prometido" value={money(agente.monto_prometido_total)} color="text-blue-700"
                 sub="suma de compromisos generados" />
        <KpiCard label="Ranking Equipo"   value={rankingLabel ?? '--'}      color="text-violet-600"
                 sub="por tasa de éxito" />
      </div>

      {/* KPIs secundarios */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Tasa Promesa"    value={pct(agente.tasa_promesa)}         color="text-amber-600" />
        <KpiCard label="Tasa Pago Inm."  value={pct(agente.tasa_pago_inmediato)}  color="text-teal-600" />
        <KpiCard label="Tasa Fracaso"    value={pct(agente.tasa_fracaso)}         color="text-red-500"
                 sub="negación + sin respuesta" />
        <KpiCard
          label="Cumplimiento Promesas"
          value={agente.tasa_cumplimiento_promesas != null ? pct(agente.tasa_cumplimiento_promesas) : '--'}
          color="text-indigo-600"
          sub={agente.promesas_generadas ? `${agente.promesas_generadas} generadas` : undefined}
        />
      </div>

      {/* Fila 1: Resultados + Actividad horaria */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPanel
          title="Distribución de Resultados"
          sub={`${totalResultados} interacciones totales`}
        >
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={resultados} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#64748b' }} width={130} />
              <Tooltip content={<ResultTooltip total={totalResultados} />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {resultados.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Actividad por Hora del Día"
          sub={agente.mejor_horario ? `Mejor franja: ${agente.mejor_horario}` : 'Distribución de llamadas y éxitos'}
        >
          {actividadHoraria.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={actividadHoraria}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="hora" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip
                  formatter={(v, name) => [v, name === 'total' ? 'Llamadas' : 'Éxitos']}
                  labelFormatter={(l) => `Hora: ${l}`}
                />
                <Legend formatter={(v) => v === 'total' ? 'Llamadas' : 'Éxitos'} />
                <Bar dataKey="total"  fill="#94a3b8" radius={[3, 3, 0, 0]} />
                <Bar dataKey="exitos" fill="#00e676" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-400 text-sm">Sin datos horarios</div>
          )}
        </ChartPanel>
      </div>

      {/* Fila 2: Sentimientos + Tendencia semanal */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartPanel
          title="Distribución de Sentimientos"
          sub="Percepción del cliente durante las llamadas"
        >
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={sentimientos}
                cx="50%" cy="50%"
                innerRadius={55} outerRadius={95}
                dataKey="value"
                paddingAngle={2}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              >
                {sentimientos.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip formatter={(v, name) => [v, name]} />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel
          title="Tendencia Semanal"
          sub="Evolución de llamadas y éxitos por semana"
        >
          {tendenciaSemanal.length > 1 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={tendenciaSemanal}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="semana" tick={{ fontSize: 9, fill: '#94a3b8' }} />
                <YAxis yAxisId="left"  tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                       tick={{ fontSize: 10, fill: '#94a3b8' }} domain={[0, 1]} />
                <Tooltip
                  formatter={(v, name) =>
                    name === 'tasa_exito'
                      ? [`${(v * 100).toFixed(1)}%`, 'Tasa éxito']
                      : [v, name === 'total' ? 'Llamadas' : 'Éxitos']
                  }
                />
                <Legend formatter={(v) =>
                  v === 'total' ? 'Llamadas' : v === 'exitos' ? 'Éxitos' : 'Tasa éxito'
                } />
                <Line yAxisId="left"  type="monotone" dataKey="total"     stroke="#94a3b8" strokeWidth={2} dot={false} />
                <Line yAxisId="left"  type="monotone" dataKey="exitos"    stroke="#00e676" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="tasa_exito" stroke="#ff9100" strokeWidth={2} strokeDasharray="4 2" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
              {tendenciaSemanal.length === 1
                ? 'Solo hay datos de una semana — el gráfico aparecerá cuando haya más histórico'
                : 'Sin datos de tendencia'}
            </div>
          )}
        </ChartPanel>
      </div>
    </div>
  );
}
