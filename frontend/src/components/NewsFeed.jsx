import { useState } from 'react';
import SignalBadge from './SignalBadge';
import { timeAgo } from '../utils/timeAgo';

export default function NewsFeed({ markets = [], onSelectCity }) {
  const [activeTab, setActiveTab] = useState('triggers');

  // AI-parsed notable events
  const triggers = markets
    .filter((m) => m.notable_event)
    .map((m) => ({
      city: m.city,
      city_slug: m.city_slug,
      direction: m.direction,
      text: m.notable_event,
      last_updated: m.last_updated,
    }));

  // Raw headlines
  const headlineItems = markets
    .filter((m) => m.top_news_headline)
    .map((m) => ({
      city: m.city,
      city_slug: m.city_slug,
      direction: m.direction,
      text: m.top_news_headline,
      last_updated: m.last_updated,
    }));

  const rawItems = activeTab === 'triggers' ? triggers : headlineItems;

  // Deduplicate consecutive identical headlines
  const items = [];
  for (let i = 0; i < rawItems.length; i++) {
    const item = rawItems[i];
    let dupeCount = 0;
    while (i + 1 < rawItems.length && rawItems[i + 1].text === item.text) {
      dupeCount++;
      i++;
    }
    items.push({ ...item, dupeCount });
  }

  const emptyMsg = activeTab === 'triggers'
    ? 'No major triggers parsed yet.'
    : 'No news headlines ingested.';

  const tabs = [
    { key: 'triggers', label: 'ALL TRIGGERS' },
    { key: 'headlines', label: 'LATEST HEADLINES' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      {/* Header */}
      <div style={{ padding: '16px 16px 0' }}>
        <span className="text-header">MARKET INTELLIGENCE FEED</span>
      </div>

      {/* Tabs — underline style, no pills */}
      <div style={{
        display: 'flex',
        gap: '20px',
        padding: '12px 16px 0',
        borderBottom: '1px solid #E7E4DD',
      }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #E94E1B' : '2px solid transparent',
              color: activeTab === tab.key ? '#0B0B0F' : '#C9C4BA',
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontWeight: 600,
              paddingBottom: '8px',
              cursor: 'pointer',
              fontFamily: 'inherit',
              transition: 'color 150ms ease, border-color 150ms ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Scrollable feed */}
      <div className="feed-scroll" style={{ flex: 1, overflowY: 'auto', padding: '0 16px' }}>
        {items.length === 0 ? (
          <p style={{
            fontSize: '11px',
            color: '#6E6A61',
            textAlign: 'center',
            padding: '32px 0',
            fontStyle: 'italic',
          }}>
            {emptyMsg}
          </p>
        ) : (
          items.map((item, i) => (
            <div
              key={`${item.city_slug}-${i}`}
              onClick={() => onSelectCity?.(item.city_slug)}
              className="feed-item"
              style={{
                padding: '12px 0',
                borderBottom: '1px solid #E7E4DD',
                cursor: 'pointer',
                transition: 'background 100ms ease',
              }}
            >
              {/* Row 1: city tag + signal badge */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <span style={{
                  fontSize: '9px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: '#2B2A27',
                  background: '#F4F1EB',
                  padding: '2px 6px',
                  borderRadius: '2px',
                  fontWeight: 600,
                }}>
                  {item.city}
                </span>
                <SignalBadge direction={item.direction} />
              </div>
              {/* Row 2: headline */}
              <p className="line-clamp-2" style={{
                fontSize: '12px',
                color: '#2B2A27',
                margin: '4px 0',
                lineHeight: 1.5,
              }}>
                {item.text}
                {item.dupeCount > 0 && (
                  <span style={{ fontSize: '10px', color: '#C9C4BA', marginLeft: '6px' }}>
                    (+{item.dupeCount} similar)
                  </span>
                )}
              </p>
              {/* Row 3: timestamp */}
              <span style={{ fontSize: '10px', color: '#C9C4BA' }}>
                {item.last_updated ? timeAgo(item.last_updated) : ''}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
