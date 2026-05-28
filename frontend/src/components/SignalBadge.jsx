export default function SignalBadge({ direction }) {
  const d = (direction || 'stable').toUpperCase();

  const styles = {
    HEATING: { background: '#E94E1B', color: '#FAFAF7', border: 'none' },
    COOLING: { background: '#2B2A27', color: '#FAFAF7', border: 'none' },
    STABLE:  { background: 'transparent', color: '#6E6A61', border: '1px solid #D8D3C6' },
  };

  const s = styles[d] || styles.STABLE;
  const label = d === 'HEATING' ? 'Heating' : d === 'COOLING' ? 'Cooling' : 'Stable';
  const pulse = d === 'HEATING' ? ' animate-ember-pulse' : '';

  return (
    <span
      className={pulse}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: '3px',
        padding: '3px 8px',
        fontSize: '10px',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        fontWeight: 600,
        lineHeight: 1,
        background: s.background,
        color: s.color,
        border: s.border || 'none',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}
