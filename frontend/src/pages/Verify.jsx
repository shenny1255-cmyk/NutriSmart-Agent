import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { api } from '../lib/api.js';
import AuthLayout from '../components/AuthLayout.jsx';
import { LogoMark } from '../components/Logo.jsx';
import { Btn } from '../components/ui.jsx';

// Trang công khai: người dùng bấm link trong email → xác minh token.
export default function Verify() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token');
  const [status, setStatus] = useState('verifying'); // verifying | success | failed

  useEffect(() => {
    if (!token) { setStatus('failed'); return; }
    api.verifyEmail(token).then(() => setStatus('success')).catch(() => setStatus('failed'));
  }, [token]);

  return (
    <AuthLayout>
      <div className="mx-auto w-full max-w-md rounded-md bg-paper-2 p-6 text-center shadow-card sm:p-8">
        <div className="mb-6 flex items-center justify-center gap-3">
          <LogoMark size={44} />
          <h1 className="font-display text-xl font-bold tracking-tight text-ink">
            Nutri<span className="text-accent-strong">Smart</span>
          </h1>
        </div>

        {status === 'verifying' && (
          <div className="flex flex-col items-center gap-3 text-muted">
            <Loader2 className="animate-spin text-accent-strong" size={32} />
            <p className="text-sm">Đang xác minh email…</p>
          </div>
        )}

        {status === 'success' && (
          <div className="flex flex-col items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
              <CheckCircle2 size={30} />
            </span>
            <p className="text-sm text-ink-2">Email của bạn đã được xác minh thành công!</p>
            <Btn variant="primary" onClick={() => navigate('/')}>Vào ứng dụng</Btn>
          </div>
        )}

        {status === 'failed' && (
          <div className="flex flex-col items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-danger-soft text-danger">
              <XCircle size={30} />
            </span>
            <p className="text-sm text-ink-2">Liên kết xác minh không hợp lệ hoặc đã hết hạn.</p>
            <p className="text-xs text-muted">Đăng nhập rồi bấm “Gửi lại” để nhận liên kết mới.</p>
            <Btn variant="subtle" onClick={() => navigate('/login')}>Đến trang đăng nhập</Btn>
          </div>
        )}
      </div>
    </AuthLayout>
  );
}
