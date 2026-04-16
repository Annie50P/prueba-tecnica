import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPrediccion, getAnomalias, getEstrategias } from '../api/client';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

const TABS = [
  { id: 'prediccion',  label: 'Analisis Predictivo',         icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { id: 'anomalias',   label: 'Deteccion de Anomalias',      icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z' },
  { id: 'estrategias', label: 'Optimizacion de Estrategias', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
];

const RISK_COLORS = { alto: '#ff1744', medio: '#ff9100', bajo: '#00e676' };
const SEV_COLORS = { alta: '#ff1744', media: '#ff9100', baja: '#00d4ff' };
const SEG_COLORS = ['#00e676', '#00d4ff', '#ff9100', '#ff1744'];

export default function Analisis() {
  const [tab, setTab] = useState('prediccion');
  const navigate = useNavigate();

  const { data: prediccion, isLoading: l1, error: e1 } = useQuery({
    queryKey: ['prediccion'], queryFn: getPrediccion, retry: 1, staleTime: 5 * 60 * 1000,
  });
  const { data: anomalias, isLoading: l2, error: e2 } = useQuery({
    queryKey: ['anomalias'], queryFn: getAnomalias, retry: 1, staleTime: 5 * 60 * 1000,
  });
  const { data: estrategias, isLoading: l3, error: e3 } = useQuery({
    queryKey: ['estrategias'], queryFn: getEstrategias, retry: 1, staleTime: 5 * 60 * 1000,
  });

  const loading = (tab === 'prediccion' && l1) || (tab === 'anomalias' && l2) || (tab === 'estrategias' && l3);
  const error = (tab === 'prediccion' && e1) || (tab === 'anomalias' && e2) || (tab === 'estrategias' && e3);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-medium transition-all ${
              tab === t.id
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d={t.icon} />
            </svg>
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="animate-spin w-10 h-10 border-4 border-slate-200 border-t-blue-500 rounded-full" />
          <p className="text-sm text-slate-400">Ejecutando modelos de ML...</p>
        </div>
      )}

      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <svg className="w-10 h-10 mx-auto mb-2 text-red-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-red-600 font-medium mb-1">Error al cargar datos</p>
          <p className="text-sm text-red-500">
            {error?.message?.includes('Network Error')
              ? 'No se pudo conectar con el servidor. Verifica que el backend este corriendo en el puerto 8001.'
              : error?.response?.data?.detail || error?.message || 'Error desconocido'}
          </p>
        </div>
      )}

      {tab === 'prediccion' && !l1 && prediccion && <PrediccionTab data={prediccion} navigate={navigate} />}
      {tab === 'anomalias' && !l2 && anomalias && <AnomaliasTab data={anomalias} />}
      {tab === 'estrategias' && !l3 && estrategias && <EstrategiasTab data={estrategias} navigate={navigate} />}
    </div>
  );
}

// ─── Prediccion ──────────────────────────────────────────

function PrediccionTab({ data, navigate }) {
  const clientes = Array.isArray(data) ? data : [];
  const modelInfo = clientes[0]?._modelo;

  const riskDistribution = [
    { name: 'Alto', value: clientes.filter(c => c.categoria_riesgo === 'alto').length, fill: RISK_COLORS.alto },
    { name: 'Medio', value: clientes.filter(c => c.categoria_riesgo === 'medio').length, fill: RISK_COLORS.medio },
    { name: 'Bajo', value: clientes.filter(c => c.categoria_riesgo === 'bajo').length, fill: RISK_COLORS.bajo },
  ];

  const top10 = clientes.slice(0, 10);

  const featureData = modelInfo?.feature_importances
    ? Object.entries(modelInfo.feature_importances)
        .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value: Math.round(value * 100) }))
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <div className="space-y-5">
      {/* Model banner */}
      {modelInfo && (
        <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200/60 rounded-xl p-4">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                <p className="text-[11px] font-semibold text-indigo-700 uppercase tracking-wide">Modelo ML</p>
              </div>
              <p className="text-sm text-indigo-900 font-semibold">{modelInfo.modelo} ({modelInfo.n_estimators} arboles)</p>
            </div>
            <div className="flex gap-5">
              <div className="text-center">
                <p className="text-xl font-bold text-indigo-700">{modelInfo.accuracy_train}%</p>
                <p className="text-[10px] text-indigo-500">Accuracy</p>
              </div>
              {modelInfo.cross_validation && (
                <div className="text-center">
                  <p className="text-xl font-bold text-indigo-700">{modelInfo.cross_validation.accuracy_mean}%</p>
                  <p className="text-[10px] text-indigo-500">CV {modelInfo.cross_validation.folds}-fold</p>
                </div>
              )}
            </div>
          </div>
          {modelInfo.label_criteria && (
            <div className="mt-3 pt-3 border-t border-indigo-200/60 flex flex-wrap gap-1.5">
              {modelInfo.label_criteria.map((c, i) => (
                <span key={i} className="text-[11px] bg-white/80 text-indigo-700 px-2 py-0.5 rounded-md border border-indigo-200/60">{c}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {riskDistribution.map(r => (
          <div key={r.name} className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5 card-hover">
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="w-3 h-3 rounded-full" style={{ background: r.fill }} />
              <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium">Riesgo {r.name}</p>
            </div>
            <p className="text-3xl font-bold text-slate-800">{r.value}</p>
            <p className="text-[11px] text-slate-400 mt-0.5">clientes</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Risk pie */}
        <ChartBox title="Distribucion de Riesgo">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={riskDistribution} cx="50%" cy="50%" innerRadius={50} outerRadius={85} dataKey="value" paddingAngle={3}
                label={({ name, value }) => `${name}: ${value}`}>
                {riskDistribution.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
              <Tooltip /><Legend wrapperStyle={{ fontSize: '11px' }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartBox>

        {/* Top 10 */}
        <ChartBox title="Top 10 Clientes por Riesgo">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={top10} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis dataKey="nombre" type="category" tick={{ fontSize: 9, fill: '#64748b' }} width={80} />
              <Tooltip formatter={(v) => [`${v}%`, 'Score']} />
              <Bar dataKey="score_riesgo" radius={[0, 4, 4, 0]}>
                {top10.map((entry, i) => <Cell key={i} fill={RISK_COLORS[entry.categoria_riesgo]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartBox>

        {/* Feature importances */}
        {featureData.length > 0 && (
          <ChartBox title="Importancia de Variables">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={featureData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 9, fill: '#94a3b8' }} tickFormatter={v => `${v}%`} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 8, fill: '#64748b' }} width={100} />
                <Tooltip formatter={(v) => [`${v}%`, 'Importancia']} />
                <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartBox>
        )}
      </div>

      {/* Detail table */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Detalle por Cliente</h2>
          <p className="text-[11px] text-slate-400">Haz clic en una fila para ver el detalle del cliente</p>
        </div>
        <div className="overflow-auto max-h-[400px]">
          <table className="w-full text-sm">
            <thead className="bg-slate-50/80 sticky top-0">
              <tr className="text-[11px] text-slate-500 uppercase tracking-wide">
                <th className="px-4 py-3 text-left font-medium">Cliente</th>
                <th className="px-4 py-3 text-center font-medium">Riesgo</th>
                <th className="px-4 py-3 text-right font-medium">Score</th>
                <th className="px-4 py-3 text-right font-medium">Prob. Pago</th>
                <th className="px-4 py-3 text-left font-medium">Factores Principales</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map(c => (
                <tr key={c.cliente_id} onClick={() => navigate(`/clientes/${c.cliente_id}`)}
                  className="border-t border-slate-50 hover:bg-blue-50/40 cursor-pointer transition-colors group">
                  <td className="px-4 py-2.5 font-medium text-slate-700 group-hover:text-blue-700 transition-colors">{c.nombre}</td>
                  <td className="px-4 py-2.5 text-center">
                    <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
                      style={{ background: RISK_COLORS[c.categoria_riesgo] + '18', color: RISK_COLORS[c.categoria_riesgo] }}>
                      {c.categoria_riesgo}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs font-medium">{c.score_riesgo}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`font-semibold ${c.probabilidad_pago >= 60 ? 'text-emerald-600' : c.probabilidad_pago >= 30 ? 'text-amber-600' : 'text-red-500'}`}>
                      {c.probabilidad_pago}%
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-slate-600 whitespace-normal break-words leading-relaxed min-w-[260px]">
                    {c.factores.join(', ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Anomalias ──────────────────────────────────────────

function AnomaliasTab({ data }) {
  const { anomalias = [], por_severidad = {}, total_anomalias = 0, modelos_utilizados = [] } = data;

  return (
    <div className="space-y-5">
      {/* Model banner */}
      {modelos_utilizados.length > 0 && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200/60 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <p className="text-[11px] font-semibold text-amber-700 uppercase tracking-wide">Modelos de Deteccion</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {modelos_utilizados.map((m, i) => (
              <span key={i} className="text-[11px] bg-white/80 text-amber-800 px-2 py-0.5 rounded-md border border-amber-200/60">{m}</span>
            ))}
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5 card-hover">
          <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-1.5">Total Anomalias</p>
          <p className="text-3xl font-bold text-slate-800">{total_anomalias}</p>
        </div>
        {Object.entries(por_severidad).map(([sev, count]) => (
          <div key={sev} className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5 card-hover">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-3 h-3 rounded-full" style={{ background: SEV_COLORS[sev] }} />
              <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium">Severidad {sev}</p>
            </div>
            <p className="text-3xl font-bold text-slate-800">{count}</p>
          </div>
        ))}
      </div>

      {/* Anomaly list */}
      <div className="space-y-3">
        {anomalias.map((a, i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5 hover:border-slate-300 transition-colors">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1.5">
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
                    style={{ background: SEV_COLORS[a.severidad] + '18', color: SEV_COLORS[a.severidad] }}>
                    {a.severidad}
                  </span>
                  <span className="text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                    {a.tipo.replace(/_/g, ' ')}
                  </span>
                  {a.modelo && <span className="text-[10px] text-slate-400">{a.modelo}</span>}
                </div>
                <p className="text-sm text-slate-700 font-medium">{a.descripcion}</p>
                <p className="text-[11px] text-slate-400 mt-1">{a.referencia}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-[11px] text-slate-400">{a.entidad_tipo}</p>
                <p className="text-xs font-mono text-slate-600">{a.entidad_id}</p>
              </div>
            </div>
          </div>
        ))}
        {anomalias.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <p className="text-sm font-medium">No se detectaron anomalias</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Estrategias ──────────────────────────────────────────

function EstrategiasTab({ data, navigate }) {
  const { mejores_horas = [], segmentos = {}, detalle_segmentos = {}, recomendaciones = [], modelo } = data;

  const segData = [
    { name: 'Quick Wins', value: segmentos.quick_wins ?? 0 },
    { name: 'Alto Potencial', value: segmentos.alto_potencial ?? 0 },
    { name: 'Req. Atencion', value: segmentos.requiere_atencion ?? 0 },
    { name: 'Criticos', value: segmentos.casos_criticos ?? 0 },
  ];

  const IMPACTO_COLORS = { alto: '#ff1744', medio: '#ff9100', bajo: '#00d4ff' };

  return (
    <div className="space-y-5">
      {/* Model banner */}
      {modelo && (
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200/60 rounded-xl p-4">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide">Modelo de Segmentacion</p>
              </div>
              <p className="text-sm text-emerald-900 font-semibold">{modelo.tipo} ({modelo.n_clusters} clusters)</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-emerald-700">{modelo.inertia?.toLocaleString()}</p>
              <p className="text-[10px] text-emerald-500">Inertia (SSE)</p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Segmentation */}
        <ChartBox title="Segmentacion de Cartera" subtitle="Distribucion por comportamiento de pago">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={segData} cx="50%" cy="50%" innerRadius={50} outerRadius={90} dataKey="value" paddingAngle={3}
                label={({ name, value }) => `${name}: ${value}`}>
                {segData.map((_, i) => <Cell key={i} fill={SEG_COLORS[i]} />)}
              </Pie>
              <Tooltip /><Legend wrapperStyle={{ fontSize: '11px' }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartBox>

        {/* Best hours */}
        <ChartBox title="Horarios con Mayor Tasa de Exito" subtitle="Efectividad por franja horaria">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={mejores_horas}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="hora" tickFormatter={h => `${h}:00`} tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
              <Tooltip formatter={(v, name) => [name === 'tasa_exito' ? `${v}%` : v, name === 'tasa_exito' ? 'Tasa Exito' : 'Total']} />
              <Bar dataKey="tasa_exito" fill="#22c55e" name="Tasa Exito %" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartBox>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-1">Recomendaciones de Estrategia</h2>
        <p className="text-[11px] text-slate-400 mb-4">Sugerencias basadas en el analisis ML de la cartera</p>
        <div className="space-y-2.5">
          {recomendaciones.map((r, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-slate-50/80 rounded-lg border border-slate-100 hover:border-slate-200 transition-colors">
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full flex-shrink-0 mt-0.5"
                style={{ background: IMPACTO_COLORS[r.impacto] + '18', color: IMPACTO_COLORS[r.impacto] }}>
                {r.impacto}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700">{r.titulo}</p>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{r.descripcion}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick wins table */}
      {(detalle_segmentos.quick_wins ?? []).length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-700">Quick Wins</h2>
            <p className="text-[11px] text-slate-400">Clientes con mayor probabilidad de cerrar su deuda</p>
          </div>
          <div className="overflow-auto max-h-64">
            <table className="w-full text-sm">
              <thead className="bg-slate-50/80">
                <tr className="text-[11px] text-slate-500 uppercase tracking-wide">
                  <th className="px-4 py-2.5 text-left font-medium">Cliente</th>
                  <th className="px-4 py-2.5 text-right font-medium">Pendiente</th>
                  <th className="px-4 py-2.5 text-right font-medium">% Pendiente</th>
                  <th className="px-4 py-2.5 text-right font-medium">Cumplimiento</th>
                </tr>
              </thead>
              <tbody>
                {detalle_segmentos.quick_wins.map(c => (
                  <tr key={c.cliente_id} onClick={() => navigate(`/clientes/${c.cliente_id}`)}
                    className="border-t border-slate-50 hover:bg-blue-50/40 cursor-pointer transition-colors group">
                    <td className="px-4 py-2.5 text-blue-600 group-hover:text-blue-700 font-medium">{c.nombre}</td>
                    <td className="px-4 py-2.5 text-right font-medium">${c.deuda_pendiente.toLocaleString('es')}</td>
                    <td className="px-4 py-2.5 text-right text-emerald-600 font-medium">{c.pct_pendiente}%</td>
                    <td className="px-4 py-2.5 text-right font-medium">{c.tasa_cumplimiento}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Shared chart wrapper ────────────────────────────────

function ChartBox({ title, subtitle, children }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm">
      <div className="px-5 pt-5 pb-2">
        <h2 className="text-sm font-semibold text-slate-700">{title}</h2>
        {subtitle && <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      <div className="px-3 pb-4">{children}</div>
    </div>
  );
}
