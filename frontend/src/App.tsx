import { NavLink, Route, Routes } from "react-router-dom";
import AdminAIProviders from "./pages/Admin/AdminAIProviders";
import AdminAudit from "./pages/Admin/AdminAudit";
import AdminSettings from "./pages/Admin/AdminSettings";
import AdminStats from "./pages/Admin/AdminStats";
import AdminUsers from "./pages/AdminUsers";
import AITokens from "./pages/AITokens";
import AiKeys from "./pages/AiKeys";
import Analytics from "./pages/Analytics";
import SSHCredentials from "./pages/Credentials/SSH";
import Dashboard from "./pages/Dashboard";
import Servers from "./pages/Servers";
import TaskDetail from "./pages/TaskDetail";

function Nav() {
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-sm font-medium transition ${
      isActive ? "bg-emerald-500/20 text-emerald-300" : "text-slate-400 hover:text-white"
    }`;
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold tracking-tight text-white">DevOps AI Agent</span>
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">Web</span>
        </div>
        <nav className="flex gap-1">
          <NavLink to="/" end className={link}>
            Dashboard
          </NavLink>
          <NavLink to="/servers" className={link}>
            Serverlar
          </NavLink>
          <NavLink to="/ai-keys" className={link}>
            AI kalitlar
          </NavLink>
          <NavLink to="/credentials/tokens" className={link}>
            AI tokens
          </NavLink>
          <NavLink to="/credentials/ssh" className={link}>
            SSH
          </NavLink>
          <NavLink to="/analytics" className={link}>
            Analytics
          </NavLink>
          <NavLink to="/admin/users" className={link}>
            Admin
          </NavLink>
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <Nav />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/servers" element={<Servers />} />
          <Route path="/ai-keys" element={<AiKeys />} />
          <Route path="/credentials/tokens" element={<AITokens />} />
          <Route path="/credentials/ssh" element={<SSHCredentials />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/stats" element={<AdminStats />} />
          <Route path="/admin/settings" element={<AdminSettings />} />
          <Route path="/admin/ai" element={<AdminAIProviders />} />
          <Route path="/admin/audit" element={<AdminAudit />} />
          <Route path="/tasks/:id" element={<TaskDetail />} />
        </Routes>
      </main>
    </div>
  );
}
