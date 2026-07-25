import { useState } from 'react';
import { MailWarning } from 'lucide-react';
import { api } from '../lib/api.js';
import { Btn } from './ui.jsx';

// Dải nhắc xác minh email, hiện trong Shell khi tài khoản chưa xác minh.
export default function VerifyBanner() {
  const [state, setState] = useState('idle'); // idle | sending | sent | verified | error

  async function resend() {
    setState('sending');
    try {
      const res = await api.resendVerification();
      setState(res.status === 'already_verified' ? 'verified' : 'sent');
    } catch {
      setState('error');
    }
  }

  if (state === 'verified') return null;   // hoá ra đã xác minh → ẩn luôn

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md bg-warning-soft px-4 py-3 text-sm text-warning-strong">
      <MailWarning size={18} className="shrink-0" />
      <span className="font-medium">Hãy xác minh email để bảo mật tài khoản.</span>
      {state === 'sent' && (
        <span className="text-accent-strong">Đã gửi liên kết — kiểm tra hộp thư (hoặc console backend).</span>
      )}
      {state === 'error' && <span className="text-danger">Gửi lại thất bại, thử lại sau.</span>}
      {state !== 'sent' && (
        <Btn variant="subtle" size="sm" onClick={resend} disabled={state === 'sending'} className="ml-auto">
          {state === 'sending' ? 'Đang gửi…' : 'Gửi lại'}
        </Btn>
      )}
    </div>
  );
}
