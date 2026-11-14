import { useState } from 'react';
import { AlertOctagon, AlertTriangle, ChevronDown, Info } from 'lucide-react';

// Hiển thị cảnh báo của Warning Engine (backend services/guardrails.py).
// Mức: DANGER (đỏ) - WARNING (vàng) - INFO (xanh), luôn nêu lý do cụ thể.
const LEVELS = {
  DANGER: {
    icon: AlertOctagon,
    box: 'border-danger/40 border-l-danger bg-danger-soft',
    text: 'text-danger',
    label: 'Nguy cơ',
  },
  WARNING: {
    icon: AlertTriangle,
    box: 'border-warning-strong/40 border-l-warning-strong bg-warning-soft',
    text: 'text-warning-strong',
    label: 'Lưu ý',
  },
  INFO: {
    icon: Info,
    box: 'border-info/40 border-l-info bg-info-soft',
    text: 'text-info',
    label: 'Thông tin',
  },
};

export const DISCLAIMER =
  'NutriSmart chỉ hỗ trợ tham khảo, không thay thế chẩn đoán hay tư vấn của bác sĩ.';

export default function WarningList({ warnings, limit = 4, compact = false, showDisclaimer = false }) {
  const [expanded, setExpanded] = useState(false);
  if (!warnings?.length) return null;

  const visible = expanded ? warnings : warnings.slice(0, limit);
  const hidden = warnings.length - visible.length;

  return (
    <div className={compact ? 'mt-1.5 space-y-1.5' : 'space-y-2'}>
      {visible.map((w, i) => {
        const lv = LEVELS[w.level] ?? LEVELS.INFO;
        const Icon = lv.icon;
        return (
          <aside
            key={`${w.code}-${i}`}
            role={w.level === 'DANGER' ? 'alert' : 'status'}
            className={[
              'flex gap-3 rounded-xl border border-l-4 shadow-whisper',
              compact ? 'p-2.5' : 'p-4',
              lv.box,
            ].join(' ')}
          >
            <Icon size={compact ? 16 : 20} className={`mt-0.5 shrink-0 ${lv.text}`} aria-hidden="true" />
            <div className="min-w-0 [overflow-wrap:anywhere]">
              <p className={`${compact ? 'text-xs' : 'text-sm'} font-medium text-ink`}>
                <span className={`font-semibold ${lv.text}`}>{lv.label}: </span>
                {w.message}
              </p>
              {w.context && (
                <p className="mt-1 text-xs text-ink-2">Xuất hiện ở: {w.context}</p>
              )}
              {w.source && !compact && (
                <p className="mt-1 text-xs text-ink-2">Nguồn tham khảo: {w.source}</p>
              )}
            </div>
          </aside>
        );
      })}

      {(hidden > 0 || expanded) && warnings.length > limit && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="inline-flex items-center gap-1 text-xs font-semibold text-ink-2 hover:text-ink"
          aria-expanded={expanded}
        >
          <ChevronDown size={14} className={expanded ? 'rotate-180 transition-transform' : 'transition-transform'} />
          {expanded ? 'Thu gọn' : `Xem thêm ${hidden} cảnh báo`}
        </button>
      )}

      {showDisclaimer && <p className="text-xs text-ink-2">{DISCLAIMER}</p>}
    </div>
  );
}
