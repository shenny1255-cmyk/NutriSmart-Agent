import { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';

import { api } from '../lib/api.js';
import PasswordInput from '../components/PasswordInput.jsx';
import { Btn, Field as TextInput, Alert } from '../components/ui.jsx';
import AuthLayout from '../components/AuthLayout.jsx';
import { LogoMark } from '../components/Logo.jsx';

const isEmail = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s || '').trim());

// PasswordInput nhận className từ ngoài — dùng chung bộ style token với TextInput
export const inputCls =
  'min-h-11 w-full rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline placeholder:text-muted transition-[background-color,box-shadow] duration-short ease-out hover:bg-paper-3 focus:bg-paper-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const [demoLoading, setDemoLoading] = useState(false);
  const [params] = useSearchParams();
  // api.js đá về đây kèm ?expired=1 khi token hết hạn giữa chừng
  const expired = params.get('expired') === '1';

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
    <AuthLayout>
      <form onSubmit={submit} className="mx-auto w-full max-w-lg rounded-md bg-paper-2 p-6 shadow-card sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <LogoMark size={44} />
          <div>
            <h1 className="font-display text-xl font-bold tracking-tight text-ink">
              Nutri<span className="text-accent-strong">Smart</span>
            </h1>
            <p className="text-sm text-muted">Đăng nhập để tiếp tục</p>
          </div>
        </div>

        {expired && !err && (
          <div className="mb-4"><Alert tone="warning">Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.</Alert></div>
        )}

        <label htmlFor="login-email" className="mb-1 block text-sm font-medium text-ink-2">Email</label>
        <TextInput
          id="login-email"
          type="email" required value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full"
        />
        <p className="mb-3 mt-1 h-4 text-xs text-warning-strong" aria-live="polite">
          {email && !isEmail(email) ? 'Email chưa đúng định dạng' : ''}
        </p>

        <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-ink-2">Mật khẩu</label>
        <PasswordInput
          id="login-password"
          required value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={`mb-4 ${inputCls}`}
        />

        {err && <div className="mb-4"><Alert tone="danger">{err}</Alert></div>}

        <Btn type="submit" variant="primary" disabled={loading} className="w-full">
          {loading ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Btn>

        {/*
        <Btn type="button" variant="subtle" onClick={tryDemo} disabled={demoLoading} className="mt-3 w-full">
          {demoLoading ? 'Đang chuẩn bị dữ liệu…' : 'Dùng thử ngay (Demo)'}
        </Btn>
        */}

        <p className="mt-5 text-center text-sm text-muted">
          Chưa có tài khoản?{' '}
          <Link
            to="/register"
            className="rounded-sm font-medium text-accent-strong underline decoration-accent/40 underline-offset-2 transition-colors duration-micro ease-out hover:decoration-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
          >
            Đăng ký
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}