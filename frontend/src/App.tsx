import React from "react";
import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import AdviserDetailPage from "./pages/AdviserDetailPage";
import AdvisersPage from "./pages/AdvisersPage";
import Overview from "./pages/Overview";

const navStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1.5rem",
  padding: "0 2rem",
  background: "#1a1a2e",
  color: "#fff",
  height: "56px",
  boxShadow: "0 2px 6px rgba(0,0,0,0.3)",
};

const linkStyle: React.CSSProperties = {
  color: "#cdd5e0",
  textDecoration: "none",
  fontSize: "0.95rem",
  fontWeight: 500,
  padding: "4px 0",
  borderBottom: "2px solid transparent",
  transition: "color 0.2s, border-color 0.2s",
};

const activeLinkStyle: React.CSSProperties = {
  ...linkStyle,
  color: "#fff",
  borderBottom: "2px solid #4fa8ff",
};

const brandStyle: React.CSSProperties = {
  fontWeight: 700,
  fontSize: "1.1rem",
  color: "#fff",
  textDecoration: "none",
  marginRight: "auto",
  letterSpacing: "0.02em",
};

export default function App() {
  return (
    <BrowserRouter>
      <nav style={navStyle}>
        <Link to="/" style={brandStyle}>
          SEC Adviser Monitor
        </Link>
        <NavLink
          to="/"
          end
          style={({ isActive }) => (isActive ? activeLinkStyle : linkStyle)}
        >
          Overview
        </NavLink>
        <NavLink
          to="/advisers"
          style={({ isActive }) => (isActive ? activeLinkStyle : linkStyle)}
        >
          Advisers
        </NavLink>
      </nav>
      <main style={{ minHeight: "calc(100vh - 56px)" }}>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/advisers" element={<AdvisersPage />} />
          <Route path="/advisers/:crd" element={<AdviserDetailPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
