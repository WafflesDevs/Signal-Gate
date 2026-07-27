import { Route, Routes, useLocation } from "react-router-dom";
import { Nav } from "./components/layout/Nav";
import { Atmosphere } from "./components/layout/Atmosphere";
import { Footer } from "./components/layout/Footer";
import { Home } from "./pages/Home";
import { Features } from "./pages/Features";
import { Charts } from "./pages/Charts";
import { Chat } from "./pages/Chat";
import { Login } from "./pages/Login";

export default function App() {
  const { pathname } = useLocation();
  const showFooter = pathname !== "/chat";
  const hideNav = pathname === "/chat";

  return (
    <div className="app-shell">
      <Atmosphere />
      {!hideNav && <Nav />}
      <main className={`app-main${hideNav ? " app-main--flush" : ""}`}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/features" element={<Features />} />
          <Route path="/charts" element={<Charts />} />
          <Route path="/login" element={<Login />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </main>
      {showFooter && <Footer />}
    </div>
  );
}
