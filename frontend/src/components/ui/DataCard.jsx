export default function DataCard({ title, subtitle, aside, children, flush = false, className = '' }) {
  return (
    <div className={`ds-card ${className}`}>
      {(title || aside) && (
        <div className="ds-card-header">
          <div>
            {title && <div className="ds-card-title">{title}</div>}
            {subtitle && <div className="ds-card-subtitle">{subtitle}</div>}
          </div>
          {aside && <div>{aside}</div>}
        </div>
      )}
      <div className={flush ? 'ds-card-body-flush' : 'ds-card-body'}>
        {children}
      </div>
    </div>
  );
}
