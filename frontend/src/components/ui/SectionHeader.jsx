export default function SectionHeader({ title, description, right }) {
  return (
    <div className="poll-section-head">
      <div>
        <h1 className="poll-section-title">{title}</h1>
        {description && <p className="poll-section-subtitle">{description}</p>}
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}
