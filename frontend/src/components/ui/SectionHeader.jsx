export default function SectionHeader({ title, description, right }) {
  return (
    <div className="ds-page-header" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 12 }}>
      <div>
        <h1 className="ds-page-title">{title}</h1>
        {description && <p className="ds-page-subtitle">{description}</p>}
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}
