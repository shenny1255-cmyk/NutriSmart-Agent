import { useEffect, useRef, useState } from 'react';
import {
  RefreshCw, Sparkles, Footprints, Sunrise, Sun, Moon, Cookie, UtensilsCrossed, Check,
  ClipboardCheck, History, CalendarClock, ShieldAlert, CheckCircle2,
} from 'lucide-react';
import { api } from '../lib/api.js';

const PLAN_JOB_KEY = 'nutrismart_plan_job';

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
  const [checkinHistory, setCheckinHistory] = useState([]);
  const generationRun = useRef(0);

  useEffect(() => {
    fetchPlan();
    fetchCheckinHistory();
    const runId = ++generationRun.current;
    const jobId = window.localStorage.getItem(PLAN_JOB_KEY);
    if (jobId) waitForPlan(jobId, runId);
    return () => {
      if (generationRun.current === runId) generationRun.current += 1;
    };
  }, []);

  useEffect(() => {
    if (plan?.current_checkin?.feedback_status !== 'PENDING') return undefined;
    const timer = window.setInterval(() => {
      api.activePlan().then(setPlan).catch(() => {});
    }, 15000);
    return () => window.clearInterval(timer);
  }, [plan?.current_checkin?.feedback_status]);

  const fetchPlan = () => {
    api.activePlan().then(setPlan).catch((e) => setErr(e.message));
  };

  const fetchCheckinHistory = () => {
    api.checkinHistory().then(setCheckinHistory).catch(() => setCheckinHistory([]));
  };

  const waitForPlan = async (jobId, runId) => {
    setIsGenerating(true);
    try {
      let status = { status: 'QUEUED', job_id: jobId };
      while (status.status === 'QUEUED' || status.status === 'RUNNING') {
        await new Promise((resolve) => window.setTimeout(resolve, 3000));
        if (generationRun.current !== runId) return;
        status = await api.generatePlanStatus(jobId);
      }
      if (generationRun.current !== runId) return;
      if (status.status === 'FAILED') {
        window.localStorage.removeItem(PLAN_JOB_KEY);
        throw new Error(status.error);
      }
      if (status.status !== 'DONE') {
        window.localStorage.removeItem(PLAN_JOB_KEY);
        throw new Error('Trạng thái tạo lộ trình không hợp lệ');
      }
      const newPlan = await api.activePlan();
      if (generationRun.current !== runId) return;
      window.localStorage.removeItem(PLAN_JOB_KEY);
      setPlan(newPlan);
      setActiveDay(0);
      setDone({});
      setErr(null);
    } catch (e) {
      if (generationRun.current !== runId) return;
      if (e.status === 404) window.localStorage.removeItem(PLAN_JOB_KEY);
      setErr('Có lỗi khi tạo lộ trình: ' + e.message);
    } finally {
      if (generationRun.current === runId) setIsGenerating(false);
    }
  };

  const handleGeneratePlan = async () => {
    const runId = ++generationRun.current;
    setErr(null);
    setIsGenerating(true);
    try {
      const job = await api.generatePlan();
      window.localStorage.setItem(PLAN_JOB_KEY, job.job_id);
      await waitForPlan(job.job_id, runId);
    } catch (e) {
      if (generationRun.current === runId) {
        setErr('Có lỗi khi xếp tác vụ tạo lộ trình: ' + e.message);
        setIsGenerating(false);
      }
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

      <CheckinPanel
        checkin={plan.current_checkin}
        onChanged={() => {
          fetchPlan();
          fetchCheckinHistory();
        }}
        onError={setErr}
      />

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

      {checkinHistory.length > 0 && <CheckinHistory items={checkinHistory} />}
    </div>
  );
}

const RECOMMENDATION_LABELS = {
  NEEDS_REVIEW: 'Phát hiện thay đổi bất thường',
  CONTINUE_AND_TRACK: 'Tiếp tục và ghi nhật ký',
  IMPROVE_ADHERENCE: 'Cải thiện mức tuân thủ',
  CONTINUE: 'Tiếp tục lộ trình',
  CONTINUE_AND_MONITOR: 'Theo dõi thêm một kỳ',
  ADJUST_PLAN: 'Có thể điều chỉnh lộ trình',
};

const SAFETY_LABELS = {
  RAPID_WEIGHT_CHANGE: 'Cân nặng thay đổi nhanh',
  LOW_ENERGY: 'Mức năng lượng thấp',
  HIGH_HUNGER: 'Mức đói cao',
  POOR_SLEEP: 'Chất lượng ngủ thấp',
  MEDICAL_REVIEW: 'Nên trao đổi với chuyên gia y tế trước khi thay đổi lộ trình',
};

const ADHERENCE_OPTIONS = [
  { value: 10, max: 20, range: '0–20%', label: 'Hầu như không thực hiện' },
  { value: 30, max: 40, range: '21–40%', label: 'Thực hiện ít' },
  { value: 50, max: 60, range: '41–60%', label: 'Thực hiện khoảng một nửa' },
  { value: 70, max: 80, range: '61–80%', label: 'Thực hiện phần lớn' },
  { value: 90, max: 100, range: '81–100%', label: 'Gần như thực hiện đầy đủ' },
];

function adherenceLabel(value) {
  const percent = Number(value);
  return ADHERENCE_OPTIONS.find((option) => percent <= option.max)?.label ?? 'Chưa xác định';
}

function adherenceValue(value) {
  const percent = Number(value);
  if (percent <= 20) return 10;
  if (percent <= 40) return 30;
  if (percent <= 60) return 50;
  if (percent <= 80) return 70;
  return 90;
}

function CheckinPanel({ checkin, onChanged, onError }) {
  const [busy, setBusy] = useState(false);
  const canSimulate = localStorage.getItem('role') === 'ADMIN';
  const draftKey = checkin ? `nutrismart_checkin_draft_${checkin.id}` : null;
  const [form, setForm] = useState({
    actual_weight_kg: '', actual_waist_cm: '', actual_activity_level: 3,
    adherence_pct: 70, energy_level: 3, hunger_level: 3, sleep_quality: 3, notes: '',
  });

  useEffect(() => {
    if (!draftKey || checkin.status !== 'OPEN') return;
    try {
      const saved = JSON.parse(sessionStorage.getItem(draftKey));
      if (saved) setForm((current) => ({
        ...current, ...saved, adherence_pct: adherenceValue(saved.adherence_pct ?? 70),
      }));
      else if (checkin.actual_weight_kg != null) setForm((current) => ({
        ...current,
        actual_weight_kg: String(checkin.actual_weight_kg),
        actual_waist_cm: checkin.actual_waist_cm == null ? '' : String(checkin.actual_waist_cm),
        actual_activity_level: checkin.actual_activity_level ?? 3,
        adherence_pct: adherenceValue(checkin.adherence_pct ?? 70),
        energy_level: checkin.energy_level ?? 3,
        hunger_level: checkin.hunger_level ?? 3,
        sleep_quality: checkin.sleep_quality ?? 3,
        notes: checkin.notes ?? '',
      }));
    } catch { /* Draft hỏng thì dùng form mặc định. */ }
  }, [draftKey, checkin?.status]);

  useEffect(() => {
    if (!draftKey || checkin.status !== 'OPEN') return;
    sessionStorage.setItem(draftKey, JSON.stringify(form));
  }, [draftKey, form, checkin?.status]);

  if (!checkin) return null;

  const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const weight = Number(form.actual_weight_kg);
  const waist = Number(form.actual_waist_cm);
  const weightValid = form.actual_weight_kg !== '' && weight >= 20 && weight <= 300;
  const weightChangeValid = !weightValid
    || Math.abs(weight - Number(checkin.baseline_weight_kg)) / Number(checkin.baseline_weight_kg) <= 0.20;
  const waistValid = form.actual_waist_cm === '' || (waist >= 30 && waist <= 250);
  const canSubmit = weightValid && weightChangeValid && waistValid && form.notes.length <= 1000;
  const isDue = checkin.display_status === 'DUE';
  const daysLeft = Math.max(0, Math.ceil(
    (new Date(`${checkin.due_date}T00:00:00`) - new Date()) / 86400000,
  ));
  const elapsed = Math.min(14, Math.max(0, 14 - daysLeft));

  async function submit(e) {
    e.preventDefault();
    if (!canSubmit || !isDue) return;
    setBusy(true);
    onError(null);
    try {
      await api.submitCheckin(checkin.id, {
        actual_weight_kg: weight,
        actual_waist_cm: form.actual_waist_cm === '' ? null : waist,
        actual_activity_level: Number(form.actual_activity_level),
        adherence_pct: Number(form.adherence_pct),
        energy_level: Number(form.energy_level),
        hunger_level: Number(form.hunger_level),
        sleep_quality: Number(form.sleep_quality),
        notes: form.notes.trim() || null,
      });
      sessionStorage.removeItem(draftKey);
      onChanged();
    } catch (error) {
      onError(typeof error.detail === 'string' ? error.detail : 'Không gửi được báo cáo tiến độ.');
    } finally {
      setBusy(false);
    }
  }

  async function decide(action) {
    setBusy(true);
    onError(null);
    try {
      await api.decideCheckin(checkin.id, action);
      onChanged();
    } catch (error) {
      onError(typeof error.detail === 'string' ? error.detail : 'Không áp dụng được quyết định.');
    } finally {
      setBusy(false);
    }
  }

  async function reopen() {
    setBusy(true);
    onError(null);
    try {
      sessionStorage.removeItem(draftKey);
      await api.reopenCheckin(checkin.id);
      onChanged();
    } catch (error) {
      onError(typeof error.detail === 'string' ? error.detail : 'Không thể mở lại báo cáo để sửa.');
    } finally {
      setBusy(false);
    }
  }

  async function simulateDue() {
    if (!window.confirm('Chuyển kỳ hiện tại sang ngày check-in để thử nghiệm? Nhật ký hiện có vẫn được giữ nguyên.')) return;
    setBusy(true);
    onError(null);
    try {
      await api.simulateCheckinDue();
      onChanged();
    } catch (error) {
      onError(typeof error.detail === 'string' ? error.detail : 'Không thể mô phỏng ngày check-in.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4 rounded-md bg-paper-2 p-5 shadow-hairline">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-info-soft text-info">
          <CalendarClock size={19} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display font-semibold">Báo cáo tiến độ 14 ngày · Kỳ {checkin.period_number}</h2>
          <p className="text-sm text-muted">{checkin.start_date} → {checkin.period_end}</p>
        </div>
        <span className="rounded-full bg-paper-3 px-3 py-1 text-xs font-semibold text-ink-2">
          {checkin.display_status === 'UPCOMING' ? `Còn ${daysLeft} ngày` :
            checkin.display_status === 'DUE' ? 'Đến hạn' :
              checkin.display_status === 'OVERDUE' ? 'Quá hạn' :
                checkin.display_status === 'COMPLETED' ? 'Đã hoàn tất' : checkin.display_status}
        </span>
      </div>

      {checkin.status === 'OPEN' && (
        <div className="h-1.5 overflow-hidden rounded-full bg-paper-3">
          <div className="h-full rounded-full bg-accent" style={{ width: `${(elapsed / 14) * 100}%` }} />
        </div>
      )}

      {checkin.display_status === 'UPCOMING' && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted">
            Form sẽ mở vào ngày {checkin.due_date}. Hãy ghi nhật ký hằng ngày để kết quả đủ tin cậy.
          </p>
          {canSimulate && (
            <button type="button" onClick={simulateDue} disabled={busy}
              className="min-h-10 rounded-md border border-dashed border-info px-3 py-2 text-sm font-semibold text-info disabled:opacity-50">
              {busy ? 'Đang mô phỏng…' : 'Thử nghiệm · Mở check-in ngay'}
            </button>
          )}
        </div>
      )}

      {isDue && checkin.status === 'OPEN' && (
        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <CheckinField label="Cân nặng hiện tại (kg)" error={form.actual_weight_kg !== '' && !weightValid
              ? 'Nhập từ 20 đến 300 kg'
              : !weightChangeValid ? `Chênh lệch quá 20% so với đầu kỳ ${checkin.baseline_weight_kg} kg. Vui lòng kiểm tra lại.` : null}>
              <input type="number" min="20" max="300" step="0.1" required value={form.actual_weight_kg}
                onChange={(e) => set('actual_weight_kg', e.target.value)}
                className={`min-h-11 rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus ${form.actual_weight_kg !== '' && !weightValid ? 'outline outline-2 outline-danger' : ''}`} />
            </CheckinField>
            <CheckinField label="Vòng eo (cm) · không bắt buộc" error={!waistValid ? 'Nhập từ 30 đến 250 cm' : null}>
              <input type="number" min="30" max="250" step="0.1" value={form.actual_waist_cm}
                onChange={(e) => set('actual_waist_cm', e.target.value)}
                className={`min-h-11 rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus ${!waistValid ? 'outline outline-2 outline-danger' : ''}`} />
            </CheckinField>
            <CheckinField label="Mức vận động thực tế">
              <select value={form.actual_activity_level} onChange={(e) => set('actual_activity_level', e.target.value)} className="min-h-11 rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus">
                <option value="1">1 · Ít vận động</option><option value="2">2 · Vận động nhẹ</option>
                <option value="3">3 · Vận động vừa</option><option value="4">4 · Vận động nhiều</option>
                <option value="5">5 · Rất năng động</option>
              </select>
            </CheckinField>
            <fieldset className="sm:col-span-2">
              <legend className="mb-2 text-sm font-medium text-ink-2">
                Bạn đã thực hiện lộ trình ở mức nào?
              </legend>
              <div className="grid gap-2 sm:grid-cols-5">
                {ADHERENCE_OPTIONS.map((option) => (
                  <label key={option.value} className="cursor-pointer">
                    <input type="radio" name="adherence" value={option.value} className="peer sr-only"
                      checked={Number(form.adherence_pct) === option.value}
                      onChange={() => set('adherence_pct', option.value)} />
                    <span className="flex h-full min-h-20 flex-col justify-center rounded-sm bg-paper-3 px-2 py-2 text-center text-xs text-ink-2 shadow-hairline peer-checked:bg-accent-soft peer-checked:text-accent-strong peer-checked:outline peer-checked:outline-2 peer-checked:outline-accent-strong peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-focus">
                      <strong className="mb-1">{option.range}</strong>
                      {option.label}
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <RatingField label="Mức năng lượng" value={form.energy_level} onChange={(v) => set('energy_level', v)} />
            <RatingField label="Mức đói" value={form.hunger_level} onChange={(v) => set('hunger_level', v)} />
            <RatingField label="Chất lượng giấc ngủ" value={form.sleep_quality} onChange={(v) => set('sleep_quality', v)} />
          </div>

          <label className="block text-sm font-medium text-ink-2">
            Ghi chú · không bắt buộc
            <textarea value={form.notes} maxLength={1000} rows={3} onChange={(e) => set('notes', e.target.value)}
              className="mt-1 w-full rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus" />
            <span className="mt-1 block text-right text-xs text-muted">{form.notes.length}/1000</span>
          </label>

          <button type="submit" disabled={!canSubmit || busy}
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-accent-strong px-4 py-2 text-sm font-semibold text-accent-ink disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? <RefreshCw size={16} className="animate-spin" /> : <ClipboardCheck size={16} />}
            {busy ? 'Đang gửi báo cáo…' : 'Gửi báo cáo tiến độ'}
          </button>
        </form>
      )}

      {checkin.status === 'COMPLETED' && <CheckinResult checkin={checkin} busy={busy} onDecide={decide} onReopen={reopen} />}
      {checkin.status === 'MISSED' && <p className="text-sm text-danger">Kỳ này đã quá thời gian check-in.</p>}
      {checkin.status === 'CANCELLED' && <p className="text-sm text-muted">Kỳ này đã bị hủy do lộ trình thay đổi.</p>}
    </section>
  );
}

function CheckinField({ label, error, children }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium text-ink-2">
      {label}
      {children}
      {error && <span className="text-xs font-medium text-danger">{error}</span>}
    </label>
  );
}

function RatingField({ label, value, onChange }) {
  return (
    <fieldset>
      <legend className="mb-1 text-sm font-medium text-ink-2">{label}</legend>
      <div className="flex gap-1" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((number) => (
          <label key={number} className="flex-1">
            <input type="radio" className="peer sr-only" name={label} value={number}
              checked={Number(value) === number} onChange={() => onChange(number)} />
            <span className="flex min-h-10 cursor-pointer items-center justify-center rounded-sm bg-paper-3 text-sm text-ink-2 shadow-hairline peer-checked:bg-accent-strong peer-checked:text-accent-ink peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-focus">
              {number}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function CheckinResult({ checkin, busy, onDecide, onReopen }) {
  const hasSafety = checkin.safety_flags?.length > 0;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <ResultMetric label="Đầu kỳ" value={`${checkin.baseline_weight_kg} kg`} />
        <ResultMetric label="Khoảng kỳ vọng" value={`${checkin.expected_weight_min_kg}–${checkin.expected_weight_max_kg} kg`} />
        <ResultMetric label="Thực tế" value={`${checkin.actual_weight_kg} kg`} />
      </div>
      <div className={`rounded-md p-4 ${hasSafety ? 'bg-warning-soft' : 'bg-accent-soft'}`}>
        <p className={`flex items-center gap-2 font-semibold ${hasSafety ? 'text-warning-strong' : 'text-accent-strong'}`}>
          {hasSafety ? <ShieldAlert size={17} /> : <CheckCircle2 size={17} />}
          {RECOMMENDATION_LABELS[checkin.recommendation] ?? checkin.recommendation}
        </p>
        <p className="mt-1 text-sm text-ink-2">{checkin.recommendation_reason}</p>
      </div>
      {hasSafety && (
        <ul className="list-inside list-disc text-sm text-warning-strong">
          {checkin.safety_flags.map((flag) => <li key={flag}>{SAFETY_LABELS[flag] ?? flag}</li>)}
        </ul>
      )}
      <p className="rounded-md bg-paper-3 p-4 text-sm leading-relaxed text-ink-2">
        {checkin.ai_feedback || (checkin.feedback_status === 'PENDING'
          ? 'Đang tạo nhận xét cá nhân hóa…'
          : 'Hãy tiếp tục theo dõi và ghi nhật ký đều đặn.')}
      </p>
      {!checkin.decision && (
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" disabled={busy} onClick={onReopen}
            className="min-h-11 rounded-md border border-ink-3 px-4 py-2 text-sm font-medium text-ink-2 disabled:opacity-50">
            Sửa số liệu báo cáo
          </button>
          <button type="button" disabled={busy} onClick={() => onDecide('CONTINUE')}
            className="min-h-11 rounded-md bg-paper-3 px-4 py-2 text-sm font-medium text-ink-2 shadow-hairline disabled:opacity-50">
            Tiếp tục lộ trình hiện tại
          </button>
          {checkin.recommendation === 'ADJUST_PLAN' && (
            <button type="button" disabled={busy} onClick={() => onDecide('APPLY_ADJUSTMENT')}
              className="min-h-11 rounded-md bg-accent-strong px-4 py-2 text-sm font-semibold text-accent-ink disabled:opacity-50">
              Áp dụng mức {checkin.proposed_kcal_target} kcal
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ResultMetric({ label, value }) {
  return <div className="rounded-md bg-paper-3 p-3"><p className="text-xs text-muted">{label}</p><p className="font-semibold text-ink">{value}</p></div>;
}

function CheckinHistory({ items }) {
  return (
    <section className="rounded-md bg-paper-2 p-5 shadow-hairline">
      <h2 className="mb-3 flex items-center gap-2 font-display font-semibold"><History size={17} className="text-muted" />Lịch sử check-in</h2>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="space-y-2 rounded-md bg-paper-3 p-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span><strong>Kỳ {item.period_number}</strong> · {item.start_date} → {item.period_end}</span>
              <span className="text-ink-2">{item.status === 'COMPLETED' ? RECOMMENDATION_LABELS[item.recommendation] : 'Đã bỏ lỡ'}</span>
            </div>
            {item.status === 'COMPLETED' && (
              <>
                <p className="text-xs text-muted">
                  {item.baseline_weight_kg} kg → {item.actual_weight_kg} kg · {adherenceLabel(item.adherence_pct)} · {item.meal_log_days} ngày nhật ký
                </p>
                {item.ai_feedback && <p className="text-sm leading-relaxed text-ink-2">{item.ai_feedback}</p>}
              </>
            )}
          </div>
        ))}
      </div>
    </section>
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
          AI đang tạo lộ trình, bạn có thể chờ hoặc quay lại sau…
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
