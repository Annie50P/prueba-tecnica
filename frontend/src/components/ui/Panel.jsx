export default function Panel({ title, subtitle, aside, className = '', children }) {
  return (
    <section className={`poll-panel ${className}`}>
      {(title || subtitle || aside) && (
        <header className="poll-panel-head">
          <div>
            {title && <h2 className="poll-panel-title">{title}</h2>}
            {subtitle && <p className="poll-panel-subtitle">{subtitle}</p>}
          </div>
          {aside && <div>{aside}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
