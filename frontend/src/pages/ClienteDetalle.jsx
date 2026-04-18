import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getClienteDetalle, getClienteTimeline } from '../api/client';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import DataCard from '../components/ui/DataCard';
import Badge from '../components/ui/Badge';

const RESULT_COLORS = {
  pago_inmediato: 'var(--state-success)',
  promesa_pago:   'var(--state-warning)',
  renegociacion:  'var(--state-info)',
  se_niega_pagar: 'var(--state-danger)',
  sin_respuesta:  'var(--text-muted)',
  disputa:        'var(--state-purple)',
};

const SENT_BADGE = {
  cooperativo:  'success',
  positivo:     'success',
  neutral:      'neutral',
  'n/a':        'neutral',
  frustrado:    'warning',
  negativo:     'danger',
  hostil:       'danger',
  muy_negativo: 'danger',
};

function money(n) {
  if (n == null) return '--';
  return `$${Number(n).toLocaleString('es')}`;
}

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

const TICK = { fontSize: 10, fill: 'var(--text-muted)' };
const TABS = ['Timeline', 'Promesas', 'Pagos', 'Planes'];

export default function ClienteDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);

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
      <div className="space-y-4 max-w-5xl mx-auto">
        <div className="ds-skeleton h-20" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          {[...Array(5)].map((_, i) => <div key={i} className="ds-skeleton h-20" />)}
        </div>
        <div className="ds-skeleton h-64" />
      </div>
    );
  }

  if (!cliente) {
    return (
      <div className="ds-empty" style={{ height: 400 }}>
        <div className="ds-empty-title">Cliente no encontrado</div>
        <button className="ds-btn ds-btn-ghost" style={{ marginTop: 12 }} onClick={() => navigate('/clientes')}>
          Volver a clientes
        </button>
      </div>
    );
  }

  const events = Array.isArray(timeline) ? timeline : (timeline?.timeline ?? []);
  const ini    = cliente.monto_deuda_inicial ?? 1;
  const status = getStatus(cliente);

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

  const pctRecuperado  = ini > 0 ? ((cliente.total_pagado ?? 0) / ini * 100).toFixed(1) : '0.0';
  const promesasAll    = cliente.promesas ?? [];
  const promesasCumpl  = promesasAll.filter(p => p.cumplida).length;
  const tasaCumpl      = promesasAll.length > 0
    ? ((promesasCumpl / promesasAll.length) * 100).toFixed(0)
    : null;

  const planes = cliente.planes ?? [];

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="ds-detail-header">
        <button className="ds-back-btn" onClick={() => navigate('/clientes')} style={{ marginBottom: 12 }}>
          <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Clientes
        </button>

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
          <div className="ds-avatar">
            {(cliente.nombre ?? 'C')[0].toUpperCase()}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 4 }}>
              <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>
                {cliente.nombre ?? cliente.id}
              </h1>
              <Badge label={status} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontFamily: 'monospace' }}>{cliente.id}</span>
              {cliente.telefono && <span>{cliente.telefono}</span>}
              {cliente.tipo_deuda && <span>{cliente.tipo_deuda.replace(/_/g, ' ')}</span>}
              {cliente.mejor_horario_contacto && (
                <span>Mejor horario: <strong style={{ color: 'var(--state-purple)' }}>{cliente.mejor_horario_contacto}</strong></span>
              )}
              {cliente.ultimo_agente_id && (
                <span>Último agente: <strong style={{ color: 'var(--text-secondary)' }}>{cliente.ultimo_agente_id}</strong></span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* KPIs fila 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        <StatCard label="Deuda Inicial"  value={money(ini)} />
        <StatCard label="Total Pagado"   value={money(cliente.total_pagado)}   variant="success" note={`${pctRecuperado}% recuperado`} />
        <StatCard label="Pendiente"      value={money(cliente.monto_pendiente)} variant="danger" />
        <StatCard label="Interacciones"  value={(cliente.interacciones ?? events).length ?? 0} />
        <StatCard
          label="Días sin contacto"
          value={cliente.dias_sin_contacto != null ? `${cliente.dias_sin_contacto}d` : '--'}
          variant={
            cliente.dias_sin_contacto == null ? 'default' :
            cliente.dias_sin_contacto <= 7    ? 'success' :
            cliente.dias_sin_contacto <= 30   ? 'warning' : 'danger'
          }
        />
      </div>

      {/* KPIs fila 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
        <StatCard
          label="Monto comprometido"
          value={money(cliente.monto_prometido_pendiente)}
          variant="warning"
          note="en promesas pendientes"
        />
        <StatCard
          label="Cumpl. promesas"
          value={tasaCumpl !== null ? `${promesasCumpl}/${promesasAll.length}` : 'Sin promesas'}
          note={tasaCumpl !== null ? `${tasaCumpl}% cumplidas` : undefined}
          variant={tasaCumpl === null ? 'default' : Number(tasaCumpl) >= 50 ? 'success' : 'danger'}
        />
        <StatCard
          label="Sentimiento"
          value={cliente.sentimiento_predominante ?? '--'}
          variant={SENT_BADGE[cliente.sentimiento_predominante] ?? 'default'}
        />
      </div>

      {/* Evolución + progreso */}
      <DataCard title="Evolución de la Deuda" subtitle="Progresión del pago a lo largo del tiempo">
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
            <span>Progreso de recuperación</span>
            <span style={{ fontWeight: 700, color: 'var(--state-success)' }}>{pctRecuperado}%</span>
          </div>
          <div style={{ background: 'var(--bg-elevated)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
            <div style={{
              width: `${Math.min(100, Number(pctRecuperado))}%`,
              height: '100%',
              background: 'linear-gradient(90deg, var(--state-success), #34d399)',
              borderRadius: 4,
              transition: 'width 700ms ease',
            }} />
          </div>
        </div>

        {evolution.length > 1 ? (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={evolution}>
              <defs>
                <linearGradient id="gDeuda" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--state-danger)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--state-danger)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gPagado" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--state-success)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--state-success)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="fecha" tick={TICK} angle={-30} textAnchor="end" height={44} />
              <YAxis tick={TICK} />
              <Tooltip
                formatter={(val) => money(val)}
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
              />
              <Area type="monotone" dataKey="deuda"  stroke="var(--state-danger)"  fill="url(#gDeuda)"  strokeWidth={2} name="Deuda" />
              <Area type="monotone" dataKey="pagado" stroke="var(--state-success)" fill="url(#gPagado)" strokeWidth={2} name="Pagado" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="ds-empty"><div className="ds-empty-desc">Sin pagos registrados</div></div>
        )}
      </DataCard>

      {/* Tabs: Timeline / Promesas / Pagos / Planes */}
      <DataCard flush>
        <div style={{ padding: '0 20px' }}>
          <div className="ds-tabs">
            {TABS.map((tab, i) => (
              <button
                key={tab}
                className={`ds-tab${activeTab === i ? ' ds-tab-active' : ''}`}
                onClick={() => setActiveTab(i)}
              >
                {tab}
                {i === 0 && events.length > 0 && (
                  <span style={{ marginLeft: 6, fontSize: 10, background: 'var(--bg-elevated)', padding: '1px 6px', borderRadius: 10, color: 'var(--text-muted)' }}>
                    {events.length}
                  </span>
                )}
                {i === 1 && (
                  <span style={{ marginLeft: 6, fontSize: 10, background: 'var(--bg-elevated)', padding: '1px 6px', borderRadius: 10, color: 'var(--text-muted)' }}>
                    {promesasAll.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div style={{ padding: '0 20px 20px' }}>
          {/* Tab: Timeline */}
          {activeTab === 0 && (
            <div style={{ maxHeight: 520, overflowY: 'auto', paddingRight: 4 }}>
              {events.length === 0 ? (
                <div className="ds-empty"><div className="ds-empty-desc">Sin interacciones registradas</div></div>
              ) : (
                events.map((ev, i) => {
                  const sent      = ev.sentimiento_cliente ?? ev.sentimiento ?? 'neutral';
                  const resultado = ev.resultado ?? ev.tipo ?? 'contacto';
                  const dotColor  = RESULT_COLORS[resultado] ?? 'var(--text-muted)';
                  const duracion  = ev.duracion_segundos
                    ? `${ev.duracion_segundos}s`
                    : ev.duracion_minutos ? `${ev.duracion_minutos} min` : '';

                  return (
                    <div key={i} className="ds-timeline-item">
                      {i < events.length - 1 && <div className="ds-timeline-line" />}
                      <div className="ds-timeline-dot" style={{ background: dotColor }} />
                      <div className="ds-timeline-card">
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                                {resultado.replace(/_/g, ' ')}
                              </span>
                              <Badge label={sent} variant={SENT_BADGE[sent] ?? 'neutral'} />
                              {ev.agente_id && (
                                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>por {ev.agente_id}</span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>
                              {ev.timestamp ?? ev.fecha ?? '--'}
                              {duracion && ` · ${duracion}`}
                            </div>
                          </div>
                        </div>

                        {(ev.promesas?.length > 0 || ev.pagos?.length > 0 || ev.planes?.length > 0) && (
                          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-soft)', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {(ev.promesas ?? []).map((p, j) => (
                              <Badge key={`pr-${j}`} label={`Promesa: ${money(p.monto_prometido ?? p.monto)}`} variant="warning" />
                            ))}
                            {(ev.pagos ?? []).map((p, j) => (
                              <Badge key={`pa-${j}`} label={`Pago: ${money(p.monto)}`} variant="success" />
                            ))}
                            {(ev.planes ?? []).map((p, j) => (
                              <Badge key={`pl-${j}`} label={`Plan: ${p.cuotas ?? '?'} cuotas · ${money(p.monto_mensual)}/mes`} variant="purple" />
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Tab: Promesas */}
          {activeTab === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
              {promesasAll.length === 0 ? (
                <div className="ds-empty"><div className="ds-empty-desc">Sin promesas registradas</div></div>
              ) : (
                promesasAll.map((p, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 14px', background: 'var(--bg-elevated)',
                    borderRadius: 8, border: '1px solid var(--border-soft)',
                  }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {money(p.monto_prometido ?? p.monto)}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      {(p.fecha_promesa ?? p.fecha ?? '--').slice(0, 10)}
                    </span>
                    <Badge label={p.cumplida ? 'Cumplida' : 'Pendiente'} variant={p.cumplida ? 'success' : 'warning'} />
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab: Pagos */}
          {activeTab === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
              {pagos.length === 0 ? (
                <div className="ds-empty"><div className="ds-empty-desc">Sin pagos registrados</div></div>
              ) : (
                pagos.map((p, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 14px', background: 'var(--bg-elevated)',
                    borderRadius: 8, border: '1px solid var(--border-soft)',
                  }}>
                    <span style={{ fontWeight: 700, color: 'var(--state-success)' }}>{money(p.monto)}</span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{(p.fecha ?? '--').slice(0, 10)}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{p.metodo_pago ?? ''}</span>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab: Planes */}
          {activeTab === 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' }}>
              {planes.length === 0 ? (
                <div className="ds-empty"><div className="ds-empty-desc">Sin planes activos</div></div>
              ) : (
                planes.map((p, i) => (
                  <div key={i} style={{
                    padding: '12px 14px', background: 'var(--bg-elevated)',
                    borderRadius: 8, border: '1px solid var(--state-purple-bg)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontWeight: 700, color: 'var(--state-purple)' }}>
                        {money(p.monto_mensual)}/mes
                      </span>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {p.cuotas ?? p.num_cuotas ?? '?'} cuotas
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      Total plan: {money(p.monto_total_plan)}
                      {p.fecha_inicio ? ` · desde ${String(p.fecha_inicio).slice(0, 10)}` : ''}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </DataCard>
    </div>
  );
}
