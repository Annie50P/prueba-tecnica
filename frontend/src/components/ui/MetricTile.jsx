import StatCard from './StatCard';

export default function MetricTile({ label, value, note }) {
  return <StatCard label={label} value={value} note={note} />;
}
