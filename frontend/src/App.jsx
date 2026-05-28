import { useState, useEffect, useCallback } from 'react';
import SplashPage from './components/SplashPage';
import CityCard from './components/CityCard';
import NewsFeed from './components/NewsFeed';
import CityDetailModal from './components/CityDetailModal';

const API_BASE = 'http://localhost:8000/api';
const REGION_ORDER = ['Ohio', 'New York', 'Ontario', 'Alberta'];
const POLL_INTERVAL = 60_000;

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [dashReady, setDashReady] = useState(false);

  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastFetch, setLastFetch] = useState(null);

  const [activeRegion, setActiveRegion] = useState(REGION_ORDER[0]);
  const [activeCitySlug, setActiveCitySlug] = useState(null);

  const fetchMarkets = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/markets`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMarkets(Array.isArray(data) ? data : data.markets || []);
      setLastFetch(new Date().toISOString());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarkets();
    const interval = setInterval(fetchMarkets, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchMarkets]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/refresh`);
      setTimeout(async () => {
        await fetchMarkets();
        setRefreshing(false);
      }, 3000);
    } catch {
      setRefreshing(false);
      setError('Refresh failed. Please try again.');
    }
  };

  const handleSplashExit = () => {
    setShowSplash(false);
    requestAnimationFrame(() => setDashReady(true));
  };

  const grouped = REGION_ORDER.reduce((acc, region) => {
    acc[region] = markets.filter((m) => m.region === region);
    return acc;
  }, {});

  const activeCities = grouped[activeRegion] || [];

  // Dynamic grid columns: 3 cities → 3 cols, otherwise 2
  const gridCols = activeCities.length === 3 ? 3 : 2;

  const lastFetchFormatted = lastFetch
    ? new Date(lastFetch).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—';

  if (showSplash) {
    return <SplashPage onEnter={handleSplashExit} />;
  }

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: '#F4F1EB',
        opacity: dashReady ? 1 : 0,
        transition: 'opacity 300ms ease',
      }}
    >
      {/* ─── NAV BAR ─── */}
      <header
        style={{
          height: '48px',
          minHeight: '48px',
          background: '#0B0B0F',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: '14px', fontWeight: 700, color: '#F4F1EB', whiteSpace: 'nowrap' }}>
          Market Watch
        </span>

        <nav style={{ display: 'flex', gap: '24px', height: '100%', alignItems: 'stretch' }}>
          {REGION_ORDER.map((region) => {
            const count = (grouped[region] || []).length;
            const isActive = region === activeRegion;
            return (
              <button
                key={region}
                onClick={() => setActiveRegion(region)}
                style={{
                  background: 'none',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #E94E1B' : '2px solid transparent',
                  color: isActive ? '#F4F1EB' : '#6E6A61',
                  fontSize: '12px',
                  letterSpacing: '0.05em',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  fontWeight: isActive ? 600 : 400,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '0',
                  transition: 'color 150ms ease, border-color 150ms ease',
                  whiteSpace: 'nowrap',
                }}
              >
                {region}
                {count > 0 && (
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '9px',
                    background: isActive ? '#E94E1B' : '#2B2A27',
                    color: isActive ? '#F4F1EB' : '#6E6A61',
                    padding: '1px 5px',
                    borderRadius: '2px',
                    lineHeight: 1,
                    fontWeight: 600,
                    minWidth: '16px',
                    height: '14px',
                  }}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            background: '#E94E1B',
            color: '#F4F1EB',
            border: 'none',
            borderRadius: '3px',
            padding: '6px 16px',
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            fontWeight: 600,
            cursor: refreshing ? 'default' : 'pointer',
            opacity: refreshing ? 0.6 : 1,
            fontFamily: 'inherit',
            transition: 'opacity 150ms ease',
            whiteSpace: 'nowrap',
          }}
        >
          {refreshing ? 'REFRESHING…' : 'REFRESH'}
        </button>
      </header>

      {/* ─── MAIN CONTENT ─── */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>

        {/* LEFT: City Grid */}
        <main className="feed-scroll" style={{
          flex: 3,
          padding: '20px 24px 0',
          overflowY: 'auto',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* Error banner */}
          {error && !loading && (
            <div style={{
              marginBottom: '12px',
              background: '#FAFAF7',
              border: '1px solid #E7E4DD',
              borderRadius: '6px',
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              flexShrink: 0,
            }}>
              <span style={{ color: '#E94E1B', fontSize: '14px' }}>⚠</span>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: '12px', color: '#2B2A27', fontWeight: 600, margin: 0 }}>
                  Unable to load market data
                </p>
                <p style={{ fontSize: '10px', color: '#6E6A61', margin: '2px 0 0' }}>{error}</p>
              </div>
              <button
                onClick={fetchMarkets}
                style={{
                  fontSize: '10px', color: '#E94E1B', background: 'none', border: 'none',
                  cursor: 'pointer', fontWeight: 600, fontFamily: 'inherit',
                  textTransform: 'uppercase', letterSpacing: '0.06em',
                }}
              >
                Retry
              </button>
            </div>
          )}

          {/* Loading skeleton */}
          {loading ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="animate-pulse"
                  style={{
                    background: '#FAFAF7', border: '1px solid #E7E4DD',
                    borderRadius: '6px', padding: '20px',
                  }}
                >
                  <div style={{ height: '14px', background: '#E7E4DD', borderRadius: '3px', width: '55%', marginBottom: '14px' }} />
                  <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
                    {[1,2,3,4,5].map(d => (
                      <div key={d} style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#E7E4DD' }} />
                    ))}
                  </div>
                  <div style={{ height: '10px', background: '#E7E4DD', borderRadius: '3px', width: '100%', marginBottom: '8px' }} />
                  <div style={{ height: '10px', background: '#E7E4DD', borderRadius: '3px', width: '85%', marginBottom: '8px' }} />
                  <div style={{ height: '10px', background: '#E7E4DD', borderRadius: '3px', width: '45%' }} />
                </div>
              ))}
            </div>
          ) : activeCities.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
              <p style={{ fontSize: '12px', color: '#6E6A61' }}>
                Waiting for {activeRegion} market data…
              </p>
            </div>
          ) : (
            <>
              {/* Region header with full-width rule */}
              <div
                style={{
                  marginBottom: '16px',
                  paddingBottom: '8px',
                  borderBottom: '1px solid #E7E4DD',
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '6px',
                  flexShrink: 0,
                }}
              >
                <span className="text-header">{activeRegion.toUpperCase()}</span>
                <span style={{ fontSize: '10px', color: '#C9C4BA' }}>
                  {activeCities.length}
                </span>
              </div>

              {/* City grid — dynamic columns */}
              <div
                key={activeRegion}
                className="grid-enter city-grid"
                style={{
                  display: 'grid',
                  gridTemplateColumns: `repeat(${gridCols}, 1fr)`,
                  gap: '16px',
                  flexShrink: 0,
                }}
              >
                {activeCities.map((market) => (
                  <CityCard
                    key={market.city_slug}
                    {...market}
                    onSelect={setActiveCitySlug}
                  />
                ))}
              </div>

              {/* Spacer pushes monitoring bar to bottom */}
              <div style={{ flex: 1 }} />

              {/* Monitoring bar — pinned to bottom */}
              <div style={{
                marginTop: 'auto',
                padding: '16px 0',
                borderTop: '1px solid #E7E4DD',
                flexShrink: 0,
              }}>
                <span style={{ fontSize: '11px', color: '#C9C4BA' }}>
                  Monitoring {activeCities.length} market{activeCities.length !== 1 ? 's' : ''} in {activeRegion} — last updated {lastFetchFormatted}
                </span>
              </div>
            </>
          )}
        </main>

        {/* RIGHT: Intelligence Feed */}
        <aside
          style={{
            flex: '0 0 280px',
            maxWidth: '320px',
            borderLeft: '1px solid #E7E4DD',
            background: '#FAFAF7',
            display: 'flex',
            flexDirection: 'column',
            minHeight: 0,
          }}
        >
          <NewsFeed markets={markets} onSelectCity={setActiveCitySlug} />
        </aside>
      </div>

      {activeCitySlug && (
        <CityDetailModal
          citySlug={activeCitySlug}
          onClose={() => setActiveCitySlug(null)}
        />
      )}
    </div>
  );
}
