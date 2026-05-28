import { useState, useEffect, useCallback } from 'react';

export default function SplashPage({ onEnter }) {
  const [fading, setFading] = useState(false);

  const handleEnter = useCallback(() => {
    if (fading) return;
    setFading(true);
    setTimeout(onEnter, 400);
  }, [fading, onEnter]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Enter') handleEnter();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [handleEnter]);

  const now = new Date();
  const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
  const dateStr = `${days[now.getDay()]} ${String(now.getDate()).padStart(2, '0')} ${months[now.getMonth()]} ${now.getFullYear()}`;

  return (
    <div
      onClick={handleEnter}
      className="splash-page"
      style={{ opacity: fading ? 0 : 1, transition: 'opacity 400ms ease' }}
    >
      <div className="splash-center">
        <span className="splash-eyebrow">INDIGO STRIDE</span>
        <h1 className="splash-wordmark">Market Watch</h1>
        <p className="splash-descriptor">
          Real estate market intelligence — Ohio · New York · Ontario · Alberta
        </p>
        <button
          className="splash-enter"
          onClick={(e) => { e.stopPropagation(); handleEnter(); }}
        >
          ENTER
        </button>
      </div>
      <span className="splash-date">{dateStr}</span>
    </div>
  );
}
