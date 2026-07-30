import { CREATOR, CREATOR_LINKS } from "../../lib/creator";
import { RiskDisclaimer } from "./RiskDisclaimer";

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <p className="site-footer__credit">
          Made by <span className="credit-name">{CREATOR}</span>
        </p>
        <div className="site-footer__links">
          <a href={CREATOR_LINKS.linkedin} target="_blank" rel="noreferrer">
            LinkedIn
          </a>
          <a href={CREATOR_LINKS.github} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </div>
      </div>
      <RiskDisclaimer className="site-footer__disclaimer" />
    </footer>
  );
}
