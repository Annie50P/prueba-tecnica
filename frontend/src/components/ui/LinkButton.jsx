export default function LinkButton({ className = '', ...props }) {
  return <button className={`ds-btn ds-btn-ghost ${className}`.trim()} style={{ fontSize: 12, padding: '4px 10px' }} {...props} />;
}
