import { useState, useEffect } from 'react';
import ExecutiveReport from './ExecutiveReport';

const PRESETS = [
  { label: 'Rate Cut (-0.5%)', headline: 'Central bank announces aggressive 50 basis point interest rate cut to stimulate housing demand.' },
  { label: 'Downtown Rezoning', headline: 'City council passes sweeping high-density rezoning laws for multi-family residential zoning.' },
  { label: 'Tech Giant Expansion', headline: 'Amazon announces new 10,000-employee corporate office campus in the metropolitan core.' },
  { label: 'Mortgage Rate Spike (+1.0%)', headline: 'National mortgage rates jump over 1% in single week following inflation scares.' }
];

/* Light-mode signal badge for Step 3 */
function TraceSignalBadge({ direction }) {
  const d = (direction || 'stable').toUpperCase();
  const map = {
    HEATING: { background: '#E94E1B', color: '#FAFAF7', border: 'none' },
    COOLING: { background: '#2B2A27', color: '#FAFAF7', border: 'none' },
    STABLE:  { background: 'transparent', color: '#6E6A61', border: '1px solid #D8D3C6' },
  };
  const s = map[d] || map.STABLE;
  const label = d === 'HEATING' ? 'Heating' : d === 'COOLING' ? 'Cooling' : 'Stable';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', borderRadius: '3px',
      padding: '3px 8px', fontSize: '10px', textTransform: 'uppercase',
      letterSpacing: '0.08em', fontWeight: 600, lineHeight: 1,
      background: s.background, color: s.color, border: s.border || 'none',
    }}>
      {label}
    </span>
  );
}

export default function CityDetailModal({ citySlug, onClose }) {
  const [cityData, setCityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [simulating, setSimulating] = useState(false);
  const [customHeadline, setCustomHeadline] = useState('');
  const [isSimulated, setIsSimulated] = useState(false);
  const [originalData, setOriginalData] = useState(null);
  const [showReport, setShowReport] = useState(false);

  const fetchCityDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/markets/${citySlug}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCityData(data);
      setOriginalData(data);
      setIsSimulated(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCityDetail(); }, [citySlug]);

  const handleSimulate = async (headlineToUse) => {
    const headline = headlineToUse || customHeadline;
    if (!headline.trim()) return;
    setSimulating(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/markets/${citySlug}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headline }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || `Server returned ${res.status}`);
      setCityData(data);
      setIsSimulated(true);
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Cannot reach the backend server. Make sure it is running on port 8000.');
      } else {
        setError(err.message);
      }
    } finally {
      setSimulating(false);
    }
  };

  const handleReset = () => {
    setCityData(originalData);
    setIsSimulated(false);
    setCustomHeadline('');
    setError(null);
  };

  if (loading) {
    return (
      <div style={S.overlay}>
        <div style={{ ...S.modal, maxWidth: '360px', textAlign: 'center', padding: '48px 32px' }}>
          <div style={{ width: '32px', height: '32px', border: '3px solid #E7E4DD', borderTop: '3px solid #E94E1B', borderRadius: '50%', margin: '0 auto 16px' }} className="animate-spin" />
          <p style={{ fontSize: '12px', color: '#2B2A27', fontWeight: 600 }}>Loading detailed intelligence…</p>
        </div>
      </div>
    );
  }

  if (error && !cityData) {
    return (
      <div style={S.overlay}>
        <div style={{ ...S.modal, maxWidth: '400px', textAlign: 'center', padding: '32px' }}>
          <p style={{ fontSize: '13px', color: '#2B2A27', fontWeight: 600, marginBottom: '4px' }}>Failed to fetch detailed records</p>
          <p style={{ fontSize: '11px', color: '#6E6A61', marginBottom: '16px' }}>{error}</p>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
            <button onClick={fetchCityDetail} style={S.btnPrimary}>Retry</button>
            <button onClick={onClose} style={S.btnSecondary}>Close</button>
          </div>
        </div>
      </div>
    );
  }

  const {
    city, region, direction, confidence, explanation, key_driver,
    severity, median_price, price_change_pct, inventory,
    inventory_change_pct, days_on_market, rate, bank,
    last_updated, is_stale, news = []
  } = cityData;

  const severityLevel = typeof severity === 'number' ? Math.max(1, Math.min(5, severity)) : 1;

  const fmt = (val) => {
    if (val === null || val === undefined) return 'N/A';
    if (val < 2000) return `${val.toFixed(1)} (Index)`;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);
  };
  const fmtPct = (val) => {
    if (val === null || val === undefined) return 'N/A';
    return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
  };

  const rateIsDriver = key_driver && key_driver.toLowerCase().includes('rate');
  const pipelineLabel = cityData?.interpretation_source === 'local_fallback'
    ? 'LOCAL RULE ENGINE' : 'GEMINI FLASH PIPELINE';

  return (
    <>
      <div style={S.overlay}>
        <div style={{ ...S.modal, maxWidth: '860px' }}>

          {/* Simulation banner */}
          {isSimulated && (
            <div style={{
              background: 'rgba(233,78,27,0.06)', borderBottom: '1px solid rgba(233,78,27,0.15)',
              margin: '-24px -24px 0', padding: '8px 24px',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px',
              fontSize: '10px', fontWeight: 600, color: '#E94E1B', textTransform: 'uppercase', letterSpacing: '0.06em',
            }}>
              <span>Simulation Active</span>
              {cityData?.is_fallback && (
                <span style={{ fontSize: '9px', color: '#6E6A61', border: '1px solid #E7E4DD', borderRadius: '2px', padding: '1px 6px' }}>
                  Rule-based fallback
                </span>
              )}
              <button onClick={handleReset} style={{ background: 'none', border: 'none', color: '#2B2A27', fontSize: '10px', cursor: 'pointer', textDecoration: 'underline', fontFamily: 'inherit' }}>
                Reset to live
              </button>
            </div>
          )}

          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginTop: isSimulated ? '16px' : 0 }}>
            <div>
              <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>Market Intelligence</span>
              <h2 style={{ fontSize: '20px', fontWeight: 700, color: '#0B0B0F', margin: '4px 0 0' }}>
                {city} <span style={{ fontSize: '13px', fontWeight: 400, color: '#6E6A61' }}>({region})</span>
              </h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                <span style={{ fontSize: '10px', color: '#6E6A61' }}>
                  Updated: {last_updated ? new Date(last_updated).toLocaleString() : 'N/A'}
                </span>
                {is_stale && <span style={{ fontSize: '9px', color: '#6E6A61', border: '1px solid #E7E4DD', borderRadius: '2px', padding: '1px 5px' }}>Cached</span>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={() => setShowReport(true)} style={S.btnPrimary}>Executive Report</button>
              <button onClick={onClose} style={{ ...S.btnSecondary, padding: '6px 10px' }}>✕</button>
            </div>
          </div>

          {/* Metrics grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginTop: '20px' }}>
            {[
              { label: 'Median Price', value: fmt(median_price), sub: `${fmtPct(price_change_pct)} MoM`, pctVal: price_change_pct },
              { label: 'Active Inventory', value: inventory !== null ? String(inventory) : 'N/A', sub: `${fmtPct(inventory_change_pct)} Trend`, pctVal: inventory_change_pct },
              { label: 'Days on Market', value: days_on_market !== null ? `${days_on_market} Days` : 'N/A', sub: 'Market Velocity', pctVal: null },
              { label: 'Interest Rate', value: rate !== null ? `${rate}%` : 'N/A', sub: bank || 'Central Bank', pctVal: null },
            ].map((m) => {
              const subColor = m.pctVal !== null && m.pctVal !== undefined
                ? (m.pctVal < 0 ? '#E94E1B' : '#6E6A61')
                : '#6E6A61';
              return (
                <div key={m.label} style={{ background: '#FAFAF7', border: '1px solid #E7E4DD', borderRadius: '6px', padding: '14px' }}>
                  <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>{m.label}</span>
                  <div style={{ marginTop: '8px' }}>
                    <span style={{ fontSize: '18px', fontWeight: 700, color: '#0B0B0F' }}>{m.value}</span>
                  </div>
                  <span style={{ fontSize: '10px', color: subColor, fontWeight: 600, marginTop: '2px', display: 'block' }}>{m.sub}</span>
                </div>
              );
            })}
          </div>

          {/* ═══ REASONING TRACE PANEL (light, vertical) ═══ */}
          <div style={{
            background: '#FAFAF7', borderRadius: '6px', border: '1px solid #E7E4DD',
            padding: '24px', marginTop: '20px', width: '100%', maxWidth: '100%', overflow: 'visible',
          }}>
            {/* Trace header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              borderBottom: '1px solid #E7E4DD', paddingBottom: '16px', marginBottom: '20px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{
                  fontSize: '11px', color: '#E94E1B', border: '1px solid #E94E1B',
                  borderRadius: '2px', padding: '2px 5px', lineHeight: 1, fontWeight: 700,
                }}>A</span>
                <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.12em', color: '#0B0B0F', fontWeight: 600 }}>
                  AI Interpretation Trace
                </span>
              </div>
              <span style={{
                fontSize: '10px', color: '#6E6A61', border: '1px solid #E7E4DD',
                borderRadius: '2px', padding: '2px 8px',
              }}>
                {pipelineLabel}
              </span>
            </div>

            {/* Vertical steps with connector line */}
            <div style={{ position: 'relative', paddingLeft: '40px' }}>
              {/* Vertical dotted connector */}
              <div style={{
                position: 'absolute', left: '11px', top: '12px', bottom: '12px',
                borderLeft: '1px dashed #E7E4DD',
              }} />

              {/* STEP 1: Raw Market Data */}
              <div style={{ position: 'relative', marginBottom: '12px' }}>
                <div style={{
                  position: 'absolute', left: '-40px', top: '0',
                  width: '24px', height: '24px', borderRadius: '50%',
                  background: '#E7E4DD', color: '#6E6A61',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '10px', fontWeight: 700, zIndex: 1,
                }}>1</div>
                <div style={{ background: '#FFFFFF', border: '1px solid #E7E4DD', borderRadius: '4px', padding: '16px' }}>
                  <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>RAW MARKET DATA</span>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 16px', marginTop: '12px' }}>
                    {[
                      { k: 'Price', v: `${fmt(median_price)} (${fmtPct(price_change_pct)})`, isRate: false },
                      { k: 'Supply', v: inventory !== null ? `${inventory} Active` : 'N/A', isRate: false },
                      { k: 'DOM', v: days_on_market !== null ? `${days_on_market} Days` : 'N/A', isRate: false },
                      { k: 'Rate', v: rate !== null ? `${rate}%` : 'N/A', isRate: true },
                    ].map((row) => (
                      <div key={row.k} style={{
                        display: 'flex', justifyContent: 'space-between', padding: '3px 6px',
                        borderRadius: '2px',
                        background: row.isRate && rateIsDriver ? 'rgba(233, 78, 27, 0.08)' : 'transparent',
                      }}>
                        <span style={{ fontSize: '11px', color: '#6E6A61' }}>{row.k}</span>
                        <span style={{ fontSize: '11px', fontWeight: 600, color: '#0B0B0F' }}>{row.v}</span>
                      </div>
                    ))}
                  </div>
                  {news[0]?.headline && (
                    <p style={{ fontSize: '10px', color: '#6E6A61', fontStyle: 'italic', marginTop: '10px' }}>
                      Trigger: {news[0].headline}
                    </p>
                  )}
                </div>
              </div>

              {/* STEP 2: AI Analysis */}
              <div style={{ position: 'relative', marginBottom: '12px' }}>
                <div style={{
                  position: 'absolute', left: '-40px', top: '0',
                  width: '24px', height: '24px', borderRadius: '50%',
                  background: '#E94E1B', color: '#FAFAF7',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '10px', fontWeight: 700, zIndex: 1,
                }}>2</div>
                <div style={{ background: '#FFFFFF', border: '1px solid #E7E4DD', borderRadius: '4px', padding: '16px' }}>
                  <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>AI ANALYSIS</span>
                  {key_driver && (
                    <div style={{ marginTop: '12px' }}>
                      <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61', display: 'block', marginBottom: '4px' }}>PRIMARY DRIVER</span>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: '#0B0B0F', marginBottom: '12px', display: 'block' }}>{key_driver}</span>
                    </div>
                  )}
                  <p className="line-clamp-4" style={{
                    fontSize: '12px', lineHeight: 1.7, color: '#2B2A27',
                    margin: key_driver ? '0' : '12px 0 0',
                  }}>
                    {explanation || 'Awaiting analysis…'}
                  </p>
                </div>
              </div>

              {/* STEP 3: Output Signal */}
              <div style={{ position: 'relative' }}>
                <div style={{
                  position: 'absolute', left: '-40px', top: '0',
                  width: '24px', height: '24px', borderRadius: '50%',
                  background: '#E7E4DD', color: '#6E6A61',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '10px', fontWeight: 700, zIndex: 1,
                }}>3</div>
                <div style={{ background: '#FFFFFF', border: '1px solid #E7E4DD', borderRadius: '4px', padding: '16px' }}>
                  <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>OUTPUT SIGNAL</span>
                  <div style={{ marginTop: '12px' }}>
                    <TraceSignalBadge direction={direction} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginTop: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>CONFIDENCE</span>
                      <span style={{ fontSize: '11px', color: '#0B0B0F', fontWeight: 600, textTransform: 'uppercase' }}>{confidence || 'low'}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61' }}>SEVERITY</span>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {[1, 2, 3, 4, 5].map((dot) => (
                          <span key={dot} style={{
                            width: '7px', height: '7px', borderRadius: '50%',
                            background: dot <= severityLevel ? '#E94E1B' : '#E7E4DD',
                          }} />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ═══ SIMULATION SANDBOX ═══ */}
          <div style={{ marginTop: '20px', border: '1px dashed #E7E4DD', borderRadius: '6px', padding: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid #E7E4DD', paddingBottom: '10px', marginBottom: '14px' }}>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61', fontWeight: 600 }}>What-If Simulation Sandbox</span>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#6E6A61', display: 'block', marginBottom: '8px' }}>Quick Presets</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => { setCustomHeadline(p.headline); handleSimulate(p.headline); }}
                    disabled={simulating}
                    style={{
                      background: '#FAFAF7', border: '1px solid #E7E4DD', borderRadius: '3px',
                      fontSize: '10px', fontWeight: 600, color: '#2B2A27', padding: '5px 10px',
                      cursor: simulating ? 'default' : 'pointer', opacity: simulating ? 0.5 : 1,
                      fontFamily: 'inherit', transition: 'border-color 150ms ease',
                    }}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="text"
                value={customHeadline}
                onChange={(e) => setCustomHeadline(e.target.value)}
                placeholder="Write custom market news headline…"
                disabled={simulating}
                style={{
                  flex: 1, background: '#FAFAF7', border: '1px solid #E7E4DD', borderRadius: '3px',
                  padding: '8px 12px', fontSize: '11px', fontFamily: 'inherit',
                  outline: 'none', color: '#2B2A27',
                }}
              />
              <button
                onClick={() => handleSimulate()}
                disabled={simulating || !customHeadline.trim()}
                style={{
                  ...S.btnPrimary, opacity: (simulating || !customHeadline.trim()) ? 0.5 : 1,
                  cursor: (simulating || !customHeadline.trim()) ? 'default' : 'pointer',
                }}
              >
                {simulating ? 'Simulating…' : 'Analyze'}
              </button>
              {isSimulated && (
                <button onClick={handleReset} disabled={simulating} style={S.btnSecondary}>Reset</button>
              )}
            </div>

            {error && (
              <div style={{ marginTop: '10px', background: '#FAFAF7', border: '1px solid #E7E4DD', borderRadius: '3px', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#E94E1B', fontSize: '12px' }}>⚠</span>
                <p style={{ fontSize: '11px', color: '#2B2A27', flex: 1, margin: 0 }}>{error}</p>
                <button onClick={() => handleSimulate()} style={{ fontSize: '10px', color: '#E94E1B', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit', textDecoration: 'underline' }}>Retry</button>
              </div>
            )}
          </div>

          {/* ═══ NEWS LIST ═══ */}
          <div style={{ marginTop: '20px' }}>
            <div style={{ borderBottom: '1px solid #E7E4DD', paddingBottom: '6px', marginBottom: '12px' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#6E6A61', fontWeight: 600 }}>Raw News Triggers Considered</span>
            </div>
            {news.length === 0 ? (
              <p style={{ fontSize: '11px', color: '#6E6A61', fontStyle: 'italic', padding: '8px 0' }}>No recent news reports fetched for this market.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                {news.map((item, idx) => (
                  <div key={item.id || idx} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 0', borderBottom: idx < news.length - 1 ? '1px solid #E7E4DD' : 'none',
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#E94E1B', fontWeight: 600 }}>
                        {item.source_name || 'Trigger'}
                      </span>
                      <p style={{ fontSize: '12px', color: '#0B0B0F', fontWeight: 600, margin: '2px 0 0', lineHeight: 1.4 }}>{item.headline}</p>
                    </div>
                    {item.url && item.url !== '#' && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontSize: '9px', color: '#6E6A61', textDecoration: 'underline', textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0, marginLeft: '12px' }}
                      >
                        Read
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {showReport && (
        <ExecutiveReport
          cityData={cityData}
          onClose={() => setShowReport(false)}
        />
      )}
    </>
  );
}

const S = {
  overlay: {
    position: 'fixed', inset: 0, zIndex: 50,
    background: 'rgba(11, 11, 15, 0.7)',
    backdropFilter: 'blur(4px)',
    display: 'flex', justifyContent: 'center',
    padding: '24px', overflowY: 'auto',
  },
  modal: {
    background: '#FFFFFF',
    borderRadius: '6px',
    border: '1px solid #E7E4DD',
    padding: '24px',
    width: '100%',
    margin: 'auto',
    position: 'relative',
  },
  btnPrimary: {
    background: '#0B0B0F', color: '#F4F1EB', border: 'none', borderRadius: '3px',
    padding: '6px 14px', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase',
    letterSpacing: '0.06em', cursor: 'pointer', fontFamily: 'inherit',
    transition: 'opacity 150ms ease',
  },
  btnSecondary: {
    background: '#FAFAF7', color: '#2B2A27', border: '1px solid #E7E4DD', borderRadius: '3px',
    padding: '6px 14px', fontSize: '11px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
    transition: 'border-color 150ms ease',
  },
};
