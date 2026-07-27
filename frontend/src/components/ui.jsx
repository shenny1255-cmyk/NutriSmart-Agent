// Bộ primitive UI dùng chung cho các trang bảng biểu (Admin + Expert)
// Mọi màu tham chiếu token qua Tailwind class — không inline OKLCH.

import { useEffect, useId, useState, useRef, useCallback } from 'react';

export function Card({ className = '', children }) {
  return (
    <div className={`rounded-md bg-paper-2 shadow-hairline ${className}`}>
      {children}
    </div>
  );
}

// Bảng: cuộn ngang trên mobile, số dùng tabular-nums, hàng hover nhẹ
export function TableShell({ children }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-sm [font-variant-numeric:tabular-nums]">
        {children}
      </table>
    </Card>
  );
}

export function THead({ cols }) {
  return (
    <thead className="border-b border-rule-2 text-left text-xs font-medium uppercase tracking-wide text-muted">
      <tr>
        {cols.map((c, i) => (
          <th key={i} className={`px-4 py-3 ${c === '' ? 'w-0' : ''}`}>{c}</th>
        ))}
      </tr>
    </thead>
  );
}

export function Tr({ children }) {
  return (
    <tr className="border-t border-rule-2 transition-colors duration-micro ease-out hover:bg-paper-3">
      {children}
    </tr>
  );
}

export function Td({ className = '', children }) {
  return <td className={`px-4 py-3 align-middle ${className}`}>{children}</td>;
}

// Nút — 4 biến thể, đủ 8 trạng thái qua pseudo-class + disabled + loading (caller tự đổi label)
const BTN_VARIANTS = {
  primary:
    'bg-accent-strong text-accent-ink shadow-whisper hover:-translate-y-px hover:shadow-card active:translate-y-0 active:shadow-whisper',
  subtle:
    'bg-paper-2 text-accent-strong shadow-hairline hover:bg-accent-soft active:bg-accent-soft',
  danger:
    'bg-danger text-paper-2 shadow-whisper hover:-translate-y-px hover:shadow-card active:translate-y-0',
  'danger-subtle':
    'bg-paper-2 text-danger shadow-hairline hover:bg-danger-soft active:bg-danger-soft',
  ghost:
    'text-ink-2 hover:bg-paper-3 active:bg-paper-3',
};

export function Btn({ variant = 'subtle', size = 'md', className = '', children, ...props }) {
  return (
    <button
      {...props}
      className={[
        'inline-flex items-center justify-center gap-1.5 rounded-sm font-medium',
        size === 'sm' ? 'min-h-9 px-3 py-1.5 text-xs' : 'min-h-11 px-4 py-2 text-sm',
        'transition-[background-color,color,transform,box-shadow,opacity] duration-short ease-out',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none',
        BTN_VARIANTS[variant],
        className,
      ].join(' ')}
    >
      {children}
    </button>
  );
}

export function Field({ className = '', ...props }) {
  return (
    <input
      {...props}
      className={[
        'min-h-11 rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline',
        'placeholder:text-muted transition-[background-color,box-shadow] duration-short ease-out',
        'hover:bg-paper-3 focus:bg-paper-2',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus',
        'disabled:cursor-not-allowed disabled:opacity-60',
        className,
      ].join(' ')}
    />
  );
}

export function Select({ className = '', children, ...props }) {
  return (
    <select
      {...props}
      className={[
        'min-h-11 cursor-pointer rounded-sm bg-paper-2 px-2 py-1.5 text-sm text-ink shadow-hairline',
        'transition-[background-color] duration-short ease-out hover:bg-paper-3',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus',
        'disabled:cursor-not-allowed disabled:opacity-60',
        className,
      ].join(' ')}
    >
      {children}
    </select>
  );
}

export function Alert({ tone = 'danger', children }) {
  const tones = {
    danger: 'bg-danger-soft text-danger',
    warning: 'bg-warning-soft text-warning-strong',
    success: 'bg-accent-soft text-accent-strong',
  };
  return (
    <p className={`rounded-sm px-3 py-2 text-sm font-medium ${tones[tone]}`}>{children}</p>
  );
}

export function EmptyRow({ colSpan, children }) {
  return (
    <tr>
      <td colSpan={colSpan} className="px-4 py-10 text-center text-sm text-muted">
        {children}
      </td>
    </tr>
  );
}

// ── Modal dùng chung ─────────────────────────────────────────
// Backdrop mờ là glassmorphism "có mục đích" (overlay che nội dung).
// ESC để đóng, click nền ngoài để đóng, animate scale-in theo motion.md.

export function Modal({ open, onClose, icon, tone = 'accent', title, children, footer }) {
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const iconTones = {
    accent: 'bg-accent-soft text-accent-strong',
    danger: 'bg-danger-soft text-danger',
    warning: 'bg-warning-soft text-warning-strong',
  };

  return (
    <div
      className="animate-fade-in fixed inset-0 z-modal flex items-center justify-center bg-ink/50 p-4 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="animate-modal-in w-full max-w-md space-y-4 rounded-md bg-paper-2 p-6 shadow-card"
      >
        <div className="flex items-center gap-3">
          {icon && (
            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${iconTones[tone]}`}>
              {icon}
            </span>
          )}
          <h3 id={titleId} className="font-display text-lg font-bold">{title}</h3>
        </div>

        <div className="text-sm leading-relaxed text-ink-2">{children}</div>

        {footer && <div className="flex justify-end gap-3 pt-2">{footer}</div>}
      </div>
    </div>
  );
}

// ── Toast ────────────────────────────────────────────────────
// Một toast tại một thời điểm, tự tắt sau 3.5s. Dùng: 
//   const { toast, show } = useToast();  ...  <Toast toast={toast} />
export function useToast() {
  const [toast, setToast] = useState(null);
  const timer = useRef(null);

  const show = useCallback((message, tone = 'success') => {
    clearTimeout(timer.current);
    setToast({ message, tone, key: Date.now() });
    timer.current = setTimeout(() => setToast(null), 3500);
  }, []);

  useEffect(() => () => clearTimeout(timer.current), []);
  return { toast, show };
}

export function Toast({ toast, position = 'bottom' }) {
  if (!toast) return null;
  const tones = {
    success: 'bg-accent-strong text-accent-ink',
    danger: 'bg-danger text-paper-2',
    warning: 'bg-warning-strong text-paper-2',
  };
  const top = position === 'top';
  return (
    <div
      className={`pointer-events-none fixed inset-x-4 ${top ? 'top-4' : 'bottom-4'} z-toast flex justify-center sm:justify-end`}
    >
      <p
        key={toast.key}
        // Lỗi/cảnh báo dùng role="alert" để trình đọc màn hình đọc ngay
        role={toast.tone === 'success' ? 'status' : 'alert'}
        className={`${top ? 'animate-toast-in-top' : 'animate-toast-in'} max-w-sm rounded-md px-4 py-3 text-sm font-medium shadow-card ${tones[toast.tone]}`}
      >
        {toast.message}
      </p>
    </div>
  );
}