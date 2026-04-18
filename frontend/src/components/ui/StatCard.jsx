export default function StatCard({ label, value, note, icon, variant = 'default' }) {
  const deltaColors = {
    success: 'ds-stat-delta-up',
    warning: 'ds-stat-delta-neutral',
    danger:  'ds-stat-delta-down',
    default: 'ds-stat-delta-neutral',
  };

  return (
    <div className="ds-stat-card">
      <div className="ds-stat-label">
        <span>{label}</span>
        {icon && <span style={{ color: 'var(--text-muted)', fontSize: 16 }}>{icon}</span>}
      </div>
      <div className="ds-stat-value">{value}</div>
      {note && (
        <div className={`ds-stat-delta ${deltaColors[variant]}`}>
          {note}
        </div>
      )}
    </div>
  );
}
