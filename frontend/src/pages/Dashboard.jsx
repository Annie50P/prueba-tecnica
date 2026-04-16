import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getDashboard, getPromesasIncumplidas, getMejoresHorarios } from '../api/client';
import {
  PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, BarChart, Bar,
} from 'recharts';
import SectionHeader from '../components/ui/SectionHeader';
import Panel from '../components/ui/Panel';
import MetricTile from '../components/ui/MetricTile';

const PIE_COLORS = ['#ff2d55', '#00d4ff', '#7c4dff', '#00e676', '#ff9100', '#ff1744'];
const CHART_COLORS = {
  llamadas: '#00d4ff',
  pagos: '#ff2d55',
  bars: '#7c4dff',
  progress: '#00e676',
};

function Skeleton({ className = '' }) {
  return <div className={`skeleton ${className}`} />;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: dash, isLoading: l1 } = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard });
  const { data: promesas, isLoading: l2 } = useQuery({ queryKey: ['promesas-incumplidas'], queryFn: getPromesasIncumplidas });
  const { data: horarios, isLoading: l3 } = useQuery({ queryKey: ['mejores-horarios'], queryFn: getMejoresHorarios });

  if (l1 || l2 || l3) {
    return (
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      </div>
    );
  }

  const deudaTipos = dash?.distribucion_tipos_deuda
    ? Object.entries(dash.distribucion_tipos_deuda).map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }))
    : [];

  const actividad = dash?.actividad_por_dia ?? [];
  const promesasList = Array.isArray(promesas) ? promesas : [];
  const horariosDetalle = horarios?.detalle_por_hora ?? [];
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

  return (
    <div className="poll-container poll-space space-y-6">
      <SectionHeader
        title="Control de cartera"
        description="Brutal minimal UI, datos directos y visualizaciones con acentos vibrantes."
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricTile
          label="Deuda total"
          value={`$${(dash?.total_deuda_inicial ?? 0).toLocaleString('es')}`}
          note="Suma de deudas iniciales"
        />
        <MetricTile
          label="Total recuperado"
          value={`$${(dash?.total_recuperado ?? 0).toLocaleString('es')}`}
          note={`Recuperacion ${tasaRec}%`}
        />
        <MetricTile
          label="Promesas"
          value={`${dash?.promesas_cumplidas ?? 0} / ${(dash?.promesas_cumplidas ?? 0) + (dash?.promesas_incumplidas ?? 0)}`}
          note={`${dash?.promesas_incumplidas ?? 0} incumplidas`}
        />
        <MetricTile
          label="Mejor hora"
          value={horarios?.mejor_hora ? `${horarios.mejor_hora}:00` : '--'}
          note="Mayor volumen de exito"
        />
      </div>

      <Panel
        title="Progreso de recuperacion"
        subtitle="Total recuperado vs deuda total"
        aside={<span style={{ color: CHART_COLORS.progress, fontSize: '1.35rem' }}>{tasaRec}%</span>}
      >
        <div className="w-full bg-slate-100 h-2">
          <div
            className="h-2 transition-all duration-700"
            style={{ width: `${Math.min(100, Number(tasaRec))}%`, background: CHART_COLORS.progress }}
          />
        </div>
        <div className="flex justify-between mt-2 text-[11px] text-slate-400">
          <span>$0</span>
          <span>${(dash?.total_deuda_inicial ?? 0).toLocaleString('es')}</span>
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Distribucion por tipo de deuda" subtitle="Composicion de cartera">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={deudaTipos}
                cx="50%"
                cy="50%"
                innerRadius={58}
                outerRadius={100}
                dataKey="value"
                paddingAngle={2}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
              >
                {deudaTipos.map((_, i) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => [`$${v.toLocaleString('es')}`, 'Monto']} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="Actividad por dia" subtitle="Llamadas y pagos en el tiempo">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={actividad}>
              <defs>
                <linearGradient id="gradLlamadas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.llamadas} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={CHART_COLORS.llamadas} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradPagos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={CHART_COLORS.pagos} stopOpacity={0.35} />
                  <stop offset="95%" stopColor={CHART_COLORS.pagos} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ededed" />
              <XAxis dataKey="fecha" tick={{ fontSize: 10, fill: '#8c8c8c' }} angle={-45} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 10, fill: '#8c8c8c' }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Area type="monotone" dataKey="llamadas" stroke={CHART_COLORS.llamadas} fill="url(#gradLlamadas)" strokeWidth={2} name="Llamadas" />
              <Area type="monotone" dataKey="pagos" stroke={CHART_COLORS.pagos} fill="url(#gradPagos)" strokeWidth={2} name="Pagos" />
            </AreaChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Efectividad por hora" subtitle="Volumen por franja">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={horariosDetalle}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ededed" />
              <XAxis dataKey="hora" tick={{ fontSize: 10, fill: '#8c8c8c' }} tickFormatter={h => `${h}h`} />
              <YAxis tick={{ fontSize: 10, fill: '#8c8c8c' }} />
              <Tooltip formatter={(v) => [v, 'Llamadas']} labelFormatter={(l) => `${l}:00`} />
              <Bar dataKey="total_llamadas" fill={CHART_COLORS.bars} name="Llamadas" />
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        <Panel
          title="Promesas vencidas"
          subtitle={`${promesasList.length} promesas sin cumplir`}
          aside={<span className="text-xs text-slate-500">{clientRows.length} clientes</span>}
        >
          <div className="overflow-auto max-h-[280px]">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] text-slate-400 uppercase tracking-wide">
                  <th className="pb-2.5 font-medium">Cliente</th>
                  <th className="pb-2.5 font-medium text-center">Qty</th>
                  <th className="pb-2.5 font-medium text-right">Monto</th>
                </tr>
              </thead>
              <tbody>
                {clientRows.slice(0, 15).map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/clientes/${c.id}`)}
                    className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="py-2.5 text-slate-700 font-mono text-xs">{c.id}</td>
                    <td className="py-2.5 text-center">
                      <span className="inline-flex items-center justify-center w-6 h-5 text-[11px]">
                        {c.count}
                      </span>
                    </td>
                    <td className="py-2.5 text-right font-medium text-slate-700">${c.total.toLocaleString('es')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  );
}
