/** Animated SVG scenes for the features page — match Signal Gate dark/wire style. */

type VisualProps = { className?: string };

export function VisualLanguage({ className }: VisualProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 360 220"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="lang-glow" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#3ecf9a" stopOpacity="0.35" />
          <stop offset="1" stopColor="#3ecf9a" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect x="28" y="36" width="304" height="148" rx="16" stroke="#4a5568" strokeOpacity="0.55" fill="#0b0f16" />
      <circle cx="52" cy="58" r="4" fill="#3ecf9a" className="fv-blink" />
      <text x="66" y="62" fill="#8b97ab" fontFamily="JetBrains Mono, monospace" fontSize="11">
        desk · paper
      </text>
      <rect x="44" y="84" width="188" height="36" rx="10" fill="#121821" stroke="#3ecf9a" strokeOpacity="0.35" />
      <text x="58" y="107" fill="#e8ecf3" fontFamily="Space Grotesk, sans-serif" fontSize="13">
        Buy 0.5 ETH
      </text>
      <path
        className="fv-draw"
        d="M44 148 H200"
        stroke="url(#lang-glow)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <g className="fv-float">
        <rect x="236" y="88" width="72" height="72" rx="14" fill="#121821" stroke="#8b97ab" strokeOpacity="0.35" />
        <path
          d="M260 112h24M272 100v24M252 136h40"
          stroke="#3ecf9a"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <text x="250" y="152" fill="#5c687c" fontFamily="JetBrains Mono, monospace" fontSize="9">
          ORDER
        </text>
      </g>
    </svg>
  );
}

export function VisualGate({ className }: VisualProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 360 220"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="48" y="40" width="264" height="140" rx="16" fill="#0b0f16" stroke="#4a5568" strokeOpacity="0.55" />
      <text x="68" y="72" fill="#e6b35a" fontFamily="JetBrains Mono, monospace" fontSize="10" letterSpacing="2">
        PENDING TRADE
      </text>
      <text x="68" y="102" fill="#e8ecf3" fontFamily="Space Grotesk, sans-serif" fontSize="18" fontWeight="600">
        SELL 12 SOL
      </text>
      <text x="68" y="124" fill="#8b97ab" fontFamily="JetBrains Mono, monospace" fontSize="11">
        awaits your gate
      </text>
      <g className="fv-pulse-btn">
        <rect x="68" y="142" width="96" height="28" rx="8" fill="#3ecf9a" />
        <text x="88" y="160" fill="#04140f" fontFamily="Space Grotesk, sans-serif" fontSize="12" fontWeight="700">
          Approve
        </text>
      </g>
      <rect x="176" y="142" width="96" height="28" rx="8" fill="#121821" stroke="#4a5568" />
      <text x="202" y="160" fill="#e8ecf3" fontFamily="Space Grotesk, sans-serif" fontSize="12" fontWeight="600">
        Reject
      </text>
      {/* diamond gate mark */}
      <g transform="translate(300 70)">
        <g className="fv-spin-slow">
          <path d="M0 -18 L14 0 L0 18 L-14 0 Z" stroke="#3ecf9a" strokeOpacity="0.7" fill="none" />
          <path d="M0 -10 L8 0 L0 10 L-8 0 Z" fill="#3ecf9a" fillOpacity="0.25" />
        </g>
      </g>
    </svg>
  );
}

export function VisualMarket({ className }: VisualProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 360 220"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="24" y="28" width="312" height="164" rx="16" fill="#0b0f16" stroke="#4a5568" strokeOpacity="0.55" />
      <text x="44" y="56" fill="#8b97ab" fontFamily="JetBrains Mono, monospace" fontSize="11">
        ETH / USD
      </text>
      <text x="44" y="82" fill="#e8ecf3" fontFamily="Unbounded, sans-serif" fontSize="22" fontWeight="700">
        3,412.80
      </text>
      <text x="180" y="80" fill="#3ecf9a" fontFamily="JetBrains Mono, monospace" fontSize="12">
        +0.94%
      </text>

      {/* candles */}
      <g className="fv-candles" transform="translate(44 100)">
        {[
          [0, 40, 18, true],
          [28, 28, 32, false],
          [56, 34, 24, true],
          [84, 16, 42, true],
          [112, 22, 36, false],
          [140, 10, 48, true],
          [168, 18, 38, true],
          [196, 26, 30, false],
          [224, 8, 50, true],
          [252, 14, 40, true],
        ].map(([x, y, h, up], i) => (
          <g key={i} style={{ animationDelay: `${i * 0.08}s` }}>
            <line
              x1={Number(x) + 6}
              y1={Number(y) - 6}
              x2={Number(x) + 6}
              y2={Number(y) + Number(h) + 6}
              stroke={up ? "#3ecf9a" : "#ef6b6b"}
              strokeOpacity="0.45"
              strokeWidth="1.5"
            />
            <rect
              x={Number(x)}
              y={Number(y)}
              width="12"
              height={Number(h)}
              rx="2"
              fill={up ? "#3ecf9a" : "#ef6b6b"}
              fillOpacity="0.85"
            />
          </g>
        ))}
      </g>

      <path
        className="fv-draw"
        d="M44 188 C90 170, 140 200, 180 160 S260 120, 296 132"
        stroke="#3ecf9a"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
        opacity="0.7"
      />
    </svg>
  );
}

export function VisualResearch({ className }: VisualProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 360 220"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="28" y="32" width="304" height="156" rx="16" fill="#0b0f16" stroke="#4a5568" strokeOpacity="0.55" />

      {/* radar */}
      <g transform="translate(100 110)">
        <circle r="54" stroke="#4a5568" strokeOpacity="0.4" />
        <circle r="36" stroke="#4a5568" strokeOpacity="0.35" />
        <circle r="18" stroke="#3ecf9a" strokeOpacity="0.45" />
        <circle r="4" fill="#3ecf9a" className="fv-blink" />
        <path
          className="fv-radar"
          d="M0 0 L48 -18"
          stroke="#3ecf9a"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <circle cx="34" cy="-28" r="3" fill="#e6b35a" className="fv-blink" />
        <circle cx="-30" cy="22" r="3" fill="#8b97ab" />
      </g>

      <g transform="translate(190 58)">
        <rect width="120" height="22" rx="6" fill="#121821" stroke="#4a5568" strokeOpacity="0.5" />
        <text x="10" y="15" fill="#8b97ab" fontFamily="JetBrains Mono, monospace" fontSize="9">
          search · BTC ETF
        </text>
        <rect y="34" width="120" height="14" rx="4" fill="#121821" className="fv-bar" />
        <rect y="56" width="96" height="14" rx="4" fill="#121821" className="fv-bar" style={{ animationDelay: "0.2s" }} />
        <rect y="78" width="108" height="14" rx="4" fill="#121821" className="fv-bar" style={{ animationDelay: "0.4s" }} />
        <rect y="100" width="72" height="14" rx="4" fill="#3ecf9a" fillOpacity="0.2" className="fv-bar" style={{ animationDelay: "0.6s" }} />
        <text x="10" y="128" fill="#3ecf9a" fontFamily="JetBrains Mono, monospace" fontSize="9">
          sources only
        </text>
      </g>
    </svg>
  );
}

export function VisualCharts({ className }: VisualProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 360 220"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="24" y="28" width="312" height="164" rx="16" fill="#0b0f16" stroke="#4a5568" strokeOpacity="0.55" />
      <text x="40" y="54" fill="#8b97ab" fontFamily="JetBrains Mono, monospace" fontSize="10" letterSpacing="1">
        LIVE CHART
      </text>
      <text x="40" y="78" fill="#e8ecf3" fontFamily="Unbounded, sans-serif" fontSize="18" fontWeight="600">
        BTC / USD
      </text>

      {/* timeframe pills */}
      {[
        { x: 160, label: "1m", on: false },
        { x: 196, label: "5m", on: false },
        { x: 232, label: "15m", on: true },
        { x: 274, label: "1h", on: false },
      ].map((t) => (
        <g key={t.label}>
          <rect
            x={t.x}
            y="44"
            width="30"
            height="18"
            rx="4"
            fill={t.on ? "#3ecf9a" : "#121821"}
            stroke={t.on ? "#3ecf9a" : "#4a5568"}
            strokeOpacity={t.on ? 1 : 0.5}
          />
          <text
            x={t.x + 7}
            y="57"
            fill={t.on ? "#04140f" : "#8b97ab"}
            fontFamily="JetBrains Mono, monospace"
            fontSize="9"
            fontWeight={t.on ? 700 : 400}
          >
            {t.label}
          </text>
        </g>
      ))}

      <text x="40" y="100" fill="#3ecf9a" fontFamily="JetBrains Mono, monospace" fontSize="11">
        See it live →
      </text>

      <g className="fv-candles" transform="translate(40 112)">
        {[
          [0, 36, 22, true],
          [26, 24, 34, false],
          [52, 30, 26, true],
          [78, 14, 44, true],
          [104, 20, 36, false],
          [130, 8, 48, true],
          [156, 16, 40, true],
          [182, 22, 32, false],
          [208, 6, 50, true],
          [234, 12, 42, true],
          [260, 18, 36, false],
        ].map(([x, y, h, up], i) => (
          <g key={i} style={{ animationDelay: `${i * 0.07}s` }}>
            <line
              x1={Number(x) + 5}
              y1={Number(y) - 5}
              x2={Number(x) + 5}
              y2={Number(y) + Number(h) + 5}
              stroke={up ? "#3ecf9a" : "#ef6b6b"}
              strokeOpacity="0.45"
              strokeWidth="1.5"
            />
            <rect
              x={Number(x)}
              y={Number(y)}
              width="10"
              height={Number(h)}
              rx="2"
              fill={up ? "#3ecf9a" : "#ef6b6b"}
              fillOpacity="0.9"
            />
          </g>
        ))}
      </g>
    </svg>
  );
}
