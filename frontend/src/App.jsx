import { useEffect, useState } from 'react';
import { Routes, Route, NavLink, Navigate, Outlet } from 'react-router-dom';
import { LayoutDashboard, CalendarCheck, Camera, MessageSquare, LogOut, Menu, X } from 'lucide-react';
import Dashboard from './pages/dashboard.jsx';
import Plan from './pages/Plan.jsx';
import MealScan from './pages/mealscan.jsx';
import Chat from './pages/Chat.jsx';
import Login from './pages/login.jsx';
import Register from './pages/register.jsx';
import { Shield, FileCheck } from 'lucide-react';
import AdminUsers from './pages/AdminUsers.jsx';
import AdminDrugs from './pages/AdminDrugs.jsx';
import AdminAudit from './pages/AdminAudit.jsx';
import ExpertReview from './pages/ExpertReview.jsx';
import Verify from './pages/Verify.jsx';
import { Logo, LogoMark } from './components/Logo.jsx';
import VerifyBanner from './components/VerifyBanner.jsx';
import { api } from './lib/api.js';

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

// Đã đăng nhập rồi thì không xem lại trang đăng nhập/đăng ký nữa
function RedirectIfAuthed() {
  const token = localStorage.getItem('access_token');
  if (token) return <Navigate to="/" replace />;
  return <Outlet />;
}

function NavList({ nav, onNavigate }) {
  return (
    <nav className="flex-1 space-y-1">
      {nav.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            [
              'group flex min-h-11 items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium',
              'transition-[background-color,color,transform] duration-short ease-out',
              'hover:translate-x-0.5 active:translate-x-0 active:duration-micro',
              isActive
                ? 'bg-accent-soft text-accent-strong'
                : 'text-ink-2 hover:bg-paper-3 hover:text-ink',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                size={18}
                strokeWidth={isActive ? 2.4 : 2}
                className="shrink-0 transition-transform duration-short ease-out group-hover:scale-110"
              />
              <span className="truncate">{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function Shell() {
  const role = localStorage.getItem('role') || 'USER';
  const nav = baseNav.filter((item) => item.roles.includes(role));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [emailVerified, setEmailVerified] = useState(true);   // mặc định true → tránh nháy banner

  useEffect(() => {
    api.me().then((me) => setEmailVerified(me.email_verified)).catch(() => {});
  }, []);

  function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
  }

  const brand = (
    <div className="mb-8 px-2">
      <Logo size={36} subtitle="Agent · Nhóm E15" />
    </div>
  );

  const logoutButton = (
    <button
      onClick={logout}
      className="flex min-h-11 items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-muted transition-colors duration-short ease-out hover:bg-danger-soft hover:text-danger focus-visible:bg-danger-soft focus-visible:text-danger disabled:cursor-not-allowed disabled:opacity-50"
    >
      <LogOut size={18} />
      Đăng xuất
    </button>
  );

  return (
    <div className="min-h-screen bg-paper font-body text-ink">
      {/* Mobile top bar — 320–767px */}
      <header className="flex items-center justify-between border-b border-rule bg-paper-2 px-4 py-3 md:hidden">
        <div className="flex items-center gap-2.5">
          <LogoMark size={28} />
          <h1 className="font-display text-base font-bold text-ink">
            Nutri<span className="text-accent-strong">Smart</span>
          </h1>
        </div>
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Mở menu điều hướng"
          className="flex h-11 w-11 items-center justify-center rounded-md text-ink-2 transition-colors duration-short ease-out hover:bg-paper-3 focus-visible:bg-paper-3"
        >
          <Menu size={22} />
        </button>
      </header>

      {/* Mobile off-canvas drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-overlay md:hidden">
          <div
            className="absolute inset-0 bg-ink/40 transition-opacity duration-short ease-out"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-paper-2 p-4 shadow-card">
            <div className="mb-4 flex items-center justify-between">
              {brand}
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Đóng menu"
                className="flex h-11 w-11 items-center justify-center rounded-md text-ink-2 hover:bg-paper-3"
              >
                <X size={20} />
              </button>
            </div>
            <NavList nav={nav} onNavigate={() => setMobileOpen(false)} />
            {logoutButton}
          </aside>
        </div>
      )}

      <div className="flex">
        {/* Desktop sidebar — soft-elevated surface (playful genre bans decorative glassmorphism) */}
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-rule bg-paper-2 p-4 shadow-whisper md:flex">
          {brand}
          <NavList nav={nav} />
          {logoutButton}
        </aside>

        <main className="min-w-0 flex-1 overflow-y-auto p-4 md:p-8">
          {!emailVerified && (
            <div className="mb-4">
              <VerifyBanner />
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<RedirectIfAuthed />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Công khai: bấm link trong email để xác minh (kể cả khi chưa/đã đăng nhập) */}
      <Route path="/verify" element={<Verify />} />

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