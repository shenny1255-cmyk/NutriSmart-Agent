import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../lib/api.js';
import PasswordInput from '../components/PasswordInput.jsx';

const isEmail = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s || '').trim());

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
    } catch (e) {
      setErr(
        e.status === undefined
          ? 'Không kết nối được máy chủ — backend đã chạy chưa?'
          : 'Không tạo được tài khoản demo, thử lại sau.'
      );
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
    } catch (e) {
      if (e.status === 401) setErr('Email hoặc mật khẩu không đúng.');
      else if (e.status === 422) setErr('Email chưa đúng định dạng.');
      else if (e.status === undefined) setErr('Không kết nối được máy chủ. Backend đã chạy chưa?');
      else setErr(typeof e.detail === 'string' ? e.detail : 'Đăng nhập thất bại, thử lại sau.');
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
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
        />
        <p className="mb-4 mt-1 h-4 text-xs text-amber-600">
          {email && !isEmail(email) ? 'Email chưa đúng định dạng' : ''}
        </p>

        <label className="mb-1 block text-sm font-medium">Mật khẩu</label>
        <PasswordInput
          required value={password}
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