import { useEffect, useState } from 'react';
import { RefreshCw, Sparkles, Footprints, Sunrise, Sun, Moon, Cookie, UtensilsCrossed, Check } from 'lucide-react';
import { api } from '../lib/api.js';

// Icon theo loại bữa — fallback UtensilsCrossed cho type lạ từ backend
const MEAL_ICONS = [
  [/sáng|breakfast/i, Sunrise],
  [/trưa|lunch/i, Sun],
  [/tối|dinner/i, Moon],
  [/phụ|snack|xế/i, Cookie],
];
function mealIcon(type = '') {
  return MEAL_ICONS.find(([re]) => re.test(type))?.[1] ?? UtensilsCrossed;
}

export default function Plan() {
  const [plan, setPlan] = useState(null);
  const [err, setErr] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeDay, setActiveDay] = useState(0);
  // Trạng thái hoàn thành — UI-only (api.js chưa có endpoint lưu), key: "day-mealIdx" / "day-ex"
  const [done, setDone] = useState({});

  useEffect(() => {
    fetchPlan();
  }, []);

  const fetchPlan = () => {
    api.activePlan().then(setPlan).catch((e) => setErr(e.message));
  };

  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    setErr(null);
    try {
      const newPlan = await api.generatePlan();
      setPlan(newPlan);
      setActiveDay(0);
      setDone({});
    } catch (e) {
      setErr('Có lỗi khi tạo lộ trình: ' + e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const toggle = (key) => setDone((d) => ({ ...d, [key]: !d[key] }));

  if (err && !plan) {
    return (
      <div className="mx-auto flex max-w-4xl flex-col items-center justify-center gap-4 rounded-md bg-paper-2 p-8 text-center shadow-hairline">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
          <Sparkles size={26} strokeWidth={2} />
        </span>
        <h2 className="font-display text-xl font-bold">Chưa có lộ trình nào</h2>
        <p className="text-sm text-muted">Hệ thống chưa tạo lộ trình dinh dưỡng cho bạn.</p>
        <GenerateButton primary loading={isGenerating} onClick={handleGeneratePlan}>
          Tạo lộ trình cá nhân hóa mới
        </GenerateButton>
        {err && !err.includes('HTTP 404') && (
          <p className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger">{err}</p>
        )}
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="max-w-4xl space-y-4" aria-busy="true">
        <div className="h-8 w-56 animate-pulse rounded-sm bg-paper-3" />
        <div className="h-24 animate-pulse rounded-md bg-paper-3" />
        <div className="h-64 animate-pulse rounded-md bg-paper-3" />
      </div>
    );
  }

  const days = plan.content?.days ?? [];
  const day = days[activeDay];
  const dayDoneCount = (d, di) =>
    (d.meals ?? []).filter((_, j) => done[`${di}-${j}`]).length +
    (d.exercise && done[`${di}-ex`] ? 1 : 0);
  const dayTotal = (d) => (d.meals?.length ?? 0) + (d.exercise ? 1 : 0);

  return (
    <div className="max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold tracking-tight">Lộ trình cá nhân hóa</h1>
        <GenerateButton loading={isGenerating} onClick={handleGeneratePlan}>
          Tạo lộ trình mới
        </GenerateButton>
      </header>

      {err && (
        <p className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger">{err}</p>
      )}

      {/* Thẻ meta */}
      <div className="rounded-md bg-paper-2 p-5 shadow-hairline">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="font-display font-semibold">Phiên bản {plan.version}</h2>
          <span className="text-sm text-muted">{plan.start_date} → {plan.end_date}</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          <span className="rounded-full bg-accent-soft px-3 py-1 font-medium text-accent-strong">{plan.goal}</span>
          <span className="rounded-full bg-paper-3 px-3 py-1 text-ink-2 [font-variant-numeric:tabular-nums]">
            {plan.daily_kcal_target} kcal/ngày
          </span>
          {plan.bmi && (
            <span className="rounded-full bg-paper-3 px-3 py-1 text-ink-2 [font-variant-numeric:tabular-nums]">
              BMI {plan.bmi}
            </span>
          )}
        </div>
      </div>

      {/* Tab ngày — button thường, không radio-hack nên không scroll-jump */}
      {days.length > 0 && (
        <>
          <div role="tablist" aria-label="Chọn ngày" className="flex gap-2 overflow-x-auto pb-1">
            {days.map((d, i) => {
              const active = i === activeDay;
              const doneN = dayDoneCount(d, i);
              const total = dayTotal(d);
              return (
                <button
                  key={i}
                  role="tab"
                  aria-selected={active}
                  onClick={() => setActiveDay(i)}
                  className={[
                    'flex min-h-11 shrink-0 flex-col items-center rounded-md px-4 py-2',
                    'transition-[background-color,color,box-shadow] duration-short ease-out',
                    active
                      ? 'bg-accent-strong text-accent-ink shadow-whisper'
                      : 'bg-paper-2 text-ink-2 shadow-hairline hover:bg-paper-3 active:bg-paper-3',
                  ].join(' ')}
                >
                  <span className="text-sm font-semibold">Ngày {i + 1}</span>
                  <span className={`text-xs [font-variant-numeric:tabular-nums] ${active ? 'text-accent-ink/80' : 'text-muted'}`}>
                    {doneN}/{total} xong
                  </span>
                </button>
              );
            })}
          </div>

          {/* Timeline bữa ăn của ngày đang chọn */}
          {day && (
            <section className="rounded-md bg-paper-2 p-5 shadow-hairline">
              <ol className="relative space-y-1 border-l-2 border-rule-2 pl-5 marker:content-none">
                {day.meals?.map((m, j) => {
                  const key = `${activeDay}-${j}`;
                  const checked = !!done[key];
                  const Icon = mealIcon(m.type);
                  return (
                    <TimelineItem
                      key={j}
                      icon={Icon}
                      checked={checked}
                      onToggle={() => toggle(key)}
                      title={m.name}
                      tag={m.type}
                      trailing={`${m.kcal} kcal`}
                    />
                  );
                })}
                {day.exercise && (
                  <TimelineItem
                    icon={Footprints}
                    checked={!!done[`${activeDay}-ex`]}
                    onToggle={() => toggle(`${activeDay}-ex`)}
                    title={day.exercise}
                    tag="Vận động"
                    exercise
                  />
                )}
              </ol>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function TimelineItem({ icon: Icon, checked, onToggle, title, tag, trailing, exercise }) {
  return (
    <li className="relative">
      {/* Chấm mốc trên đường timeline */}
      <span
        aria-hidden="true"
        className={[
          'absolute -left-[27px] top-4 h-2.5 w-2.5 rounded-full transition-colors duration-short ease-out',
          checked ? 'bg-accent' : 'bg-rule',
        ].join(' ')}
      />
      <label
        className={[
          'group flex cursor-pointer items-center gap-3 rounded-md p-3',
          'transition-[background-color] duration-short ease-out hover:bg-paper-3',
          'has-[:focus-visible]:bg-paper-3',
        ].join(' ')}
      >
        {/* Checkbox custom — input thật giữ accessibility */}
        <span className="relative flex h-6 w-6 shrink-0 items-center justify-center">
          <input
            type="checkbox"
            checked={checked}
            onChange={onToggle}
            className="peer absolute inset-0 h-full w-full cursor-pointer opacity-0"
          />
          <span
            aria-hidden="true"
            className={[
              'flex h-5 w-5 items-center justify-center rounded-sm border-2',
              'transition-[background-color,border-color,transform] duration-micro ease-out',
              'peer-active:scale-90',
              'peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus',
              checked
                ? 'border-accent-strong bg-accent-strong text-accent-ink'
                : 'border-rule bg-paper-2 group-hover:border-accent',
            ].join(' ')}
          >
            {checked && <Check size={13} strokeWidth={3.2} />}
          </span>
        </span>

        <span
          className={[
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors duration-short ease-out',
            exercise ? 'bg-info-soft text-info' : 'bg-accent-soft text-accent-strong',
            checked && 'opacity-60',
          ].filter(Boolean).join(' ')}
        >
          <Icon size={17} strokeWidth={2.2} />
        </span>

        <span className="min-w-0 flex-1">
          <span className="block text-xs font-medium uppercase tracking-wide text-muted">{tag}</span>
          <span
            className={[
              'block truncate text-sm font-medium transition-colors duration-short ease-out',
              checked ? 'text-muted line-through decoration-rule' : 'text-ink',
            ].join(' ')}
          >
            {title}
          </span>
        </span>

        {trailing && (
          <span className={`shrink-0 text-sm [font-variant-numeric:tabular-nums] ${checked ? 'text-muted' : 'text-ink-2'}`}>
            {trailing}
          </span>
        )}
      </label>
    </li>
  );
}

function GenerateButton({ primary, loading, onClick, children }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className={[
        'flex min-h-11 items-center gap-2 rounded-md px-4 py-2 text-sm font-medium',
        'transition-[background-color,color,transform,box-shadow] duration-short ease-out',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
        'disabled:cursor-not-allowed disabled:opacity-60',
        primary
          ? 'bg-accent-strong text-accent-ink shadow-whisper hover:-translate-y-px hover:shadow-card active:translate-y-0 active:shadow-whisper'
          : 'bg-paper-2 text-accent-strong shadow-hairline hover:bg-accent-soft active:bg-accent-soft',
      ].join(' ')}
    >
      {loading ? (
        <>
          <RefreshCw size={16} className="animate-spin" />
          AI đang tạo lộ trình (15–30s)…
        </>
      ) : (
        <>
          <RefreshCw size={16} />
          {children}
        </>
      )}
    </button>
  );
}