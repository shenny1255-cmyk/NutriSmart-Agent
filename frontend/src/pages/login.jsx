import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../lib/api.js';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [demoLoading, setDemoLoading] = useState(false);

  async function tryDemo() {
    setErr(null);
    setDemoLoading(true);
    try {
      // seed sẽ tạo/reset tài khoản demo và trả token luôn
      const res = await api.seedDemo();
      localStorage.setItem('access_token', res.access_token);
      const me = await api.me();
      localStorage.setItem('role', me.role);
      window.location.href = '/';
    } catch {
      setErr('Không tạo được tài khoản demo — backend đã chạy chưa?');
      setDemoLoading(false);
    }
  }
  async function submit(e) {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      const res = await api.login(email, password);
      localStorage.setItem('access_token', res.access_token);
      const me = await api.me();
      localStorage.setItem('role', me.role);
      navigate('/');
    } catch {
      setErr('Email hoặc mật khẩu không đúng.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <form onSubmit={submit} className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8">
        <h1 className="text-xl font-bold text-emerald-700">NutriSmart</h1>
        <p className="mb-6 text-sm text-slate-500">Đăng nhập để tiếp tục</p>

        <label className="mb-1 block text-sm font-medium">Email</label>
        <input
          type="email" required value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        />

        <label className="mb-1 block text-sm font-medium">Mật khẩu</label>
        <input
          type="password" required value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        />

        {err && <p className="mb-4 text-sm text-red-600">{err}</p>}

        <button
          type="submit" disabled={loading}
          className="w-full rounded-lg bg-emerald-600 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>

        {/*
        <button
          type="button"
          onClick={tryDemo}
          disabled={demoLoading}
          className="mt-3 w-full rounded-lg border border-emerald-600 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
        >
          {demoLoading ? 'Đang chuẩn bị dữ liệu…' : 'Dùng thử ngay (Demo)'}
        </button>
        */}

        <p className="mt-4 text-center text-sm text-slate-500">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="text-emerald-700 underline">Đăng ký</Link>
        </p>
      </form>
    </div>
  );
}