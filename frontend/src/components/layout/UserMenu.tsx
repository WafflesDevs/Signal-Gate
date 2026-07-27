import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

function initialFromEmail(email: string | undefined) {
  if (!email) return "U";
  return email.trim().charAt(0).toUpperCase();
}

export function UserMenu() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  if (!user) return null;

  async function onLogout() {
    setOpen(false);
    await signOut();
    navigate("/login");
  }

  return (
    <div className="user-menu" ref={rootRef}>
      <button
        type="button"
        className="user-menu__avatar"
        aria-label="Account menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {initialFromEmail(user.email)}
      </button>

      {open && (
        <div className="user-menu__dropdown">
          <div className="user-menu__meta">
            <span className="user-menu__label">Signed in</span>
            <span className="user-menu__email">{user.email}</span>
          </div>
          <button
            type="button"
            className="user-menu__item"
            onClick={() => {
              setOpen(false);
              navigate("/settings");
            }}
          >
            Settings
          </button>
          <button type="button" className="user-menu__logout" onClick={() => void onLogout()}>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}
