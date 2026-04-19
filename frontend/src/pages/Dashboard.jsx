import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getPromesasIncumplidas, getMejoresHorarios } from '../api/client';
import {
  PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, BarChart, Bar,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import DataCard from '../components/ui/DataCard';

const CHART_COLORS = {
  llamadas: 'var(--chart-1)',
  pagos:    'var(--chart-2)',
  bars:     'var(--chart-4)',
};

const PIE_COLORS = [
  'var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)',
  'var(--chart-4)', 'var(--chart-5)', 'var(--chart-6)',
];

function Skeleton({ h = 'h-28' }) {
  return <div className={`ds-skeleton ${h}`} />;
}

const TICK = { fontSize: 10, fill: 'var(--text-muted)' };

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: dash, isLoading: l1 } = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard });
  const { data: promesas, isLoading: l2 } = useQuery({ queryKey: ['promesas-incumplidas'], queryFn: getPromesasIncumplidas });
  const { data: horarios, isLoading: l3 } = useQuery({ queryKey: ['mejores-horarios'], queryFn: getMejoresHorarios });

  if (l1 || l2 || l3) {
    return (
      <div className="space-y-5 max-w-7xl mx-auto">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} h="h-24" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton h="h-72" /><Skeleton h="h-72" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton h="h-64" /><Skeleton h="h-64" />
        </div>
      </div>
    );
  }

  const deudaTipos = dash?.distribucion_tipos_deuda
    ? Object.entries(dash.distribucion_tipos_deuda).map(([name, value]) => ({
        name: name.replace(/_/g, ' '),
        value,
      }))
    : [];

  const actividad = dash?.actividad_por_dia ?? [];
  const promesasList = Array.isArray(promesas) ? promesas : [];
  const horariosDetalle = horarios?.detalle_por_hora ?? [];

  const RESULTADO_LABEL = {
    pago_inmediato:  'Pago inm.',
    promesa_pago:    'Promesa',
    sin_respuesta:   'Sin resp.',
    se_niega_pagar:  'Negativa',
    renegociacion:   'Renegoc.',
    disputa:         'Disputa',
    '':              'Sin dato',
  };
  const RESULTADO_COLOR = {
    pago_inmediato: '#10b981',
    promesa_pago:   '#3b82f6',
    sin_respuesta:  '#94a3b8',
    se_niega_pagar: '#ef4444',
    renegociacion:  '#f59e0b',
    disputa:        '#8b5cf6',
    '':             '#4a5568',
  };
  const resultadoDist = Object.entries(
    horariosDetalle.reduce((acc, h) => {
      Object.entries(h.distribucion_resultados ?? {}).forEach(([k, v]) => {
        acc[k] = (acc[k] ?? 0) + v;
      });
      return acc;
    }, {})
  )
    .map(([key, value]) => ({ key, name: RESULTADO_LABEL[key] ?? key, value, fill: RESULTADO_COLOR[key] ?? '#4a5568' }))
    .filter(d => d.key !== '')
    .sort((a, b) => b.value - a.value);
  const tasaRec = ((dash?.tasa_recuperacion ?? 0) * 100).toFixed(1);

  const byClient = {};
  promesasList.forEach(p => {
    const cid = p.cliente_id ?? 'desconocido';
    if (!byClient[cid]) byClient[cid] = { count: 0, total: 0 };
    byClient[cid].count += 1;
    byClient[cid].total += (p.monto ?? 0);
  });
  const clientRows = Object.entries(byClient)
    .map(([id, { count, total }]) => ({ id, count, total }))
    .sort((a, b) => b.total - a.total);

  const promesasCumplidas = dash?.promesas_cumplidas ?? 0;
  const promesasTotal = promesasCumplidas + (dash?.promesas_incumplidas ?? 0);

  return (
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Deuda total"
          value={`$${(dash?.total_deuda_inicial ?? 0).toLocaleString('es')}`}
          note="Cartera total inicial"
        />
        <StatCard
          label="Recuperado"
          value={`$${(dash?.total_recuperado ?? 0).toLocaleString('es')}`}
          note={`${tasaRec}% de la cartera`}
          variant="success"
        />
        <StatCard
          label="Promesas"
          value={`${promesasCumplidas} / ${promesasTotal}`}
          note={`${dash?.promesas_incumplidas ?? 0} incumplidas`}
          variant={dash?.promesas_incumplidas > 5 ? 'danger' : 'default'}
        />
        <StatCard
          label="Mejor hora"
          value={horarios?.mejor_hora != null ? `${horarios.mejor_hora}:00` : '--'}
          note="Mayor volumen de éxito"
        />
      </div>

      {/* Progreso global */}
      <DataCard
        title="Progreso de recuperación"
        aside={
          <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--state-success)' }}>
            {tasaRec}%
          </span>
        }
      >
        <div style={{ background: 'var(--bg-elevated)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
          <div
            style={{
              width: `${Math.min(100, Number(tasaRec))}%`,
              height: '100%',
              background: 'var(--state-success)',
              borderRadius: 4,
              transition: 'width 700ms ease',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>
          <span>$0</span>
          <span>${(dash?.total_deuda_inicial ?? 0).toLocaleString('es')}</span>
        </div>
      </DataCard>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DataCard title="Actividad por día" subtitle="Llamadas y pagos en el tiempo">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={actividad}>
              <defs>
                <linearGradient id="gLlamadas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={CHART_COLORS.llamadas} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={CHART_COLORS.llamadas} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gPagos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={CHART_COLORS.pagos} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={CHART_COLORS.pagos} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="fecha" tick={TICK} angle={-40} textAnchor="end" height={54} />
              <YAxis tick={TICK} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
                labelStyle={{ color: 'var(--text-secondary)' }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="llamadas" stroke={CHART_COLORS.llamadas} fill="url(#gLlamadas)" strokeWidth={2} name="Llamadas" />
              <Area type="monotone" dataKey="pagos"    stroke={CHART_COLORS.pagos}    fill="url(#gPagos)"    strokeWidth={2} name="Pagos" />
            </AreaChart>
          </ResponsiveContainer>
        </DataCard>

        <DataCard title="Distribución por tipo de deuda" subtitle="Composición de cartera">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={deudaTipos}
                cx="50%" cy="50%"
                innerRadius={62} outerRadius={105}
                dataKey="value"
                paddingAngle={2}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: 'var(--text-muted)' }}
              >
                {deudaTipos.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => [`$${v.toLocaleString('es')}`, 'Monto']}
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </DataCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <DataCard title="Distribución de resultados" subtitle="Tipo de resultado por interacción">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={resultadoDist} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={TICK} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} width={65} />
              <Tooltip
                formatter={(v, _, props) => [v + ' interacciones', props.payload?.name]}
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {resultadoDist.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </DataCard>

        <DataCard
          title="Promesas vencidas"
          subtitle={`${promesasList.length} promesas sin cumplir`}
          aside={
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {clientRows.length} clientes
            </span>
          }
          flush
        >
          <div style={{ overflowY: 'auto', maxHeight: 264 }}>
            {clientRows.length === 0 ? (
              <div className="ds-empty">
                <div className="ds-empty-title">Sin promesas vencidas</div>
              </div>
            ) : (
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th className="center">Qty</th>
                    <th className="right">Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {clientRows.slice(0, 15).map(c => (
                    <tr key={c.id} onClick={() => navigate(`/clientes/${c.id}`)}>
                      <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{c.id}</td>
                      <td className="center">
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          width: 22, height: 22, borderRadius: 4,
                          background: 'var(--state-danger-bg)', color: 'var(--state-danger)',
                          fontSize: 11, fontWeight: 700,
                        }}>
                          {c.count}
                        </span>
                      </td>
                      <td className="right" style={{ fontWeight: 600, color: 'var(--state-danger)' }}>
                        ${c.total.toLocaleString('es')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </DataCard>
      </div>
    </div>
  );
}
