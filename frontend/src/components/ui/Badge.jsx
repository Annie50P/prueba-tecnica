const STATUS_MAP = {
  'Liquidado':      'ds-badge-success',
  'Buen pagador':   'ds-badge-info',
  'En proceso':     'ds-badge-warning',
  'Pendiente alto': 'ds-badge-orange',
  'Sin gestión':    'ds-badge-purple',
  'Alto riesgo':    'ds-badge-danger',
  'cooperativo':    'ds-badge-success',
  'neutral':        'ds-badge-neutral',
  'frustrado':      'ds-badge-warning',
  'hostil':         'ds-badge-danger',
  'positivo':       'ds-badge-success',
  'negativo':       'ds-badge-danger',
  'muy_negativo':   'ds-badge-danger',
  'Cumplida':       'ds-badge-success',
  'Pendiente':      'ds-badge-warning',
  'alto':           'ds-badge-danger',
  'medio':          'ds-badge-warning',
  'bajo':           'ds-badge-success',
};

export default function Badge({ label, variant }) {
  const cls = variant
    ? `ds-badge ds-badge-${variant}`
    : `ds-badge ${STATUS_MAP[label] ?? 'ds-badge-neutral'}`;

  return <span className={cls}>{label}</span>;
}

export function getStatusBadgeVariant(label) {
  const map = {
    'Liquidado': 'success', 'Buen pagador': 'info',
    'En proceso': 'warning', 'Pendiente alto': 'orange',
    'Sin gestión': 'purple', 'Alto riesgo': 'danger',
  };
  return map[label] ?? 'neutral';
}
