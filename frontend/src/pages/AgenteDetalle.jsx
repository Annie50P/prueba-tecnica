import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getAgenteEfectividad, getAgentes } from '../api/client';
import {
  BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import DataCard from '../components/ui/DataCard';

const RESULT_COLORS = {
  promesa_pago:    'var(--state-warning)',
  pago_inmediato:  'var(--state-success)',
  renegociacion:   'var(--state-info)',
  sin_respuesta:   'var(--text-muted)',
  se_niega_pagar:  'var(--state-danger)',
  disputa:         'var(--state-purple)',
};

const SENT_COLORS_PIE = {
  cooperativo: '#10b981',
  neutral:     '#4a5568',
  frustrado:   '#f59e0b',
  hostil:      '#ef4444',
  'n/a':       '#2d3748',
};

const TICK = { fontSize: 10, fill: 'var(--text-muted)' };

function pct(n) { return n == null ? '--' : `${(n * 100).toFixed(1)}%`; }

function money(n) {
  if (n == null) return '--';
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
}

function AgentInitials(agent) {
  return (agent.nombre ?? agent.id ?? '?')
    .replace('agente_0', '').replace('agente_', '')
    .slice(0, 2).toUpperCase();
}

function CustomTooltip({ active, payload, total }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0].payload;
  const p = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)',
      borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      <p style={{ fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{name}</p>
      <p style={{ color: 'var(--text-muted)', margin: '2px 0 0' }}>
        {value} llamadas ({p}%)
      </p>
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

  const { data: todosAgentes } = useQuery({
    queryKey: ['agentes'],
    queryFn: getAgentes,
  });

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-5xl mx-auto">
        <div className="ds-skeleton h-20" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[...Array(4)].map((_, i) => <div key={i} className="ds-skeleton h-20" />)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="ds-skeleton h-72" /><div className="ds-skeleton h-72" />
        </div>
      </div>
    );
  }

  if (!agente) {
    return (
      <div className="ds-empty" style={{ height: 400 }}>
        <div className="ds-empty-title">Agente no encontrado</div>
        <button className="ds-btn ds-btn-ghost" style={{ marginTop: 12 }} onClick={() => navigate('/agentes')}>
          Volver
        </button>
      </div>
    );
  }

  const resultados = agente.distribucion_resultados
    ? Object.entries(agente.distribucion_resultados).map(([name, value]) => ({
        name: name.replace(/_/g, ' '),
        value,
        fill: RESULT_COLORS[name] ?? 'var(--text-muted)',
      }))
    : [];

  const sentimientos = agente.distribucion_sentimientos
    ? Object.entries(agente.distribucion_sentimientos).map(([name, value]) => ({
        name,
        value,
        fill: SENT_COLORS_PIE[name] ?? '#4a5568',
      }))
    : [];

  const totalResultados = resultados.reduce((s, r) => s + r.value, 0) || 1;

  let rankingLabel = null;
  if (todosAgentes?.length > 1) {
    const sortedAll = [...todosAgentes].sort(
      (a, b) => ((b.tasa_promesa ?? 0) + (b.tasa_pago_inmediato ?? 0)) -
                ((a.tasa_promesa ?? 0) + (a.tasa_pago_inmediato ?? 0))
    );
    const pos = sortedAll.findIndex(a => a.id === id) + 1;
    rankingLabel = `#${pos} de ${sortedAll.length}`;
  }

  const actividadHoraria = agente.actividad_por_hora ?? [];
  const tendenciaSemanal = agente.tendencia_semanal ?? [];

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="ds-detail-header">
        <button className="ds-back-btn" onClick={() => navigate('/agentes')} style={{ marginBottom: 12 }}>
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Agentes
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div className="ds-avatar">
            {AgentInitials(agente)}
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
              {agente.nombre ?? agente.id}
            </h1>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {agente.id} · Rendimiento y análisis de llamadas
              {agente.mejor_horario && (
                <span style={{ marginLeft: 12, color: 'var(--state-info)' }}>
                  Mejor franja: {agente.mejor_horario}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* KPIs primarios */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        <StatCard label="Total Llamadas"  value={agente.total_llamadas ?? 0} />
        <StatCard label="Tasa Éxito"      value={pct(agente.tasa_exito)}    variant="success" note="promesa + pago inmediato" />
        <StatCard label="Monto Prometido" value={money(agente.monto_prometido_total)} variant="info" />
        <StatCard label="Ranking Equipo"  value={rankingLabel ?? '--'}       variant="purple" note="por tasa de éxito" />
      </div>

      {/* KPIs secundarios */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        <StatCard label="Tasa Promesa"      value={pct(agente.tasa_promesa)}          variant="warning" />
        <StatCard label="Tasa Pago Inm."    value={pct(agente.tasa_pago_inmediato)}   variant="info" />
        <StatCard label="Tasa Fracaso"      value={pct(agente.tasa_fracaso)}           variant="danger" note="negación + sin respuesta" />
        <StatCard
          label="Cumpl. Promesas"
          value={agente.tasa_cumplimiento_promesas != null ? pct(agente.tasa_cumplimiento_promesas) : '--'}
          variant="success"
          note={agente.promesas_generadas ? `${agente.promesas_generadas} generadas` : undefined}
        />
      </div>

      {/* Charts row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <DataCard title="Distribución de Resultados" subtitle={`${totalResultados} interacciones`}>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={resultados} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={TICK} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} width={120} />
              <Tooltip content={<CustomTooltip total={totalResultados} />} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {resultados.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </DataCard>

        <DataCard title="Actividad por Hora">
          {actividadHoraria.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={actividadHoraria}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hora" tick={TICK} />
                <YAxis tick={TICK} />
                <Tooltip
                  formatter={(v, name) => [v, name === 'total' ? 'Llamadas' : 'Éxitos']}
                  labelFormatter={l => `Hora: ${l}`}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
                />
                <Legend formatter={v => v === 'total' ? 'Llamadas' : 'Éxitos'} />
                <Bar dataKey="total"  fill="rgba(148,163,184,0.4)" radius={[3,3,0,0]} />
                <Bar dataKey="exitos" fill="var(--state-success)"  radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="ds-empty"><div className="ds-empty-desc">Sin datos horarios</div></div>
          )}
        </DataCard>
      </div>

      {/* Charts row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <DataCard title="Sentimientos" subtitle="Percepción del cliente">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={sentimientos}
                cx="50%" cy="50%"
                innerRadius={55} outerRadius={90}
                dataKey="value"
                paddingAngle={2}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {sentimientos.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v, name) => [v, name]}
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </DataCard>

        <DataCard title="Tendencia Semanal" subtitle="Evolución de llamadas y éxitos">
          {tendenciaSemanal.length > 1 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={tendenciaSemanal}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="semana" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
                <YAxis yAxisId="left"  tick={TICK} />
                <YAxis yAxisId="right" orientation="right" tickFormatter={v => `${(v * 100).toFixed(0)}%`} tick={TICK} domain={[0,1]} />
                <Tooltip
                  formatter={(v, name) =>
                    name === 'tasa_exito'
                      ? [`${(v * 100).toFixed(1)}%`, 'Tasa éxito']
                      : [v, name === 'total' ? 'Llamadas' : 'Éxitos']
                  }
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
                />
                <Legend formatter={v => v === 'total' ? 'Llamadas' : v === 'exitos' ? 'Éxitos' : 'Tasa éxito'} />
                <Line yAxisId="left"  type="monotone" dataKey="total"      stroke="var(--text-muted)"    strokeWidth={2} dot={false} />
                <Line yAxisId="left"  type="monotone" dataKey="exitos"     stroke="var(--state-success)" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="tasa_exito" stroke="var(--state-warning)" strokeWidth={2} strokeDasharray="4 2" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="ds-empty">
              <div className="ds-empty-desc">
                {tendenciaSemanal.length === 1
                  ? 'Solo hay datos de una semana'
                  : 'Sin datos de tendencia'}
              </div>
            </div>
          )}
        </DataCard>
      </div>
    </div>
  );
}
