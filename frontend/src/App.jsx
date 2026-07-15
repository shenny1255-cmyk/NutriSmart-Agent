import { Routes, Route, NavLink, Navigate, Outlet } from 'react-router-dom';
import { LayoutDashboard, CalendarCheck, Camera, MessageSquare, LogOut } from 'lucide-react';
import Dashboard from './pages/Dashboard.jsx';
import Plan from './pages/Plan.jsx';
import MealScan from './pages/MealScan.jsx';
import Chat from './pages/Chat.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import { Shield, FileCheck } from 'lucide-react';
import AdminUsers from './pages/AdminUsers.jsx';
import AdminDrugs from './pages/AdminDrugs.jsx';
import AdminAudit from './pages/AdminAudit.jsx';
import ExpertReview from './pages/ExpertReview.jsx';

const baseNav = [

  { to: '/', label: 'Tổng quan', icon: LayoutDashboard, roles: ['USER', 'EXPERT', 'ADMIN'] },
  { to: '/plan', label: 'Lộ trình', icon: CalendarCheck, roles: ['USER', 'EXPERT', 'ADMIN'] },
  { to: '/scan', label: 'Phân tích món ăn', icon: Camera, roles: ['USER', 'EXPERT', 'ADMIN'] },
  { to: '/chat', label: 'Trợ lý AI', icon: MessageSquare, roles: ['USER', 'EXPERT', 'ADMIN'] },
  { to: '/expert/review', label: 'Duyệt tài liệu', icon: FileCheck, roles: ['EXPERT', 'ADMIN'] },
  { to: '/admin/users', label: 'Người dùng', icon: Shield, roles: ['ADMIN'] },
  { to: '/admin/drugs', label: 'Thuốc', icon: Shield, roles: ['ADMIN'] },
  { to: '/admin/audit', label: 'Nhật ký', icon: Shield, roles: ['ADMIN'] },
];

// Chặn truy cập nếu chưa đăng nhập
function RequireAuth() {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function Shell() {
  const role = localStorage.getItem('role') || 'USER';
  const nav = baseNav.filter((item) => item.roles.includes(role));

  function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4">
        <div className="mb-8 px-2">
          <h1 className="text-lg font-bold text-emerald-700">NutriSmart</h1>
          <p className="text-xs text-slate-500">Agent · Nhóm E15</p>
        </div>

        <nav className="flex-1 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${isActive
                  ? 'bg-emerald-50 font-medium text-emerald-700'
                  : 'text-slate-600 hover:bg-slate-100'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={logout}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-100"
        >
          <LogOut size={18} />
          Đăng xuất
        </button>
      </aside>

      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/scan" element={<MealScan />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/expert/review" element={<ExpertReview />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/drugs" element={<AdminDrugs />} />
          <Route path="/admin/audit" element={<AdminAudit />} />
        </Route>
      </Route>
    </Routes>
  );
}