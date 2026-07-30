import { DISCLAIMER_PRIMARY, DISCLAIMER_SECONDARY } from "../../lib/disclaimer";

type Props = {
  /** Hide the optional second line when space is tight. */
  compact?: boolean;
  className?: string;
};

/** Muted legal-style risk notice for chat, auth, and Alpaca linking. */
export function RiskDisclaimer({ compact = false, className = "" }: Props) {
  return (
    <p className={`risk-disclaimer${className ? ` ${className}` : ""}`} role="note">
      <span className="risk-disclaimer__primary">{DISCLAIMER_PRIMARY}</span>
      {!compact && (
        <span className="risk-disclaimer__secondary">{DISCLAIMER_SECONDARY}</span>
      )}
    </p>
  );
}
