import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  VisualAlpaca,
  VisualCharts,
  VisualGate,
  VisualLanguage,
  VisualMarket,
  VisualResearch,
} from "../components/features/FeatureVisuals";
import { CREATOR } from "../lib/creator";

const features = [
  {
    index: "01",
    title: "Natural language trading",
    body: "Say “buy 0.5 ETH” or “sell all SOL.” Signal Gate turns intent into precise paper orders,  no dashboards to hunt through.",
    Visual: VisualLanguage,
  },
  {
    index: "02",
    title: "Double Checking",
    body: "Every buy and sell pauses for your yes or no. The agent proposes; you approve. Nothing leaves the desk without you.",
    Visual: VisualGate,
  },
  {
    index: "03",
    title: "Live market awareness",
    body: "Prices, positions, and portfolio value are pulled in real time so answers stay grounded in the book,not guesses.",
    Visual: VisualMarket,
  },
  {
    index: "04",
    title: "Research on demand",
    body: "Ask what’s moving a coin and the assistant searches the web, then reports only what it finds, no invented headlines.",
    Visual: VisualResearch,
  },
  {
    index: "05",
    title: "Live candle charts",
    body: "Using Tradingviews API,Ask for a price and tap See it live, or open Charts in the nav. Switch 1m, 5m, 15m, and more on real candle bars.",
    Visual: VisualCharts,
  },
  {
    index: "06",
    title: "Alpaca Trading API",
    body: "Paper and live orders ride Alpaca’s Trading API — your keys, their rails, Signal Gate in between.",
    Visual: VisualAlpaca,
  },
];

const faqs = [
  {
    q: "Who’s the creator?",
    a: `Signal Gate is built by ${CREATOR}.`,
  },
  {
    q: "What does it do?",
    a: "It’s a crypto trading desk you talk to. Ask for prices, research, portfolio checks, or place paper (or live) orders in plain English — with a gate before anything hits the wire.",
  },
  {
    q: "How does it work?",
    a: "You chat. The agent reads your book and the market, proposes a trade when you ask, then waits for your yes or no. Approved orders go out through your linked Alpaca keys.",
  },
  {
    q: "What API does it use?",
    a: "Alpaca Trading API — for accounts, positions, and order routing. Charts use live candle data; research pulls from the web when you ask.",
  },
  {
    q: "Do I need an account?",
    a: "Yes. Sign up for Signal Gate, then link your Alpaca API keys in Settings so the desk can quote and trade on your account.",
  },
  {
    q: "Paper vs live — what’s the difference?",
    a: "Paper uses Alpaca’s simulated account (no real money). Live uses real funds. Toggle the mode in Settings and paste keys from the matching Alpaca dashboard.",
  },
  {
    q: "Do trades need my approval?",
    a: "Yes. Every buy and sell pauses for your confirm. The agent proposes; you approve. Nothing leaves the desk without you.",
  },
  {
    q: "Can I see charts while I chat?",
    a: "Yes. Ask for a price and open the live chart, or go to Charts in the nav. Switch timeframes on real candle bars while you keep talking.",
  },
  {
    q: "Is it free?",
    a: "Signal Gate itself is free to use. You’ll need an Alpaca account (paper is free to practice). Live trading uses your own capital and Alpaca’s terms.",
  },
];

const fadeUp = {
  initial: { opacity: 0, y: 32 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.35 },
  transition: { duration: 0.65, ease: [0.22, 1, 0.36, 1] as const },
};

export function Features() {
  return (
    <div className="page features">
      <motion.div className="features__intro" {...fadeUp}>
        <p className="features__kicker">Capabilities</p>
        <h1 className="features__title">Trading Agentic Assistant</h1>
        <p className="features__lead">
          Signal Gate sits between you and the market: an AI that can act, and a
          gate that waits for you.
        </p>
      </motion.div>

      {features.map((f) => (
        <motion.section key={f.index} className="feature-block" {...fadeUp}>
          <div>
            <div className="feature-block__index">{f.index}</div>
            <h2 className="feature-block__title">{f.title}</h2>
            <p className="feature-block__body">{f.body}</p>
          </div>
          <div className="feature-block__visual">
            <f.Visual className="feature-art" />
          </div>
        </motion.section>
      ))}

      <motion.section className="features-faq" {...fadeUp} aria-labelledby="features-faq-title">
        <div className="features-faq__intro">
          <p className="features__kicker">FAQ</p>
          <h2 id="features-faq-title" className="features-faq__title">
            Questions at the desk
          </h2>
          <p className="features-faq__lead">
            Short answers on who built it, how trades clear, and what you need to start.
          </p>
        </div>

        <div className="features-faq__list">
          {faqs.map((item) => (
            <details key={item.q} className="features-faq__item">
              <summary className="features-faq__q">{item.q}</summary>
              <p className="features-faq__a">{item.a}</p>
            </details>
          ))}
        </div>
      </motion.section>

      <motion.div className="features__cta" {...fadeUp}>
        <div>
          <h2>Ready to open the desk?</h2>
          <p>Chat, approve trades, or watch live charts.</p>
        </div>
        <div className="features__cta-actions">
          <Link to="/chat" className="btn btn--primary">
            Enter chat
          </Link>
          <Link to="/charts" className="btn btn--ghost">
            View charts
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
