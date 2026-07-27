import { Route, Routes, useLocation } from "react-router-dom";
import { Nav } from "./components/layout/Nav";
import { Atmosphere } from "./components/layout/Atmosphere";
import { Footer } from "./components/layout/Footer";
import { PageTransition } from "./components/layout/PageTransition";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Home } from "./pages/Home";
import { Features } from "./pages/Features";
import { Charts } from "./pages/Charts";
import { Chat } from "./pages/Chat";
import { Login } from "./pages/Login";
import { Settings } from "./pages/Settings";

export default function App() {
  const { pathname } = useLocation();
  const showFooter = pathname !== "/chat";
  const hideNav = pathname === "/chat";

  return (
    <div className="app-shell">
      <Atmosphere />
      <PageTransition />
      {!hideNav && <Nav />}
      <main className={`app-main${hideNav ? " app-main--flush" : ""}`}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/features" element={<Features />} />
          <Route path="/login" element={<Login />} />
          <Route
            path="/charts"
            element={
              <ProtectedRoute>
                <Charts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
      {showFooter && <Footer />}
    </div>
  );
}
