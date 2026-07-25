import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

// Ô nhập mật khẩu có nút hiện/ẩn. Nhận value/onChange + các prop input khác.
export default function PasswordInput({ value, onChange, className = '', ...props }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        className={`${className} pr-11`}
        {...props}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
        aria-pressed={show}
        className={[
          'absolute inset-y-0 right-0 flex min-w-11 items-center justify-center rounded-sm px-3',
          'text-muted transition-colors duration-micro ease-out',
          'hover:text-accent-strong active:text-accent-strong',
          'focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus',
        ].join(' ')}
      >
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}