import { BrowserRouter, Routes, Route, NavLink, Navigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  ClipboardCheck,
  HeartHandshake,
  ShieldCheck,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import EmployeeExplorer from "./pages/EmployeeExplorer";
import HumanReviews from "./pages/HumanReviews";
import InterventionManagement from "./pages/InterventionManagement";
import DataQuality from "./pages/DataQuality";
import "./App.css";

function AppLayout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">RA</div>
          <div>
            <h2>Retention Analytics</h2>
            <span>Workforce Insights</span>
          </div>
        </div>

        <p className="nav-label">MAIN MENU</p>

        <nav className="sidebar-nav">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>

          <NavLink to="/employees" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <Users size={18} />
            Employee Explorer
          </NavLink>

          <NavLink to="/reviews" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <ClipboardCheck size={18} />
            Human Reviews
          </NavLink>

          <NavLink to="/interventions" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <HeartHandshake size={18} />
            Interventions
          </NavLink>

          <NavLink to="/data-quality" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
            <ShieldCheck size={18} />
            Data Quality
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <span>Employee Retention Analytics</span>
          <small>Prototype · Version 1.0</small>
        </div>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/employees" element={<EmployeeExplorer />} />
          <Route path="/reviews" element={<HumanReviews />} />
          <Route path="/interventions" element={<InterventionManagement />} />
          <Route path="/data-quality" element={<DataQuality />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

export default App;