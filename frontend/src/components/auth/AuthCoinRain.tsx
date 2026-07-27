/**
 * Large 3D crypto coins slowly falling behind login / signup.
 * Assets from Figma community file "3D Crypto coins" (non-green only).
 */

import type { CSSProperties } from "react";

type CoinKind = "btc" | "eth" | "ltc" | "doge" | "xmr" | "zec";

type Drop = {
  id: number;
  left: string;
  size: number;
  delay: number;
  fall: number;
  tumble: number;
  sway: number;
  coin: CoinKind;
  /** Hide on narrow screens so the form stays readable. */
  mobileHide?: boolean;
};

const DROPS: Drop[] = [
  // left field
  { id: 1, left: "3%", size: 148, delay: 0, fall: 32, tumble: 16, sway: 26, coin: "btc" },
  { id: 2, left: "13%", size: 110, delay: 3.5, fall: 36, tumble: 18, sway: -18, coin: "eth" },
  { id: 3, left: "22%", size: 126, delay: 7.5, fall: 30, tumble: 15, sway: 30, coin: "ltc" },
  { id: 4, left: "7%", size: 92, delay: 12, fall: 34, tumble: 19, sway: -14, coin: "doge", mobileHide: true },
  { id: 5, left: "17%", size: 156, delay: 16, fall: 38, tumble: 17, sway: 20, coin: "zec" },
  { id: 6, left: "26%", size: 98, delay: 20, fall: 31, tumble: 20, sway: -26, coin: "xmr", mobileHide: true },
  // right field
  { id: 7, left: "69%", size: 134, delay: 1.5, fall: 33, tumble: 16.5, sway: -22, coin: "doge" },
  { id: 8, left: "79%", size: 104, delay: 5.5, fall: 37, tumble: 14, sway: 16, coin: "eth" },
  { id: 9, left: "88%", size: 150, delay: 9, fall: 29, tumble: 17.5, sway: -28, coin: "btc" },
  { id: 10, left: "73%", size: 88, delay: 13.5, fall: 35, tumble: 19, sway: 18, coin: "ltc", mobileHide: true },
  { id: 11, left: "83%", size: 118, delay: 17.5, fall: 32, tumble: 15.5, sway: -20, coin: "xmr" },
  { id: 12, left: "92%", size: 112, delay: 21.5, fall: 36, tumble: 18, sway: 14, coin: "zec", mobileHide: true },
  // soft middle pass (behind the card)
  { id: 13, left: "39%", size: 78, delay: 6, fall: 40, tumble: 21, sway: 12, coin: "eth", mobileHide: true },
  { id: 14, left: "55%", size: 84, delay: 14, fall: 34, tumble: 16, sway: -16, coin: "btc", mobileHide: true },
];

export function AuthCoinRain() {
  return (
    <div className="auth-rain" aria-hidden="true">
      {DROPS.map((d) => (
        <span
          key={d.id}
          className={`auth-rain__drop${d.mobileHide ? " auth-rain__drop--mobile-hide" : ""}`}
          style={
            {
              left: d.left,
              width: d.size,
              height: d.size,
              animationDelay: `${d.delay}s`,
              animationDuration: `${d.fall}s`,
              "--sway": `${d.sway}px`,
            } as CSSProperties
          }
        >
          <img
            className="auth-rain__coin"
            src={`/coins/${d.coin}.png`}
            alt=""
            width={d.size}
            height={d.size}
            draggable={false}
            style={{
              animationDuration: `${d.tumble}s`,
              animationDelay: `${d.delay * 0.2}s`,
            }}
          />
        </span>
      ))}
    </div>
  );
}
