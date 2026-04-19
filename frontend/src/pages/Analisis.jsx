import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPrediccion, getAnomalias, getEstrategias } from '../api/client';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';
import DataCard from '../components/ui/DataCard';

const TABS = [
  { id: 'prediccion',  label: 'Análisis Predictivo' },
  { id: 'anomalias',   label: 'Detección de Anomalías' },
  { id: 'estrategias', label: 'Optimización de Estrategias' },
];

const RISK_COLORS = { alto: '#ef4444', medio: '#f59e0b', bajo: '#10b981' };
const SEV_COLORS  = { alta: '#ef4444', media: '#f59e0b', baja: '#06b6d4' };
const SEG_COLORS  = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'];
const TICK        = { fontSize: 10, fill: 'var(--text-muted)' };

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
  const error   = (tab === 'prediccion' && e1) || (tab === 'anomalias' && e2) || (tab === 'estrategias' && e3);

  return (
    <div className="max-w-7xl mx-auto" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Tabs — sticky dentro del scroll container del main */}
      <div style={{
        position: 'sticky',
        top: 'var(--topbar-height)',
        zIndex: 9,
        background: 'var(--bg-base)',
        marginLeft: 'calc(-1 * var(--content-pad))',
        marginRight: 'calc(-1 * var(--content-pad))',
        padding: '8px var(--content-pad) 0',
        borderBottom: '1px solid var(--border-soft)',
      }}>
        <div className="ds-tabs" style={{ marginBottom: 0 }}>
          {TABS.map(t => (
            <button
              key={t.id}
              className={`ds-tab${tab === t.id ? ' ds-tab-active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 0', gap: 12 }}>
          <div style={{
            width: 36, height: 36, border: '3px solid var(--border-medium)',
            borderTopColor: 'var(--accent-primary)', borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Ejecutando modelos de ML…</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {error && !loading && (
        <div style={{
          background: 'var(--state-danger-bg)', border: '1px solid rgba(239,68,68,0.25)',
          borderRadius: 12, padding: 24, textAlign: 'center',
        }}>
          <p style={{ color: 'var(--state-danger)', fontWeight: 600, marginBottom: 4 }}>Error al cargar datos</p>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {error?.message?.includes('Network Error')
              ? 'No se pudo conectar con el servidor. Verifica que el backend esté corriendo.'
              : error?.response?.data?.detail || error?.message || 'Error desconocido'}
          </p>
        </div>
      )}

      {tab === 'prediccion'  && !l1 && prediccion  && <PrediccionTab  data={prediccion}  navigate={navigate} />}
      {tab === 'anomalias'   && !l2 && anomalias   && <AnomaliasTab   data={anomalias} />}
      {tab === 'estrategias' && !l3 && estrategias && <EstrategiasTab data={estrategias} navigate={navigate} />}
    </div>
  );
}

function MetricCell({ value, suffix = '', good, bad, isCount = false }) {
  if (value == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  const isGood = good?.(value);
  const isBad  = bad?.(value);
  const color  = isGood ? 'var(--state-success)' : isBad ? 'var(--state-danger)' : 'var(--state-warning)';
  return (
    <span style={{ fontSize: 12, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums' }}>
      {isCount ? value : `${value}${suffix}`}
    </span>
  );
}

const NEGATIVE_KEYWORDS = ['sin ', 'baja', 'muy baja', 'hostil', 'frustrad', 'decreciente', 'pendiente', 'último pago hace', 'solo '];
const POSITIVE_KEYWORDS = ['consistente', 'alta tasa'];

function FactorPills({ factors }) {
  if (!factors?.length) return <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>—</span>;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {factors.map((f, i) => {
        const lower = f.toLowerCase();
        const isNeg = NEGATIVE_KEYWORDS.some(k => lower.includes(k));
        const isPos = POSITIVE_KEYWORDS.some(k => lower.includes(k));
        const color = isNeg ? 'var(--state-danger)' : isPos ? 'var(--state-success)' : 'var(--text-muted)';
        const bg    = isNeg ? 'rgba(239,68,68,0.08)' : isPos ? 'rgba(16,185,129,0.08)' : 'var(--bg-elevated)';
        return (
          <span key={i} style={{
            fontSize: 10, fontWeight: 500, padding: '2px 7px', borderRadius: 4,
            background: bg, color, whiteSpace: 'nowrap',
          }}>
            {f}
          </span>
        );
      })}
    </div>
  );
}

// ── Prediccion ────────────────────────────────────────────────
function PrediccionTab({ data, navigate }) {
  const clientes = Array.isArray(data) ? data : [];
  const modelInfo = clientes[0]?._modelo;

  const riskDistribution = [
    { name: 'Alto',  value: clientes.filter(c => c.categoria_riesgo === 'alto').length,  fill: RISK_COLORS.alto },
    { name: 'Medio', value: clientes.filter(c => c.categoria_riesgo === 'medio').length, fill: RISK_COLORS.medio },
    { name: 'Bajo',  value: clientes.filter(c => c.categoria_riesgo === 'bajo').length,  fill: RISK_COLORS.bajo },
  ];

  const top10 = clientes.slice(0, 10);

  const featureData = modelInfo?.feature_importances
    ? Object.entries(modelInfo.feature_importances)
        .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value: Math.round(value * 100) }))
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <div className="space-y-5">
      {modelInfo && (
        <div style={{
          background: 'var(--state-purple-bg)', border: '1px solid rgba(139,92,246,0.2)',
          borderRadius: 12, padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 12,
        }}>
          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--state-purple)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Modelo ML activo
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
              {modelInfo.modelo?.replace(/_\d+$/, '')}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              Modo: <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
                {modelInfo.label_mode === 'temporal_split' ? 'Corte temporal (datos reales)' : (modelInfo.label_mode ?? '—')}
              </span>
            </span>
          </div>
          {/* Metrics row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
            {[
              { label: 'ROC-AUC',   value: modelInfo.metrics?.roc_auc   != null ? (modelInfo.metrics.roc_auc   * 100).toFixed(1) + '%' : '—' },
              { label: 'Accuracy',  value: modelInfo.metrics?.accuracy   != null ? (modelInfo.metrics.accuracy  * 100).toFixed(0) + '%' : '—' },
              { label: 'Precision', value: modelInfo.metrics?.precision  != null ? (modelInfo.metrics.precision * 100).toFixed(0) + '%' : '—' },
              { label: 'Recall',    value: modelInfo.metrics?.recall     != null ? (modelInfo.metrics.recall    * 100).toFixed(0) + '%' : '—' },
              { label: 'F1',        value: modelInfo.metrics?.f1         != null ? (modelInfo.metrics.f1        * 100).toFixed(0) + '%' : '—' },
            ].map(({ label, value }) => (
              <div key={label} style={{
                textAlign: 'center', background: 'var(--bg-elevated)',
                borderRadius: 8, padding: '8px 4px',
                border: '1px solid rgba(139,92,246,0.12)',
              }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--state-purple)' }}>{value}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>
          {/* Nota: Precision/Recall/F1 = 0 es esperado con datos desbalanceados */}
          {(modelInfo.metrics?.precision === 0 || modelInfo.metrics?.recall === 0) && (
            <div style={{
              fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5,
              padding: '8px 10px', background: 'rgba(139,92,246,0.06)',
              borderRadius: 6, borderLeft: '3px solid rgba(139,92,246,0.3)',
            }}>
              <strong style={{ color: 'var(--text-secondary)' }}>¿Por qué Precision/Recall/F1 = 0%?</strong>{' '}
              Con solo ~50 clientes y pocos pagos confirmados post-corte, el modelo predice "no paga" para todos (clase mayoritaria).
              El <strong style={{ color: 'var(--state-purple)' }}>ROC-AUC de {(modelInfo.metrics.roc_auc * 100).toFixed(1)}%</strong> confirma
              que el modelo sí distingue quién es más o menos riesgoso — ese ordenamiento es el que usa el ranking de terciles.
              Con más datos históricos, Precision y Recall mejorarían.
            </div>
          )}
        </div>
      )}

      {/* Risk summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {riskDistribution.map(r => (
          <div key={r.name} className="ds-stat-card" style={{ borderLeft: `3px solid ${r.fill}` }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
              Riesgo {r.name}
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, color: r.fill }}>{r.value}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>clientes</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        <DataCard title="Distribución de Riesgo">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={riskDistribution} cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                dataKey="value" paddingAngle={3} label={({ name, value }) => `${name}: ${value}`}>
                {riskDistribution.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </DataCard>

        <DataCard title="Top 10 Clientes por Riesgo">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={top10} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={['auto', 'auto']} tick={TICK} tickFormatter={v => `${v}%`} />
              <YAxis dataKey="nombre" type="category" tick={{ fontSize: 9, fill: 'var(--text-secondary)' }} width={80} />
              <Tooltip
                formatter={(v) => [`${v}%`, 'Score']}
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
              />
              <Bar dataKey="score_riesgo" radius={[0, 4, 4, 0]}>
                {top10.map((entry, i) => <Cell key={i} fill={RISK_COLORS[entry.categoria_riesgo] ?? '#4a5568'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </DataCard>

        {featureData.length > 0 && (
          <DataCard title="Importancia de Variables">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={featureData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={TICK} tickFormatter={v => `${v}%`} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 8, fill: 'var(--text-secondary)' }} width={100} />
                <Tooltip
                  formatter={(v) => [`${v}%`, 'Importancia']}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
                />
                <Bar dataKey="value" fill="var(--state-purple)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </DataCard>
        )}
      </div>

      {/* Detail table */}
      <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '4px 0 8px', fontStyle: 'italic' }}>
        El riesgo es una posición relativa (tercil) entre todos los clientes, no un umbral absoluto.
        Un cliente puede tener 0% pagado pero riesgo "medio" si sus otros indicadores son mejores que el tercio inferior.
      </div>

      <DataCard
        title="Detalle por Cliente"
        subtitle="Clic en una fila para ver el perfil completo"
        flush
      >
        <div className="ds-table-scroll">
          <table className="ds-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th className="center">Riesgo</th>
                <th className="center" title="Porcentaje de deuda ya pagada">Deuda pagada</th>
                <th className="center" title="Número de pagos realizados">Pagos</th>
                <th className="center" title="Promesas de pago que cumplió">Cumplimiento</th>
                <th className="center" title="Interacciones con el equipo">Contactos</th>
                <th>Señales del modelo</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map(c => {
                const m = c.metricas ?? {};
                const pagadoPct = m.deuda_pendiente_pct != null ? (100 - m.deuda_pendiente_pct) : null;
                return (
                <tr key={c.cliente_id} onClick={() => navigate(`/clientes/${c.cliente_id}`)}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{c.nombre}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                      Prob. pago: <span style={{
                        fontWeight: 700,
                        color: c.probabilidad_pago >= 60 ? 'var(--state-success)'
                             : c.probabilidad_pago >= 30 ? 'var(--state-warning)'
                             : 'var(--state-danger)',
                      }}>{c.probabilidad_pago}%</span>
                    </div>
                  </td>
                  <td className="center">
                    <span style={{
                      fontSize: 11, fontWeight: 700, padding: '2px 10px', borderRadius: 4,
                      background: (RISK_COLORS[c.categoria_riesgo] ?? '#4a5568') + '20',
                      color: RISK_COLORS[c.categoria_riesgo] ?? 'var(--text-muted)',
                    }}>
                      {c.categoria_riesgo}
                    </span>
                  </td>
                  <td className="center">
                    <MetricCell value={pagadoPct} suffix="%" good={v => v >= 30} bad={v => v < 5} />
                  </td>
                  <td className="center">
                    <MetricCell value={m.total_pagos} good={v => v >= 3} bad={v => v === 0} isCount />
                  </td>
                  <td className="center">
                    <MetricCell value={m.tasa_cumplimiento} suffix="%" good={v => v >= 50} bad={v => v < 15} />
                  </td>
                  <td className="center">
                    <MetricCell value={m.total_interacciones} good={v => v >= 5} bad={v => v <= 1} isCount />
                  </td>
                  <td style={{ maxWidth: 260 }}>
                    <FactorPills factors={c.factores} />
                  </td>
                </tr>
              );
              })}
            </tbody>
          </table>
        </div>
      </DataCard>
    </div>
  );
}

// ── Anomalias ────────────────────────────────────────────────
function AnomaliasTab({ data }) {
  const { anomalias = [], por_severidad = {}, total_anomalias = 0, modelos_utilizados = [] } = data;

  return (
    <div className="space-y-5">
      {modelos_utilizados.length > 0 && (
        <div style={{
          background: 'var(--state-warning-bg)', border: '1px solid rgba(245,158,11,0.2)',
          borderRadius: 12, padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--state-warning)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Modelos de Detección
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
              {total_anomalias} anomalía{total_anomalias !== 1 ? 's' : ''} detectada{total_anomalias !== 1 ? 's' : ''}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {modelos_utilizados.map((m, i) => (
              <span key={i} style={{
                fontSize: 11, fontWeight: 500,
                background: 'var(--bg-elevated)', color: 'var(--state-warning)',
                padding: '4px 10px', borderRadius: 6,
                border: '1px solid rgba(245,158,11,0.2)',
              }}>
                {m}
              </span>
            ))}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5, padding: '6px 10px', background: 'rgba(245,158,11,0.06)', borderRadius: 6, borderLeft: '3px solid rgba(245,158,11,0.3)' }}>
            La detección usa <strong style={{ color: 'var(--text-secondary)' }}>Isolation Forest</strong> y <strong style={{ color: 'var(--text-secondary)' }}>Z-Score</strong> para identificar clientes con comportamiento estadísticamente atípico (deuda muy alta, sin contacto prolongado, sentimiento extremo).
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
        <div className="ds-stat-card">
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: 8 }}>
            Total Anomalías
          </div>
          <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--text-primary)' }}>{total_anomalias}</div>
        </div>
        {Object.entries(por_severidad).map(([sev, count]) => (
          <div key={sev} className="ds-stat-card" style={{ borderLeft: `3px solid ${SEV_COLORS[sev] ?? 'var(--text-muted)'}` }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: 8 }}>
              Severidad {sev}
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, color: SEV_COLORS[sev] ?? 'var(--text-primary)' }}>{count}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {anomalias.map((a, i) => (
          <div key={i} style={{
            background: 'var(--bg-surface)', border: '1px solid var(--border-medium)',
            borderLeft: `3px solid ${SEV_COLORS[a.severidad] ?? 'var(--border-medium)'}`,
            borderRadius: 8, padding: '14px 16px',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                  <span style={{
                    fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                    background: (SEV_COLORS[a.severidad] ?? '#4a5568') + '20',
                    color: SEV_COLORS[a.severidad] ?? 'var(--text-muted)',
                  }}>
                    {a.severidad}
                  </span>
                  <span style={{ fontSize: 11, background: 'var(--bg-elevated)', color: 'var(--text-secondary)', padding: '2px 8px', borderRadius: 4 }}>
                    {a.tipo?.replace(/_/g, ' ')}
                  </span>
                  {a.modelo && <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{a.modelo}</span>}
                </div>
                <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', margin: 0 }}>{a.descripcion}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{a.referencia}</p>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.entidad_tipo}</div>
                <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{a.entidad_id}</div>
              </div>
            </div>
          </div>
        ))}
        {anomalias.length === 0 && (
          <div className="ds-empty"><div className="ds-empty-title">No se detectaron anomalías</div></div>
        )}
      </div>
    </div>
  );
}

// ── Estrategias ──────────────────────────────────────────────
const IMPACTO_COLORS = { alto: '#ef4444', medio: '#f59e0b', bajo: '#06b6d4' };

function EstrategiasTab({ data, navigate }) {
  const {
    mejores_horas = [],
    agentes = [],
    cluster_profiles = [],
    mejor_agente_por_resultado = {},
    recomendaciones = [],
    modelo,
  } = data;

  const segData = cluster_profiles.map((p, i) => ({
    name: p.nombre,
    value: p.count,
    fill: SEG_COLORS[i % SEG_COLORS.length],
  }));

  const RESULTADO_LABEL = {
    promesa_pago:   'Mejor en Promesas',
    pago_inmediato: 'Mejor en Pago Inm.',
    renegociacion:  'Mejor en Renegociación',
  };

  return (
    <div className="space-y-5">

      {/* Model card */}
      {modelo && (
        <div style={{
          background: 'var(--state-success-bg)', border: '1px solid rgba(16,185,129,0.2)',
          borderRadius: 12, padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--state-success)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Modelo de Segmentación
            </span>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
              {modelo.tipo} · k={modelo.k_optimo} clusters óptimos
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {[
              { label: 'Inertia (SSE)', value: modelo.inertia?.toFixed(2) ?? '—' },
              { label: 'Silhouette',    value: modelo.silhouette?.toFixed(4) ?? '—' },
              { label: 'Davies-Bouldin',value: modelo.davies_bouldin?.toFixed(4) ?? '—' },
            ].map(({ label, value }) => (
              <div key={label} style={{
                textAlign: 'center', background: 'var(--bg-elevated)',
                borderRadius: 8, padding: '8px 4px',
                border: '1px solid rgba(16,185,129,0.15)',
              }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--state-success)' }}>{value}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5, padding: '6px 10px', background: 'rgba(16,185,129,0.06)', borderRadius: 6, borderLeft: '3px solid rgba(16,185,129,0.3)' }}>
            <strong style={{ color: 'var(--text-secondary)' }}>K-Means</strong> agrupa los {cluster_profiles.reduce((s, p) => s + p.count, 0)} clientes en {modelo.k_optimo} segmentos según comportamiento de pago, sentimiento y engagement. Silhouette más alto = clusters más compactos y separados.
          </div>
        </div>
      )}

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <DataCard title="Segmentación de Cartera">
          {segData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={segData} cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                  dataKey="value" paddingAngle={3}
                  label={({ name, value }) => `${value}`}>
                  {segData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Pie>
                <Tooltip
                  formatter={(v, _n, props) => [v + ' clientes', props.payload?.name]}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 10 }}
                  formatter={(value, entry) => entry.payload?.name ?? value}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="ds-empty"><div className="ds-empty-title">Sin datos de segmentación</div></div>
          )}
        </DataCard>

        <DataCard title="Horarios con Mayor Éxito">
          {mejores_horas.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={mejores_horas}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hora" tickFormatter={h => `${h}:00`} tick={TICK} />
                <YAxis tick={TICK} tickFormatter={v => `${v}%`} />
                <Tooltip
                  formatter={(v, name) => [`${v}%`, 'Tasa de éxito']}
                  labelFormatter={h => `Hora: ${h}:00`}
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
                />
                <Bar dataKey="tasa_exito" fill="var(--state-success)" name="Tasa Éxito %" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="ds-empty"><div className="ds-empty-title">Sin datos de horarios</div></div>
          )}
        </DataCard>
      </div>

      {/* Cluster profiles — un card por segmento con sus clientes */}
      {cluster_profiles.length > 0 && (
        <DataCard title="Perfiles de Segmento" subtitle="Estrategia recomendada por cluster">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {cluster_profiles.map((p, i) => (
              <div key={p.key} style={{
                borderRadius: 8, overflow: 'hidden',
                border: `1px solid ${SEG_COLORS[i % SEG_COLORS.length]}30`,
              }}>
                {/* Segment header */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 14px',
                  background: `${SEG_COLORS[i % SEG_COLORS.length]}10`,
                  borderBottom: `1px solid ${SEG_COLORS[i % SEG_COLORS.length]}20`,
                }}>
                  <span style={{
                    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                    background: SEG_COLORS[i % SEG_COLORS.length],
                  }} />
                  <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                    {p.nombre}
                  </span>
                  <span style={{
                    fontSize: 11, fontWeight: 700, padding: '1px 8px', borderRadius: 4, marginLeft: 4,
                    background: (IMPACTO_COLORS[p.impacto] ?? '#4a5568') + '20',
                    color: IMPACTO_COLORS[p.impacto] ?? 'var(--text-muted)',
                  }}>
                    impacto {p.impacto}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)' }}>
                    {p.count} cliente{p.count !== 1 ? 's' : ''}
                  </span>
                </div>
                {/* Strategy */}
                <div style={{ padding: '8px 14px', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, background: 'var(--bg-surface)' }}>
                  {p.estrategia}
                </div>
                {/* Clients mini-table */}
                {p.clientes?.length > 0 && (
                  <div style={{ overflowX: 'auto' }}>
                    <table className="ds-table" style={{ fontSize: 11 }}>
                      <thead>
                        <tr>
                          <th>Cliente</th>
                          <th className="right">Pendiente</th>
                          <th className="right">% Pend.</th>
                          <th className="right">Cumplimiento</th>
                        </tr>
                      </thead>
                      <tbody>
                        {p.clientes.map(c => (
                          <tr key={c.cliente_id} onClick={() => navigate(`/clientes/${c.cliente_id}`)}>
                            <td style={{ fontWeight: 500 }}>{c.nombre}</td>
                            <td className="right" style={{ fontVariantNumeric: 'tabular-nums' }}>
                              ${(c.deuda_pendiente ?? 0).toLocaleString('es')}
                            </td>
                            <td className="right" style={{
                              fontWeight: 700,
                              color: c.pct_pendiente <= 30 ? 'var(--state-success)'
                                   : c.pct_pendiente <= 70 ? 'var(--state-warning)'
                                   : 'var(--state-danger)',
                            }}>
                              {c.pct_pendiente}%
                            </td>
                            <td className="right" style={{
                              fontWeight: 600,
                              color: c.tasa_cumplimiento >= 50 ? 'var(--state-success)'
                                   : c.tasa_cumplimiento > 0  ? 'var(--state-warning)'
                                   : 'var(--state-danger)',
                            }}>
                              {c.tasa_cumplimiento}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        </DataCard>
      )}

      {/* Mejor agente por tipo de resultado */}
      {Object.keys(mejor_agente_por_resultado).length > 0 && (
        <DataCard title="Mejor Agente por Tipo de Resultado">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 10 }}>
            {Object.entries(mejor_agente_por_resultado).map(([tipo, info]) => (
              <div
                key={tipo}
                onClick={() => navigate(`/agentes/${info.agente_id}`)}
                style={{
                  padding: '12px 14px', borderRadius: 8, cursor: 'pointer',
                  background: 'var(--bg-elevated)', border: '1px solid var(--border-soft)',
                  transition: 'border-color 150ms',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-focus)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-soft)'}
              >
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                  {RESULTADO_LABEL[tipo] ?? tipo.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 2 }}>
                  {info.agente_id?.replace('agente_', 'Agente ')}
                </div>
                <div style={{ fontSize: 11, color: 'var(--state-success)', fontWeight: 600 }}>
                  {info.tasa_tipo}% · {info.total_llamadas} llamadas
                </div>
              </div>
            ))}
          </div>
        </DataCard>
      )}

      {/* Recomendaciones */}
      {recomendaciones.length > 0 && (
        <DataCard title="Recomendaciones de Estrategia" subtitle="Generadas por el análisis de segmentación">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {recomendaciones.map((r, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                padding: '12px 14px', background: 'var(--bg-elevated)',
                border: '1px solid var(--border-soft)', borderRadius: 8,
              }}>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 4, flexShrink: 0, marginTop: 2,
                  background: (IMPACTO_COLORS[r.impacto] ?? '#4a5568') + '20',
                  color: IMPACTO_COLORS[r.impacto] ?? 'var(--text-muted)',
                }}>
                  {r.impacto}
                </span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{r.titulo}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.5 }}>{r.descripcion}</div>
                </div>
              </div>
            ))}
          </div>
        </DataCard>
      )}

    </div>
  );
}
