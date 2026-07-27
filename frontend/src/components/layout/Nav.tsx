import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const { user, signOut } = useAuth();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.classList.toggle("nav-open", open);
    return () => document.body.classList.remove("nav-open");
  }, [open]);

  return (
    <header className={`nav${scrolled ? " nav--scrolled" : ""}${open ? " nav--open" : ""}`}>
      <Link to="/" className="nav__brand" onClick={() => setOpen(false)}>
        <img src="/signal-s.png" alt="" className="nav__mark" />
        <span className="nav__wordmark brand-name">Signal Gate</span>
      </Link>

      <button
        className="nav__burger"
        aria-label="Menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span />
      </button>

      <nav className={`nav__links${open ? " nav__links--open" : ""}`}>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `nav__link${isActive ? " nav__link--active" : ""}`
          }
          onClick={() => setOpen(false)}
        >
          Home
        </NavLink>
        <NavLink
          to="/features"
          className={({ isActive }) =>
            `nav__link${isActive ? " nav__link--active" : ""}`
          }
          onClick={() => setOpen(false)}
        >
          Features
        </NavLink>
        <NavLink
          to="/charts"
          className={({ isActive }) =>
            `nav__link${isActive ? " nav__link--active" : ""}`
          }
          onClick={() => setOpen(false)}
        >
          Charts
        </NavLink>
        <NavLink
          to="/chat"
          className={({ isActive }) =>
            `nav__link${isActive ? " nav__link--active" : ""}`
          }
          onClick={() => setOpen(false)}
        >
          Chat
        </NavLink>
        {user && (
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              `nav__link${isActive ? " nav__link--active" : ""}`
            }
            onClick={() => setOpen(false)}
          >
            Settings
          </NavLink>
        )}
        {user ? (
          <>
            <button
              type="button"
              className="nav__link"
              onClick={() => {
                setOpen(false);
                void signOut();
              }}
            >
              Log out
            </button>
            <Link to="/chat" className="nav__cta" onClick={() => setOpen(false)}>
              Open desk
            </Link>
          </>
        ) : (
          <Link to="/login" className="nav__cta" onClick={() => setOpen(false)}>
            Log in
          </Link>
        )}
      </nav>
    </header>
  );
}
