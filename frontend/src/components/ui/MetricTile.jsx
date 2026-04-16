export default function MetricTile({ label, value, note }) {
  return (
    <article className="poll-metric-tile">
      <p className="poll-metric-label">{label}</p>
      <p className="poll-metric-value">{value}</p>
      {note && <p className="poll-metric-note">{note}</p>}
    </article>
  );
}
