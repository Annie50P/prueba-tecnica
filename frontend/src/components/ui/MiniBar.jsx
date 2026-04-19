export default function MiniBar({ value, color = 'var(--accent-primary)', showLabel = true }) {
  const pct = Math.min(Math.max((value ?? 0) * 100, 0), 100);
  return (
    <div className="ds-minibar">
      <div className="ds-minibar-track">
        <div className="ds-minibar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      {showLabel && (
        <span className="ds-minibar-label">{pct.toFixed(1)}%</span>
      )}
    </div>
  );
}
