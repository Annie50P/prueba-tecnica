import { useState, useRef, useEffect } from 'react';
import { queryMcp } from '../api/client';

const SUGGESTIONS = [
  'Cual es el cliente con mayor deuda?',
  'Que agente tiene mejor tasa de promesas?',
  'Cuantas promesas estan incumplidas?',
  'Cual es el mejor horario para llamar?',
  'Dame un resumen de la cartera',
  'Que clientes tienen pagos pendientes altos?',
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    setLoading(true);

    try {
      const res = await queryMcp(q);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: res.respuesta || res.message || 'Sin respuesta',
          provider: res.proveedor,
          tokens: res.tokens_usados,
          queries: res.queries_ejecutadas,
          error: res.status === 'error' ? res.error : null,
        },
      ]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const serverMsg = detail?.message || detail?.error || err.message;
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: `Error: ${serverMsg ?? 'No se pudo conectar'}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      maxWidth: 680,
      margin: '0 auto',
      height: 'calc(100vh - 56px - 48px)',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-medium)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border-soft)',
        background: 'var(--bg-elevated)',
        flexShrink: 0,
      }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>Chat IA</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
          Consultas de cobranza en lenguaje natural
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}>
        {messages.length === 0 && (
          <div style={{ paddingTop: 24 }}>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12, textAlign: 'center' }}>
              Pregunta en lenguaje natural sobre clientes, pagos y agentes.
            </div>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((q, i) => (
                <button key={i} className="chat-suggestion-btn" onClick={() => setInput(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`chat-msg ${m.role === 'user' ? 'chat-msg-user' : 'chat-msg-ai'}`}
          >
            <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{m.text}</p>
            {m.role === 'assistant' && !m.error && (m.provider || m.tokens || m.queries?.length > 0) && (
              <div className="chat-meta">
                {m.provider && <span>Proveedor: {m.provider}</span>}
                {m.tokens != null && <span>Tokens: {m.tokens}</span>}
                {m.queries?.length > 0 && <span>Tools: {m.queries.join(', ')}</span>}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-msg chat-msg-ai">
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Procesando…</span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-soft)',
          background: 'var(--bg-elevated)',
          display: 'flex',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Escribe tu consulta…"
          disabled={loading}
          className="chat-widget-input"
          style={{ flex: 1 }}
          autoFocus
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="chat-widget-send"
        >
          Enviar
        </button>
      </form>
    </div>
  );
}
