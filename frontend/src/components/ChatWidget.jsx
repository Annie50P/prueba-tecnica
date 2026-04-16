import { useState, useRef, useEffect } from 'react';
import { queryMcp } from '../api/client';
import LinkButton from './ui/LinkButton';

const SUGGESTIONS = [
  'Cual es el cliente con mayor deuda?',
  'Que agente tiene mejor tasa de promesas?',
  'Cuantas promesas estan incumplidas?',
  'Cual es el mejor horario para llamar?',
  'Dame un resumen de la cartera',
  'Que clientes tienen pagos pendientes altos?',
];

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

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
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: `Error: ${err.message ?? 'No se pudo conectar'}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-widget">
      {isOpen && (
        <div className="chat-widget-panel">
          <header className="chat-widget-head">
            <button
              className="chat-widget-close"
              onClick={() => setIsOpen(false)}
              aria-label="Cerrar chat"
            >
              <CloseIcon />
            </button>
            <h2 className="chat-widget-title">Chat IA</h2>
            <p className="chat-widget-subtitle">Consultas de cobranza en lenguaje natural.</p>
          </header>

          <div className="chat-widget-body">
            {messages.length === 0 && (
              <div className="chat-widget-empty">
                <p>Prueba con alguna de estas preguntas:</p>
                <div className="poll-chat-suggestions">
                  {SUGGESTIONS.map((q, i) => (
                    <LinkButton key={i} onClick={() => setInput(q)}>{q}</LinkButton>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i}>
                <article className={`poll-chat-message ${m.role === 'user' ? 'poll-chat-message-user' : 'poll-chat-message-ai'}`}>
                  <p className="whitespace-pre-wrap leading-relaxed m-0">{m.text}</p>
                  {m.role === 'assistant' && !m.error && (
                    <div className="chat-widget-meta">
                      {m.provider && <span>Proveedor: {m.provider}</span>}
                      {m.tokens != null && <span>Tokens: {m.tokens}</span>}
                      {m.queries?.length > 0 && <span>Tools: {m.queries.join(', ')}</span>}
                    </div>
                  )}
                </article>
              </div>
            ))}

            {loading && (
              <div className="poll-chat-message poll-chat-message-ai">
                <p className="m-0" style={{ color: 'var(--poll-muted)' }}>Procesando…</p>
              </div>
            )}

            <div ref={endRef} />
          </div>

          <form onSubmit={handleSend} className="chat-widget-foot">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Escribe tu consulta…"
              disabled={loading}
              autoFocus
            />
            <LinkButton type="submit" disabled={loading || !input.trim()}>
              Enviar
            </LinkButton>
          </form>
        </div>
      )}

      <button
        className="chat-widget-fab"
        onClick={() => setIsOpen(o => !o)}
        aria-label={isOpen ? 'Cerrar chat' : 'Abrir chat'}
      >
        {isOpen ? <CloseIcon /> : <ChatIcon />}
      </button>
    </div>
  );
}
