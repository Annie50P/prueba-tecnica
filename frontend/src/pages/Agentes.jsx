import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getAgentes } from '../api/client';
import DataCard from '../components/ui/DataCard';
import MiniBar from '../components/ui/MiniBar';

function pct(n) { return n == null ? '--' : `${(n * 100).toFixed(1)}%`; }

const RANK_STYLES = [
  { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', label: '1°' },
  { color: '#94a3b8', bg: 'rgba(148,163,184,0.12)', label: '2°' },
  { color: '#c2773a', bg: 'rgba(194,119,58,0.12)',  label: '3°' },
];

function getRankStyle(idx) {
  return RANK_STYLES[idx] ?? { color: 'var(--text-muted)', bg: 'var(--bg-elevated)', label: `${idx + 1}°` };
}

function AgentInitials(agent) {
  return (agent.nombre ?? agent.id ?? '?')
    .replace('agente_0', '').replace('agente_', '')
    .slice(0, 2).toUpperCase();
}

const SORT_OPTIONS = [
  { key: 'tasa_exito',          label: 'Éxito' },
  { key: 'tasa_promesa',        label: 'Promesas' },
  { key: 'tasa_pago_inmediato', label: 'Pago inm.' },
  { key: 'total_llamadas',      label: 'Llamadas' },
];

export default function Agentes() {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState('tasa_exito');

  const { data, isLoading } = useQuery({ queryKey: ['agentes'], queryFn: getAgentes });
  const agentes = Array.isArray(data) ? data : (data?.agentes ?? []);

  if (isLoading) {
    return (
      <div className="space-y-4 max-w-5xl mx-auto">
        <div className="ds-skeleton h-48" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {[...Array(6)].map((_, i) => <div key={i} className="ds-skeleton h-36" />)}
        </div>
      </div>
    );
  }

  const withExito = agentes.map(a => ({
    ...a,
    tasa_exito: Math.min((a.tasa_promesa ?? 0) + (a.tasa_pago_inmediato ?? 0), 1),
  }));

  const sorted = [...withExito].sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0));

  if (agentes.length === 0) {
    return (
      <div className="ds-empty" style={{ height: 400 }}>
        <div className="ds-empty-title">No se encontraron agentes</div>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Ranking table */}
      <DataCard
        title="Ranking del Equipo"
        subtitle="Ordenar por métrica"
        aside={
          <div style={{ display: 'flex', gap: 4 }}>
            {SORT_OPTIONS.map(opt => (
              <button
                key={opt.key}
                onClick={() => setSortKey(opt.key)}
                className={`ds-btn ${sortKey === opt.key ? 'ds-btn-active' : 'ds-btn-ghost'}`}
                style={{ fontSize: 11, padding: '4px 10px' }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        }
        flush
      >
        <div className="ds-table-wrap">
          <table className="ds-table">
            <thead>
              <tr>
                <th style={{ width: 48 }}>#</th>
                <th>Agente</th>
                <th style={{ minWidth: 130 }}>Tasa Éxito</th>
                <th style={{ minWidth: 120 }}>Promesas</th>
                <th style={{ minWidth: 120 }}>Pago Inm.</th>
                <th className="right">Llamadas</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((a, idx) => {
                const rank = getRankStyle(idx);
                return (
                  <tr key={a.id} onClick={() => navigate(`/agentes/${a.id}`)}>
                    <td>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        width: 28, height: 20, borderRadius: 4,
                        background: rank.bg, color: rank.color,
                        fontSize: 11, fontWeight: 700,
                      }}>
                        {rank.label}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{
                          width: 30, height: 30, borderRadius: 8,
                          background: 'linear-gradient(135deg, #374151, #1f2937)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: 11, fontWeight: 700, color: '#fff', flexShrink: 0,
                        }}>
                          {AgentInitials(a)}
                        </div>
                        <div>
                          <div style={{ fontWeight: 500, fontSize: 13 }}>{a.nombre ?? a.id}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{a.id}</div>
                        </div>
                      </div>
                    </td>
                    <td><MiniBar value={a.tasa_exito}          color="var(--state-success)" /></td>
                    <td><MiniBar value={a.tasa_promesa}        color="var(--state-warning)" /></td>
                    <td><MiniBar value={a.tasa_pago_inmediato} color="var(--state-info)"    /></td>
                    <td className="right" style={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
                      {a.total_llamadas ?? 0}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </DataCard>

      {/* Cards grid */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12 }}>
          Vista de tarjetas
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {sorted.map((a, idx) => {
            const rank = getRankStyle(idx);
            return (
              <div
                key={a.id}
                onClick={() => navigate(`/agentes/${a.id}`)}
                className="ds-card"
                style={{ cursor: 'pointer', padding: 18, transition: 'border-color 150ms' }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-focus)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-medium)'}
              >
                {/* Card header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                  <div style={{
                    width: 40, height: 40, borderRadius: 10,
                    background: 'linear-gradient(135deg, #374151, #1f2937)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 14, fontWeight: 700, color: '#fff', flexShrink: 0,
                  }}>
                    {AgentInitials(a)}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
                      {a.nombre ?? a.id}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {a.id} · {a.total_llamadas ?? 0} llamadas
                    </div>
                  </div>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                    background: rank.bg, color: rank.color,
                  }}>
                    {rank.label}
                  </span>
                </div>

                {/* Metrics */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      <span>Tasa de éxito</span>
                      <span style={{ fontWeight: 700, color: 'var(--state-success)' }}>{pct(a.tasa_exito)}</span>
                    </div>
                    <MiniBar value={a.tasa_exito} color="var(--state-success)" showLabel={false} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      <span>Promesas</span>
                      <span style={{ fontWeight: 700, color: 'var(--state-warning)' }}>{pct(a.tasa_promesa)}</span>
                    </div>
                    <MiniBar value={a.tasa_promesa} color="var(--state-warning)" showLabel={false} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
                      <span>Pago inmediato</span>
                      <span style={{ fontWeight: 700, color: 'var(--state-info)' }}>{pct(a.tasa_pago_inmediato)}</span>
                    </div>
                    <MiniBar value={a.tasa_pago_inmediato} color="var(--state-info)" showLabel={false} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
