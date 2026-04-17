import { useState, useRef, useEffect } from 'react';
import { queryMcp } from '../api/client';
import LinkButton from '../components/ui/LinkButton';

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
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
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
    <div className="poll-chat-shell">
      <header className="poll-chat-head">
        <h1>Chat IA</h1>
        <p>Conversacion compacta para consultas de cobranza.</p>
      </header>

      <div className="poll-chat-body space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-10">
            <p className="text-sm text-slate-600">Pregunta en lenguaje natural sobre clientes, pagos y agentes.</p>
            <div className="poll-chat-suggestions justify-center">
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
                <div className="mt-2 pt-2 border-t border-slate-100 flex flex-wrap gap-3 text-[11px] text-slate-400">
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
            <p className="m-0 text-slate-500">Procesando...</p>
          </div>
        )}

        <div ref={endRef} />
      </div>

      <form onSubmit={handleSend} className="poll-chat-foot">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Escribe tu consulta..."
          disabled={loading}
          className="text-sm"
        />
        <LinkButton type="submit" disabled={loading || !input.trim()}>
          Enviar
        </LinkButton>
      </form>
    </div>
  );
}
