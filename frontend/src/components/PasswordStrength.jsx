import { Check, Circle } from 'lucide-react';
import { isCommonPassword, passwordChecks, passwordStrength } from '../lib/password.js';

const LEVELS = [
  null,
  { label: 'Yếu', bar: 'bg-danger', text: 'text-danger' },
  { label: 'Trung bình', bar: 'bg-warning', text: 'text-warning-strong' },
  { label: 'Mạnh', bar: 'bg-accent-strong', text: 'text-accent-strong' },
];

const RULES = [
  ['length', 'Tối thiểu 8 ký tự'],
  ['mixedCase', 'Chữ hoa & chữ thường'],
  ['digit', 'Có ít nhất 1 chữ số'],
  ['special', 'Có ít nhất 1 ký tự đặc biệt'],
];

// Thanh đo độ mạnh + checklist 4 tiêu chí hiển thị dưới ô mật khẩu đăng ký.
export default function PasswordStrength({ password }) {
  const checks = passwordChecks(password);
  const level = passwordStrength(password);
  const info = LEVELS[level];

  return (
    <div className="mt-2 space-y-2" aria-live="polite">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1" aria-hidden="true">
          {[1, 2, 3].map((i) => (
            <span
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors duration-short ${
                level >= i ? info.bar : 'bg-paper-3'
              }`}
            />
          ))}
        </div>
        <span className={`w-20 text-right text-xs font-semibold ${info ? info.text : 'text-muted'}`}>
          {info ? info.label : 'Độ mạnh'}
        </span>
      </div>

      <ul className="grid grid-cols-1 gap-1 text-xs sm:grid-cols-2">
        {RULES.map(([key, label]) => (
          <li key={key} className={`flex items-center gap-1.5 ${checks[key] ? 'text-accent-strong' : 'text-muted'}`}>
            {checks[key]
              ? <Check size={12} strokeWidth={3} aria-hidden="true" />
              : <Circle size={10} aria-hidden="true" />}
            <span>{label}</span>
            <span className="sr-only">{checks[key] ? '(đạt)' : '(chưa đạt)'}</span>
          </li>
        ))}
      </ul>

      {password && isCommonPassword(password) && (
        <p className="text-xs font-medium text-danger">Mật khẩu này quá phổ biến, vui lòng chọn mật khẩu khác.</p>
      )}
      {/\s/.test(password) && (
        <p className="text-xs font-medium text-danger">Mật khẩu không được chứa khoảng trắng.</p>
      )}
    </div>
  );
}
