import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useLocation } from "react-router-dom";
import { CREATOR, CREATOR_LINKS } from "../../lib/creator";

const DURATION_MS = 1000;
const FADE_S = 0.28;
const EASE = [0.22, 1, 0.36, 1] as const;

/**
 * Full-screen brand overlay on client-side route changes.
 * Restarts cleanly if the user navigates again mid-transition.
 * Skips the initial mount so hard reloads don't flash a splash.
 */
export function PageTransition() {
  const { pathname } = useLocation();
  const [active, setActive] = useState(false);
  const [runId, setRunId] = useState(0);
  const isFirst = useRef(true);
  const gen = useRef(0);

  useEffect(() => {
    if (isFirst.current) {
      isFirst.current = false;
      return;
    }

    const id = ++gen.current;
    setRunId(id);
    setActive(true);

    // Start exit so fade-out completes at ~1s total.
    const hide = window.setTimeout(() => {
      if (gen.current === id) setActive(false);
    }, DURATION_MS - FADE_S * 1000);

    return () => window.clearTimeout(hide);
  }, [pathname]);

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          key={runId}
          className="page-transition"
          role="status"
          aria-live="polite"
          aria-label="Loading page"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: FADE_S, ease: EASE }}
        >
          <motion.div
            className="page-transition__inner"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.04 }}
            transition={{ duration: FADE_S + 0.07, ease: EASE }}
          >
            <img
              src="/signal-s.png"
              alt="Signal Gate"
              className="page-transition__logo"
              width={80}
              height={80}
              draggable={false}
            />
            <p className="page-transition__brand">
              <span>Signal</span>
              <span>Gate</span>
            </p>
            <p className="page-transition__credit">
              Created by <span className="credit-name">{CREATOR}</span>
            </p>
            <div className="page-transition__links">
              <a
                href={CREATOR_LINKS.linkedin}
                target="_blank"
                rel="noreferrer"
              >
                LinkedIn
              </a>
              <span className="page-transition__sep" aria-hidden="true">
                ·
              </span>
              <a href={CREATOR_LINKS.github} target="_blank" rel="noreferrer">
                GitHub
              </a>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
