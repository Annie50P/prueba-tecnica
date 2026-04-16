export default function LinkButton({ className = '', ...props }) {
  return <button className={`poll-link-btn ${className}`.trim()} {...props} />;
}
