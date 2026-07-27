export function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <p className="site-footer__credit">
          Made by <span className="credit-name">WaffeDevs</span>
        </p>
        <div className="site-footer__links">
          <a
            href="https://www.linkedin.com/in/ayaanalii/"
            target="_blank"
            rel="noreferrer"
          >
            LinkedIn
          </a>
          <a
            href="https://github.com/WafflesDevs"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </div>
      </div>
      <p className="site-footer__disclaimer">
        Not financial advice. Signal Gate is a paper-trading demo for education
        only. Crypto is volatile — you are solely responsible for any real-money
        decisions you make. We are not liable for losses.
      </p>
    </footer>
  );
}
