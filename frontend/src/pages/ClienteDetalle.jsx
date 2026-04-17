import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getClienteDetalle, getClienteTimeline } from '../api/client';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';

const SENT_STYLES = {
  positivo:     { cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: '+' },
  cooperativo:  { cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: '+' },
  neutral:      { cls: 'bg-slate-50 text-slate-600 border-slate-200',       icon: '~' },
  'n/a':        { cls: 'bg-slate-50 text-slate-500 border-slate-200',       icon: '-' },
  negativo:     { cls: 'bg-red-50 text-red-700 border-red-200',             icon: '!' },
  frustrado:    { cls: 'bg-orange-50 text-orange-700 border-orange-200',    icon: '!' },
  hostil:       { cls: 'bg-red-100 text-red-800 border-red-300',            icon: '!!' },
  muy_negativo: { cls: 'bg-red-100 text-red-800 border-red-300',            icon: '!!' },
};

const RESULT_DOTS = {
  pago_inmediato: 'bg-emerald-400',
  promesa_pago:   'bg-amber-400',
  renegociacion:  'bg-cyan-400',
  se_niega_pagar: 'bg-rose-500',
  sin_respuesta:  'bg-slate-300',
  disputa:        'bg-fuchsia-500',
};

function StatCard({ label, value, color = 'text-slate-800', sub }) {
  return (
    <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-100">
      <p className="text-[11px] text-slate-500 uppercase tracking-wide font-medium mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function getStatus(c) {
  const pend  = c.monto_pendiente ?? 0;
  const ini   = c.monto_deuda_inicial ?? 1;
  const ratio = pend / ini;
  const dias  = c.dias_sin_contacto ?? 0;
  const cumpl = c.tasa_cumplimiento ?? 1;
  const nllamadas = (c.interacciones ?? []).length;

  if (pend === 0)
    return { label: 'Liquidado',       cls: 'bg-emerald-100 text-emerald-700' };
  if (ratio < 0.3)
    return { label: 'Casi liquidado',  cls: 'bg-blue-100 text-blue-700' };
  if (ratio >= 0.5 && cumpl < 0.25 && nllamadas > 2)
    return { label: 'Alto riesgo',     cls: 'bg-red-200 text-red-800' };
  if (dias > 60 && ratio >= 0.5)
    return { label: 'Sin gestión',     cls: 'bg-orange-100 text-orange-700' };
  if (ratio < 0.7)
    return { label: 'En proceso',      cls: 'bg-amber-100 text-amber-700' };
  return   { label: 'Pendiente alto',  cls: 'bg-red-100 text-red-700' };
}

function money(n) {
  if (n == null) return '--';
  return `$${Number(n).toLocaleString('es')}`;
}

export default function ClienteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();

  const { data: cliente, isLoading: l1 } = useQuery({
    queryKey: ['cliente', id],
    queryFn: () => getClienteDetalle(id),
  });
  const { data: timeline, isLoading: l2 } = useQuery({
    queryKey: ['cliente-timeline', id],
    queryFn: () => getClienteTimeline(id),
  });

  if (l1 || l2) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <div className="skeleton h-16" />
        <div className="grid grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <div key={i} className="skeleton h-20" />)}</div>
        <div className="skeleton h-64" />
      </div>
    );
  }

  if (!cliente) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-slate-400">
        <svg className="w-16 h-16 mb-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="font-medium">Cliente no encontrado</p>
        <button onClick={() => navigate('/clientes')} className="mt-3 text-blue-600 hover:underline text-sm">Volver a clientes</button>
      </div>
    );
  }

  const events = Array.isArray(timeline) ? timeline : (timeline?.timeline ?? []);
  const ini  = cliente.monto_deuda_inicial ?? 1;
  const pend = cliente.monto_pendiente ?? 0;
  const status = getStatus({ ...cliente, tasa_cumplimiento: cliente.tasa_cumplimiento });

  // Gráfico evolución deuda
  const pagos = (cliente.pagos ?? [])
    .map(p => ({ monto: p.monto ?? 0, fecha: p.fecha ?? p.timestamp ?? '' }))
    .filter(p => p.fecha)
    .sort((a, b) => a.fecha.localeCompare(b.fecha));

  const evolution = [{ fecha: 'Inicio', deuda: ini, pagado: 0 }];
  let acum = 0;
  pagos.forEach(p => {
    acum += p.monto;
    evolution.push({ fecha: p.fecha.slice(0, 10), deuda: Math.max(0, ini - acum), pagado: acum });
  });

  const pctRecuperado  = ini > 0 ? ((cliente.total_pagado ?? 0) / ini * 100).toFixed(1) : 0;
  const promesasTotal  = (cliente.promesas ?? []).length;
  const promesasCumpl  = (cliente.promesas ?? []).filter(p => p.cumplida).length;
  const tasaCumpl      = promesasTotal > 0 ? ((promesasCumpl / promesasTotal) * 100).toFixed(0) : '--';

  const planes = cliente.planes ?? [];

  return (
    <div className="poll-container poll-space">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button onClick={() => navigate('/clientes')} className="mt-1 text-slate-400 hover:text-slate-700 transition-colors p-1 -ml-1">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-sm">
              {(cliente.nombre ?? 'C')[0]}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl font-bold text-slate-800">{cliente.nombre ?? cliente.id}</h1>
                <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${status.cls}`}>{status.label}</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {cliente.id} · {cliente.telefono ?? ''} · {(cliente.tipo_deuda ?? '').replace(/_/g, ' ')}
                {cliente.ultimo_agente_id && (
                  <span className="ml-2 text-slate-300">· Último gestor: <span className="text-slate-500">{cliente.ultimo_agente_id}</span></span>
                )}
                {cliente.mejor_horario_contacto && (
                  <span className="ml-2 text-slate-300">· Mejor horario: <span className="text-violet-600">{cliente.mejor_horario_contacto}</span></span>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* KPIs fila 1 */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard label="Deuda Inicial"   value={money(ini)} />
        <StatCard label="Total Pagado"    value={money(cliente.total_pagado)}   color="text-emerald-600" />
        <StatCard label="Pendiente"       value={money(pend)}                   color="text-red-500" />
        <StatCard label="Recuperado"      value={`${pctRecuperado}%`}           color="text-blue-600" />
        <StatCard label="Interacciones"   value={(cliente.interacciones ?? events).length ?? 0} />
      </div>

      {/* KPIs fila 2 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          label="Días sin contacto"
          value={cliente.dias_sin_contacto != null ? `${cliente.dias_sin_contacto}d` : '--'}
          color={
            cliente.dias_sin_contacto == null ? 'text-slate-500' :
            cliente.dias_sin_contacto <= 7  ? 'text-emerald-600' :
            cliente.dias_sin_contacto <= 30 ? 'text-amber-600' : 'text-red-500'
          }
          sub={cliente.ultima_interaccion ? cliente.ultima_interaccion.slice(0, 10) : undefined}
        />
        <StatCard
          label="Monto comprometido"
          value={money(cliente.monto_prometido_pendiente)}
          color="text-amber-600"
          sub="en promesas pendientes"
        />
        <StatCard
          label="Cumplimiento promesas"
          value={promesasTotal > 0 ? `${promesasCumpl}/${promesasTotal}` : '--'}
          color={Number(tasaCumpl) >= 50 ? 'text-emerald-600' : 'text-red-500'}
          sub={promesasTotal > 0 ? `${tasaCumpl}% cumplidas` : undefined}
        />
        <StatCard
          label="Sentimiento predominante"
          value={cliente.sentimiento_predominante ?? '--'}
          color={
            cliente.sentimiento_predominante === 'cooperativo' ? 'text-emerald-600' :
            cliente.sentimiento_predominante === 'hostil'      ? 'text-red-600' :
            cliente.sentimiento_predominante === 'frustrado'   ? 'text-amber-600' : 'text-slate-600'
          }
        />
      </div>

      {/* Evolución de deuda */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Evolución de la Deuda</h2>
            <p className="text-[11px] text-slate-400">Progresión del pago a lo largo del tiempo</p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-red-400 rounded" /> Deuda</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-emerald-400 rounded" /> Pagado</span>
          </div>
        </div>

        <div className="mb-5">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
            <span>Progreso de recuperación</span>
            <span className="font-semibold text-emerald-600">{pctRecuperado}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2.5">
            <div className="h-2.5 rounded-full bg-gradient-to-r from-emerald-400 to-emerald-500 transition-all" style={{ width: `${Math.min(100, Number(pctRecuperado))}%` }} />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="space-y-3">
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Promesas</p>
              <p className="text-lg font-bold text-slate-800 mt-0.5">{promesasCumpl}/{promesasTotal}</p>
              <p className="text-[11px] text-slate-400">{tasaCumpl !== '--' ? `${tasaCumpl}% cumplidas` : 'Sin promesas'}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
              <p className="text-[10px] text-slate-400 uppercase tracking-wide">Pagos</p>
              <p className="text-lg font-bold text-slate-800 mt-0.5">{pagos.length}</p>
              <p className="text-[11px] text-slate-400">realizados</p>
            </div>
          </div>

          <div className="lg:col-span-3">
            {evolution.length > 1 ? (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={evolution}>
                  <defs>
                    <linearGradient id="gradDeuda" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f87171" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gradPagado" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#34d399" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="fecha" tick={{ fontSize: 9, fill: '#94a3b8' }} angle={-30} textAnchor="end" height={45} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip formatter={(val) => money(val)} />
                  <Area type="monotone" dataKey="deuda"  stroke="#f87171" fill="url(#gradDeuda)"  strokeWidth={2} name="Deuda" />
                  <Area type="monotone" dataKey="pagado" stroke="#34d399" fill="url(#gradPagado)" strokeWidth={2} name="Pagado" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-48 text-slate-400 text-sm">Sin pagos registrados</div>
            )}
          </div>
        </div>
      </div>

      {/* Promesas, Pagos y Planes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Promesas */}
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-700">Promesas</h2>
            <span className="text-xs text-slate-400">{promesasTotal} total</span>
          </div>
          <div className="space-y-2 max-h-48 overflow-auto">
            {(cliente.promesas ?? []).map((p, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-lg text-sm border border-slate-100">
                <span className="font-medium text-slate-700">{money(p.monto_prometido ?? p.monto)}</span>
                <span className="text-slate-400 text-xs">{(p.fecha_promesa ?? p.fecha ?? p.timestamp ?? '--').slice(0, 10)}</span>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${p.cumplida ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
                  {p.cumplida ? 'Cumplida' : 'Pendiente'}
                </span>
              </div>
            ))}
            {promesasTotal === 0 && <p className="text-slate-400 text-sm text-center py-4">Sin promesas registradas</p>}
          </div>
        </div>

        {/* Pagos */}
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-700">Pagos</h2>
            <span className="text-xs text-slate-400">{pagos.length} total</span>
          </div>
          <div className="space-y-2 max-h-48 overflow-auto">
            {pagos.map((p, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 bg-slate-50 rounded-lg text-sm border border-slate-100">
                <span className="font-semibold text-emerald-600">{money(p.monto)}</span>
                <span className="text-slate-400 text-xs">{(p.fecha ?? '--').slice(0, 10)}</span>
                <span className="text-[11px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">{p.metodo_pago ?? ''}</span>
              </div>
            ))}
            {pagos.length === 0 && <p className="text-slate-400 text-sm text-center py-4">Sin pagos registrados</p>}
          </div>
        </div>

        {/* Planes de pago */}
        <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-slate-700">Planes de Pago</h2>
            <span className="text-xs text-slate-400">{planes.length} activo{planes.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-2 max-h-48 overflow-auto">
            {planes.map((p, i) => (
              <div key={i} className="py-2 px-3 bg-violet-50 rounded-lg text-sm border border-violet-100">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-violet-700">{money(p.monto_mensual)}/mes</span>
                  <span className="text-[11px] text-violet-500">{p.cuotas ?? p.num_cuotas ?? '?'} cuotas</span>
                </div>
                <p className="text-[11px] text-violet-400 mt-0.5">
                  Total plan: {money(p.monto_total_plan)}
                  {p.fecha_inicio ? ` · desde ${String(p.fecha_inicio).slice(0, 10)}` : ''}
                </p>
              </div>
            ))}
            {planes.length === 0 && <p className="text-slate-400 text-sm text-center py-4">Sin planes activos</p>}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm p-5">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Timeline de Interacciones</h2>
            <p className="text-[11px] text-slate-400">{events.length} eventos en orden cronológico</p>
          </div>
        </div>
        <div className="space-y-0 max-h-[500px] overflow-auto pr-2">
          {events.map((ev, i) => {
            const sent      = ev.sentimiento_cliente ?? ev.sentimiento ?? 'neutral';
            const sentStyle = SENT_STYLES[sent] ?? SENT_STYLES.neutral;
            const resultado = ev.resultado ?? ev.tipo ?? 'contacto';
            const dotColor  = RESULT_DOTS[resultado] ?? 'bg-slate-300';
            const duracion  = ev.duracion_segundos
              ? `· ${ev.duracion_segundos}s`
              : ev.duracion_minutos
              ? `· ${ev.duracion_minutos} min`
              : '';

            return (
              <div key={i} className="relative pl-8 pb-5 last:pb-0">
                {i < events.length - 1 && <div className="absolute left-[11px] top-3 bottom-0 w-[2px] bg-slate-100" />}
                <div className={`absolute left-1.5 top-1 w-3 h-3 rounded-full ${dotColor} ring-2 ring-white`} />

                <div className="bg-slate-50/80 rounded-lg p-3 border border-slate-100 hover:border-slate-200 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-slate-700">{resultado.replace(/_/g, ' ')}</span>
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${sentStyle.cls}`}>{sent}</span>
                        {ev.agente_id && <span className="text-[10px] text-slate-400">por {ev.agente_id}</span>}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {ev.timestamp ?? ev.fecha ?? '--'} {duracion}
                      </p>
                    </div>
                  </div>

                  {(ev.promesas?.length > 0 || ev.pagos?.length > 0 || ev.planes?.length > 0) && (
                    <div className="mt-2 pt-2 border-t border-slate-200/60 flex flex-wrap gap-2">
                      {(ev.promesas ?? []).map((p, j) => (
                        <span key={`pr-${j}`} className="text-[11px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">
                          Promesa: {money(p.monto_prometido ?? p.monto)}
                        </span>
                      ))}
                      {(ev.pagos ?? []).map((p, j) => (
                        <span key={`pa-${j}`} className="text-[11px] bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded border border-emerald-200">
                          Pago: {money(p.monto)}
                        </span>
                      ))}
                      {(ev.planes ?? []).map((p, j) => (
                        <span key={`pl-${j}`} className="text-[11px] bg-violet-50 text-violet-700 px-2 py-0.5 rounded border border-violet-200">
                          Plan: {p.cuotas ?? p.num_cuotas ?? '?'} cuotas · {money(p.monto_mensual)}/mes
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {events.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <p className="text-sm">Sin interacciones registradas</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
