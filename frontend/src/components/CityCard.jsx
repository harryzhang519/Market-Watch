import SignalBadge from './SignalBadge';
import { timeAgo } from '../utils/timeAgo';

export default function CityCard({
  city,
  direction,
  confidence,
  explanation,
  key_driver,
  severity,
  last_updated,
  top_news_headline,
  city_slug,
  onSelect,
}) {
  const severityLevel = typeof severity === 'number' ? Math.max(0, Math.min(5, severity)) : 0;
  const confUpper = (confidence || 'low').toUpperCase();
  const confLabel = confUpper === 'MEDIUM' ? 'MED' : confUpper;
  const dirLabel = (direction || 'stable').toLowerCase();

  return (
    <div
      onClick={() => onSelect?.(city_slug)}
      className="city-card"
      style={{
        background: '#FAFAF7',
        border: '1px solid #E7E4DD',
        borderBottom: '2px solid #E7E4DD',
        borderRadius: '6px',
        padding: '20px',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'none',
        minWidth: 0,
      }}
    >
      {/* Top row: city name + badges */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: '16px', fontWeight: 700, color: '#0B0B0F', lineHeight: 1.3 }}>{city}</span>
        <div style={{ display: 'flex', gap: '6px', flexShrink: 0, marginLeft: '12px' }}>
          <SignalBadge direction={direction} />
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            background: 'transparent',
            border: '1px solid #D8D3C6',
            color: '#6E6A61',
            fontSize: '10px',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            borderRadius: '3px',
            padding: '3px 8px',
            lineHeight: 1,
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}>
            {confLabel}
          </span>
        </div>
      </div>

      {/* Severity row */}
      <div
        style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}
        title={`Severity ${severityLevel} of 5 — ${dirLabel} signal strength`}
      >
        <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#C9C4BA' }}>
          SEVERITY
        </span>
        <div style={{ display: 'flex', gap: '5px' }}>
          {[1, 2, 3, 4, 5].map((dot) => (
            <span
              key={dot}
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: dot <= severityLevel ? '#E94E1B' : '#E7E4DD',
                flexShrink: 0,
              }}
            />
          ))}
        </div>
      </div>

      {/* Explanation */}
      {explanation && (
        <p className="line-clamp-3" style={{
          margin: '14px 0 0',
          fontSize: '13px',
          lineHeight: 1.6,
          color: '#2B2A27',
          wordWrap: 'break-word',
          overflowWrap: 'break-word',
        }}>
          {explanation}
        </p>
      )}

      {/* Driver with editorial accent bar */}
      {key_driver && (
        <div style={{
          marginTop: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          overflow: 'hidden',
        }}>
          <span style={{
            display: 'inline-block',
            width: '2px',
            height: '12px',
            background: '#E94E1B',
            borderRadius: '1px',
            flexShrink: 0,
          }} />
          <p style={{
            margin: 0,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            minWidth: 0,
          }}>
            <span style={{ fontSize: '10px', color: '#C9C4BA' }}>{"Driver —"}</span>{' '}
            <span style={{ fontSize: '11px', fontStyle: 'italic', color: '#6E6A61' }}>{key_driver}</span>
          </p>
        </div>
      )}

      {/* News footer — vertical bar instead of LATEST label */}
      <div style={{
        marginTop: '16px',
        paddingTop: '12px',
        borderTop: '1px solid #E7E4DD',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
      }}>
        <span style={{
          display: 'inline-block',
          width: '2px',
          height: '14px',
          background: '#E7E4DD',
          borderRadius: '1px',
          flexShrink: 0,
        }} />
        <span className="line-clamp-1" style={{ flex: 1, fontSize: '11px', color: '#6E6A61', lineHeight: 1.4 }}>
          {top_news_headline || 'No recent headlines'}
        </span>
        <span style={{
          fontSize: '10px',
          color: '#C9C4BA',
          fontVariantNumeric: 'tabular-nums',
          flexShrink: 0,
          whiteSpace: 'nowrap',
        }}>
          {last_updated ? timeAgo(last_updated) : '—'}
        </span>
      </div>
    </div>
  );
}
