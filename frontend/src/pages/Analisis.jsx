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
    <div className="space-y-5 max-w-7xl mx-auto">
      {/* Tabs */}
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
          borderRadius: 12, padding: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--state-purple)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
                Modelo ML
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                {modelInfo.modelo} ({modelInfo.n_estimators} árboles)
              </div>
            </div>
            <div style={{ display: 'flex', gap: 20 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--state-purple)' }}>{modelInfo.accuracy_train}%</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Accuracy</div>
              </div>
              {modelInfo.cross_validation && (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--state-purple)' }}>{modelInfo.cross_validation.accuracy_mean}%</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>CV {modelInfo.cross_validation.folds}-fold</div>
                </div>
              )}
            </div>
          </div>
          {modelInfo.label_criteria && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(139,92,246,0.15)', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {modelInfo.label_criteria.map((c, i) => (
                <span key={i} style={{
                  fontSize: 11, background: 'var(--bg-elevated)',
                  color: 'var(--state-purple)', padding: '2px 8px', borderRadius: 4,
                }}>
                  {c}
                </span>
              ))}
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
              <XAxis type="number" domain={[0, 100]} tick={TICK} />
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
      <DataCard title="Detalle por Cliente" subtitle="Clic en una fila para ver el detalle del cliente" flush>
        <div style={{ overflowY: 'auto', maxHeight: 400 }}>
          <table className="ds-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th className="center">Riesgo</th>
                <th className="right">Score</th>
                <th className="right">Prob. Pago</th>
                <th>Factores Principales</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map(c => (
                <tr key={c.cliente_id} onClick={() => navigate(`/clientes/${c.cliente_id}`)}>
                  <td style={{ fontWeight: 500 }}>{c.nombre}</td>
                  <td className="center">
                    <span style={{
                      fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                      background: (RISK_COLORS[c.categoria_riesgo] ?? '#4a5568') + '20',
                      color: RISK_COLORS[c.categoria_riesgo] ?? 'var(--text-muted)',
                    }}>
                      {c.categoria_riesgo}
                    </span>
                  </td>
                  <td className="right" style={{ fontFamily: 'monospace', fontSize: 12 }}>{c.score_riesgo}</td>
                  <td className="right" style={{
                    fontWeight: 700,
                    color: c.probabilidad_pago >= 60 ? 'var(--state-success)'
                         : c.probabilidad_pago >= 30 ? 'var(--state-warning)'
                         : 'var(--state-danger)',
                  }}>
                    {c.probabilidad_pago}%
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 260 }}>
                    {c.factores?.join(', ')}
                  </td>
                </tr>
              ))}
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
          borderRadius: 12, padding: 14,
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--state-warning)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 8 }}>
            Modelos de Detección
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {modelos_utilizados.map((m, i) => (
              <span key={i} style={{
                fontSize: 11, background: 'var(--bg-elevated)',
                color: 'var(--state-warning)', padding: '2px 8px', borderRadius: 4,
              }}>
                {m}
              </span>
            ))}
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
function EstrategiasTab({ data, navigate }) {
  const { mejores_horas = [], segmentos = {}, detalle_segmentos = {}, recomendaciones = [], modelo } = data;

  const segData = [
    { name: 'Quick Wins',    value: segmentos.quick_wins      ?? 0 },
    { name: 'Alto Potencial', value: segmentos.alto_potencial  ?? 0 },
    { name: 'Req. Atención',  value: segmentos.requiere_atencion ?? 0 },
    { name: 'Críticos',       value: segmentos.casos_criticos   ?? 0 },
  ];

  const IMPACTO_COLORS = { alto: '#ef4444', medio: '#f59e0b', bajo: '#06b6d4' };

  return (
    <div className="space-y-5">
      {modelo && (
        <div style={{
          background: 'var(--state-success-bg)', border: '1px solid rgba(16,185,129,0.2)',
          borderRadius: 12, padding: 14,
          display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
        }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--state-success)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
              Modelo de Segmentación
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
              {modelo.tipo} ({modelo.n_clusters} clusters)
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--state-success)' }}>{modelo.inertia?.toLocaleString()}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Inertia (SSE)</div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <DataCard title="Segmentación de Cartera">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={segData} cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                dataKey="value" paddingAngle={3} label={({ name, value }) => `${name}: ${value}`}>
                {segData.map((_, i) => <Cell key={i} fill={SEG_COLORS[i]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </DataCard>

        <DataCard title="Horarios con Mayor Éxito">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={mejores_horas}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hora" tickFormatter={h => `${h}:00`} tick={TICK} />
              <YAxis tick={TICK} />
              <Tooltip
                formatter={(v, name) => [name === 'tasa_exito' ? `${v}%` : v, name === 'tasa_exito' ? 'Tasa Éxito' : 'Total']}
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-medium)', borderRadius: 8 }}
              />
              <Bar dataKey="tasa_exito" fill="var(--state-success)" name="Tasa Éxito %" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </DataCard>
      </div>

      {/* Recomendaciones */}
      <DataCard title="Recomendaciones de Estrategia" subtitle="Sugerencias basadas en el análisis ML">
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

      {/* Quick wins */}
      {(detalle_segmentos.quick_wins ?? []).length > 0 && (
        <DataCard title="Quick Wins" subtitle="Clientes con mayor probabilidad de cerrar su deuda" flush>
          <div style={{ overflowY: 'auto', maxHeight: 280 }}>
            <table className="ds-table">
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th className="right">Pendiente</th>
                  <th className="right">% Pendiente</th>
                  <th className="right">Cumplimiento</th>
                </tr>
              </thead>
              <tbody>
                {detalle_segmentos.quick_wins.map(c => (
                  <tr key={c.cliente_id} onClick={() => navigate(`/clientes/${c.cliente_id}`)}>
                    <td style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>{c.nombre}</td>
                    <td className="right" style={{ fontWeight: 600 }}>${c.deuda_pendiente.toLocaleString('es')}</td>
                    <td className="right" style={{ fontWeight: 700, color: 'var(--state-success)' }}>{c.pct_pendiente}%</td>
                    <td className="right" style={{ fontWeight: 600 }}>{c.tasa_cumplimiento}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataCard>
      )}
    </div>
  );
}
