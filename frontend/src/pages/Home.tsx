import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const tickers = [
  { s: "BTC", p: "97,420", d: "+1.8%" },
  { s: "ETH", p: "3,412", d: "+0.9%" },
  { s: "SOL", p: "178.40", d: "-0.4%", down: true },
  { s: "XRP", p: "2.31", d: "+3.2%" },
  { s: "AVAX", p: "28.10", d: "+1.1%" },
  { s: "LINK", p: "16.88", d: "-0.2%", down: true },
];

const assets = [
  { symbol: "BTC", name: "Bitcoin" },
  { symbol: "ETH", name: "Ethereum" },
  { symbol: "SOL", name: "Solana" },
  { symbol: "XRP", name: "XRP" },
  { symbol: "DOGE", name: "Dogecoin" },
  { symbol: "AVAX", name: "Avalanche" },
  { symbol: "LINK", name: "Chainlink" },
  { symbol: "ADA", name: "Cardano" },
  { symbol: "DOT", name: "Polkadot" },
  { symbol: "LTC", name: "Litecoin" },
  { symbol: "UNI", name: "Uniswap" },
  { symbol: "PEPE", name: "Pepe" },
];

export function Home() {
  const doubled = [...tickers, ...tickers];

  return (
    <div className="page">
      <section className="hero">
        <div className="hero__layout">
          <motion.div
            initial={{ opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          >
            <h1 className="hero__brand">
              <span>Signal</span>
              <span>Gate</span>
            </h1>
            <p className="hero__headline">
              Your crypto trading desk, spoken in plain English. Powered by Alpaca's API.
            </p>
            <p className="hero__sub">
              Ask prices, scan markets, and paper-trade with human approval
              before every order hits the wire.
            </p>
            <div className="hero__actions">
              <Link to="/chat" className="btn btn--primary">
                Start chatting
              </Link>
              <Link to="/features" className="btn btn--ghost">
                See features
              </Link>
            </div>
          </motion.div>

          <motion.div
            className="hero__visual"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="hero__ring hero__ring--slow" />
            <div className="hero__ring" />
            <img
              src="/signal-s.png"
              alt="Signal Gate mark"
              className="hero__icon"
            />
          </motion.div>
        </div>

        <div className="hero__ticker" aria-hidden="true">
          <div className="hero__ticker-track">
            {doubled.map((t, i) => (
              <span key={`${t.s}-${i}`}>
                {t.s} <b className={t.down ? "down" : undefined}>{t.p}</b>{" "}
                <span className={t.down ? "down" : undefined}>{t.d}</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="assets">
        <div className="assets__top">
          <motion.div
            className="assets__intro"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.4 }}
            transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          >
            <p className="assets__kicker">Markets</p>
            <h2 className="assets__title">Trade across dozens of crypto assets</h2>
            <p className="assets__lead">
              From majors like Bitcoin and Ethereum to SOL, XRP, DOGE, and more —
              ask Signal Gate to quote, buy, or sell any coin on your desk.
            </p>
          </motion.div>

          <motion.div
            className="assets__showcase"
            aria-hidden="true"
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.75, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="assets__card assets__card--coin">
              <img
                src="/coins/sol.png"
                alt=""
                className="assets__card-coin"
                draggable={false}
              />
            </div>
          </motion.div>
        </div>

        <motion.ul
          className="assets__grid"
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.25 }}
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: 0.05 } },
          }}
        >
          {assets.map((a) => (
            <motion.li
              key={a.symbol}
              className="assets__coin"
              variants={{
                hidden: { opacity: 0, y: 16 },
                show: {
                  opacity: 1,
                  y: 0,
                  transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
                },
              }}
            >
              <span className="assets__symbol">{a.symbol}</span>
              <span className="assets__name">{a.name}</span>
            </motion.li>
          ))}
        </motion.ul>

        <p className="assets__note">
          30+ base assets supported · paper trade any ticker on your list
        </p>
      </section>
    </div>
  );
}
