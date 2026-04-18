import DataCard from './DataCard';

export default function Panel({ title, subtitle, aside, className = '', children }) {
  return (
    <DataCard title={title} subtitle={subtitle} aside={aside} className={className}>
      {children}
    </DataCard>
  );
}
