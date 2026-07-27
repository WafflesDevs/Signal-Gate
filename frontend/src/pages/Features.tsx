import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  VisualCharts,
  VisualGate,
  VisualLanguage,
  VisualMarket,
  VisualResearch,
} from "../components/features/FeatureVisuals";

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
