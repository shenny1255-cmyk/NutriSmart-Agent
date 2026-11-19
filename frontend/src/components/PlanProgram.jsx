import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import confetti from 'canvas-confetti';
import {
  ArrowRight, CalendarClock, Camera, Check, CheckCircle2, Cookie, Footprints,
  HelpCircle, Lightbulb, LockKeyhole, Moon, RefreshCw, RotateCcw, Save, Sun,
  Sunrise, UserCheck, UtensilsCrossed,
} from 'lucide-react';
import { api } from '../lib/api.js';
import WarningList from './WarningList.jsx';
import { Btn, Field, Modal, Select, Toast, useToast } from './ui.jsx';

function fireConfetti() {
  try {
    confetti({
      particleCount: 80,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#10B981', '#059669', '#34D399', '#FBBF24', '#F59E0B', '#3B82F6'],
    });
  } catch {
    // Ignore if not supported in environment
  }
}

const PLAN_JOB_KEY = 'nutrismart_plan_job';
const ITEM_KEYS = ['meal:0', 'meal:1', 'meal:2', 'exercise'];
const MEAL_ICONS = [
  [/sáng|breakfast/i, Sunrise],
  [/trưa|lunch/i, Sun],
  [/tối|dinner/i, Moon],
  [/phụ|snack|xế/i, Cookie],
];

function parseDate(value) {
  return new Date(`${value}T00:00:00`);
}

function toDateKey(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function todayKey() {
  return toDateKey(new Date());
}

function datesInPeriod(checkin) {
  if (!checkin) return [];
  const result = [];
  const cursor = parseDate(checkin.start_date);
  const end = parseDate(checkin.period_end);
  while (cursor <= end) {
    result.push(toDateKey(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return result;
}

function dateLabel(value) {
  if (value === todayKey()) return 'Hôm nay';
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit' }).format(parseDate(value));
}

function fullDateLabel(value) {
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  }).format(parseDate(value));
}

function progressLabel(status, count, total) {
  if (status === 'COMPLETED') {
    return count === total && total > 0
      ? `Hoàn thành ${count}/${total}`
      : `Đã ghi nhận ${count}/${total}`;
  }
  return `${count}/${total} mục`;
}

function mealIcon(type = '') {
  return MEAL_ICONS.find(([pattern]) => pattern.test(type))?.[1] ?? UtensilsCrossed;
}

function exerciseData(value) {
  if (value && typeof value === 'object') {
    const duration = Number(value.duration_min || 0);
    let calories = Number(value.calories_kcal || 0);
    if (!calories && duration) {
      calories = Math.round((3.5 * 3.5 * 60 / 200) * duration);
    }
    return {
      name: value.name || 'Vận động theo lộ trình',
      duration,
      calories,
    };
  }
  const text = String(value || '').trim();
  if (!text) return { name: 'Vận động theo lộ trình', duration: 0, calories: 0 };
  const durationMatch = text.match(/(\d+(?:[.,]\d+)?)\s*(?:phút|phut|minutes?|mins?)/i);
  const caloriesMatch = text.match(/(\d+(?:[.,]\d+)?)\s*kcal/i);
  const metricStarts = [durationMatch?.index, caloriesMatch?.index]
    .filter((index) => Number.isInteger(index));
  const name = metricStarts.length
    ? text.slice(0, Math.min(...metricStarts)).replace(/[\s\---·,:]+$/u, '')
    : text;
  const duration = durationMatch ? Math.trunc(Number(durationMatch[1].replace(',', '.'))) : 0;
  let calories = caloriesMatch ? Number(caloriesMatch[1].replace(',', '.')) : 0;
  if (!calories && duration) {
    calories = Math.round((3.5 * 3.5 * 60 / 200) * duration);
  }
  return {
    name: name || 'Vận động theo lộ trình',
    duration,
    calories,
  };
}

export default function PlanProgram({ CheckinPanel, CheckinHistory }) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [history, setHistory] = useState([]);
  const [activeDate, setActiveDate] = useState(null);
  const [checkedByDate, setCheckedByDate] = useState({});
  const [diaryByDate, setDiaryByDate] = useState({});
  const [statusByDate, setStatusByDate] = useState({});
  const [progressBusy, setProgressBusy] = useState(false);
  const [missingItems, setMissingItems] = useState(null);
  const [generatorOpen, setGeneratorOpen] = useState(false);
  const [generatorBusy, setGeneratorBusy] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [extendMonths, setExtendMonths] = useState(1);
  const [extending, setExtending] = useState(false);
  const [baseWeight, setBaseWeight] = useState(null);
  const [generatorForm, setGeneratorForm] = useState({
    height_cm: '', weight_kg: '', duration_months: 3,
  });
  const generationRun = useRef(0);
  const { toast, show: showToast } = useToast();

  function hydratePlan(nextPlan) {
    setPlan(nextPlan);
    const checked = {};
    const statuses = {};
    const diary = {};
    for (const row of nextPlan.daily_progress || []) {
      checked[row.progress_date] = row.checked_items || [];
      statuses[row.progress_date] = row.status;
      diary[row.progress_date] = row.diary_items || [];
    }
    setCheckedByDate(checked);
    setDiaryByDate(diary);
    setStatusByDate(statuses);
    const dates = datesInPeriod(nextPlan.current_checkin);
    setActiveDate((current) => {
      if (current && dates.includes(current)) return current;
      const today = todayKey();
      if (dates.includes(today)) return today;
      return dates.find((item) => item >= today) || dates.at(-1) || null;
    });
  }

  async function fetchPlan() {
    try {
      const nextPlan = await api.activePlan();
      hydratePlan(nextPlan);
      setError(null);
    } catch (requestError) {
      setPlan(null);
      setError(requestError.status === 404 ? null : requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function fetchHistory() {
    try {
      setHistory(await api.checkinHistory());
    } catch {
      setHistory([]);
    }
  }

  async function waitForPlan(jobId, runId) {
    setIsGenerating(true);
    try {
      let job = { status: 'QUEUED' };
      while (job.status === 'QUEUED' || job.status === 'RUNNING') {
        await new Promise((resolve) => window.setTimeout(resolve, 3000));
        if (generationRun.current !== runId) return;
        job = await api.generatePlanStatus(jobId);
      }
      if (generationRun.current !== runId) return;
      if (job.status !== 'DONE') throw new Error(job.error || 'Không thể tạo lộ trình');
      window.localStorage.removeItem(PLAN_JOB_KEY);
      hydratePlan(await api.activePlan());
      await fetchHistory();
      setError(null);
      showToast('Đã tạo chương trình và lộ trình cá nhân hóa mới.');
    } catch (requestError) {
      if (generationRun.current !== runId) return;
      window.localStorage.removeItem(PLAN_JOB_KEY);
      setError(`Có lỗi khi tạo lộ trình: ${requestError.message}`);
      showToast(requestError.message, 'danger');
    } finally {
      if (generationRun.current === runId) setIsGenerating(false);
    }
  }

  useEffect(() => {
    fetchPlan();
    fetchHistory();
    const runId = ++generationRun.current;
    const jobId = window.localStorage.getItem(PLAN_JOB_KEY);
    if (jobId) waitForPlan(jobId, runId);
    return () => {
      if (generationRun.current === runId) generationRun.current += 1;
    };
  }, []);

  useEffect(() => {
    if (plan?.current_checkin?.feedback_status !== 'PENDING') return undefined;
    const timer = window.setInterval(fetchPlan, 15000);
    return () => window.clearInterval(timer);
  }, [plan?.current_checkin?.feedback_status]);

  async function openGenerator() {
    setGeneratorBusy(true);
    setError(null);
    try {
      const me = await api.me();
      const height = me.profile?.height_cm ?? '';
      const weight = me.profile?.weight_kg ?? '';
      setBaseWeight(weight === '' ? null : Number(weight));
      setGeneratorForm({ height_cm: height, weight_kg: weight, duration_months: 3 });
      setGeneratorOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setGeneratorBusy(false);
    }
  }

  async function submitGenerator() {
    setGeneratorBusy(true);
    setError(null);
    try {
      const replacingActive = plan?.status === 'ACTIVE';
      const job = await api.generatePlan({
        height_cm: Number(generatorForm.height_cm),
        weight_kg: Number(generatorForm.weight_kg),
        duration_months: Number(generatorForm.duration_months),
        confirm_recreate: replacingActive,
        expected_active_plan_id: replacingActive ? plan.id : null,
      });
      const runId = ++generationRun.current;
      window.localStorage.setItem(PLAN_JOB_KEY, job.job_id);
      setGeneratorOpen(false);
      await waitForPlan(job.job_id, runId);
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message, 'danger');
    } finally {
      setGeneratorBusy(false);
    }
  }

  const periodDates = datesInPeriod(plan?.current_checkin);
  const checkedItems = checkedByDate[activeDate] || [];
  const diaryItems = diaryByDate[activeDate] || [];
  const progressStatus = statusByDate[activeDate] || 'IN_PROGRESS';
  const futureDate = activeDate > todayKey();
  const pastDate = Boolean(activeDate && activeDate < todayKey());
  const periodLocked = plan?.current_checkin?.status !== 'OPEN';
  const progressLocked = futureDate || periodLocked;
  const programStart = plan?.program?.started_at || plan?.start_date;
  const templateIndex = activeDate && programStart
    ? ((parseDate(activeDate) - parseDate(programStart)) / 86400000) % 7
    : 0;
  const day = plan?.content?.days?.[(templateIndex + 7) % 7];
  const exercise = exerciseData(day?.exercise);
  const totalItems = (day?.meals?.length || 0) + (day?.exercise ? 1 : 0);

  const completedStreak = useMemo(() => {
    let streak = 0;
    const sortedDates = [...periodDates].filter((d) => d <= todayKey()).sort().reverse();
    for (const d of sortedDates) {
      if (statusByDate[d] === 'COMPLETED' || (checkedByDate[d] && checkedByDate[d].length >= totalItems && totalItems > 0)) {
        streak += 1;
      } else if (d < todayKey()) {
        break;
      }
    }
    return streak;
  }, [periodDates, statusByDate, checkedByDate, totalItems]);

  function toggleItem(key) {
    if (progressLocked) return;
    setCheckedByDate((current) => {
      const selected = new Set(current[activeDate] || []);
      if (selected.has(key)) selected.delete(key);
      else selected.add(key);
      return { ...current, [activeDate]: ITEM_KEYS.filter((item) => selected.has(item)) };
    });
  }

  function applyProgress(result) {
    setCheckedByDate((current) => ({ ...current, [result.progress_date]: result.checked_items }));
    setDiaryByDate((current) => ({ ...current, [result.progress_date]: result.diary_items || [] }));
    setStatusByDate((current) => ({ ...current, [result.progress_date]: result.status }));
    if (result.status === 'COMPLETED' || (result.checked_items && result.checked_items.length >= totalItems && totalItems > 0)) {
      fireConfetti();
    }
  }

  function deltaText(result) {
    const parts = [];
    if (result.kcal_intake_delta) parts.push(`${result.kcal_intake_delta > 0 ? '+' : ''}${result.kcal_intake_delta} kcal nạp`);
    if (result.kcal_burned_delta) parts.push(`${result.kcal_burned_delta > 0 ? '+' : ''}${result.kcal_burned_delta} kcal tiêu hao`);
    return parts.length ? ` (${parts.join(', ')})` : '';
  }

  async function runProgress(action) {
    if (!activeDate || !plan) return;
    setProgressBusy(true);
    setError(null);
    try {
      let result;
      if (action === 'save') {
        result = await api.savePlanDayProgress(plan.id, activeDate, checkedItems);
        showToast(`Đã lưu tiến độ${deltaText(result)}.`);
      } else if (action === 'complete') {
        result = await api.completePlanDay(plan.id, activeDate, checkedItems);
        showToast(`Đã ghi nhận ngày ${dateLabel(activeDate)}${deltaText(result)}.`);
      } else {
        if (!window.confirm('Đặt lại tiến độ ngày này? Các nhật ký do lộ trình tạo sẽ được xóa.')) return;
        result = await api.resetPlanDay(plan.id, activeDate);
        showToast(`Đã đặt lại tiến độ${deltaText(result)}.`);
      }
      applyProgress(result);
      if (action === 'complete') {
        const nextDate = periodDates.find((value) => (
          value > activeDate && value <= todayKey() && statusByDate[value] !== 'COMPLETED'
        ));
        if (nextDate) setActiveDate(nextDate);
      }
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message, 'danger');
    } finally {
      setProgressBusy(false);
    }
  }

  function requestComplete() {
    const missing = [];
    for (let index = 0; index < (day?.meals || []).length; index += 1) {
      if (!checkedItems.includes(`meal:${index}`)) {
        missing.push(day.meals[index].name || `Bữa ăn ${index + 1}`);
      }
    }
    if (day?.exercise && !checkedItems.includes('exercise')) missing.push(exercise.name);
    if (missing.length) setMissingItems(missing);
    else runProgress('complete');
  }

  async function extendProgram() {
    setExtending(true);
    setError(null);
    try {
      await api.extendProgram(Number(extendMonths));
      await fetchPlan();
      await fetchHistory();
      showToast(`Đã gia hạn thêm ${extendMonths} tháng và mở Đợt tiếp theo.`);
    } catch (requestError) {
      setError(requestError.message);
      showToast(requestError.message, 'danger');
    } finally {
      setExtending(false);
    }
  }

  const height = Number(generatorForm.height_cm);
  const weight = Number(generatorForm.weight_kg);
  const heightValid = height > 50 && height < 250;
  const weightValid = weight >= 20 && weight <= 300;
  const weightGuardValid = !baseWeight || Math.abs(weight - baseWeight) / baseWeight <= 0.10;
  const generatorValid = heightValid && weightValid && weightGuardValid;
  const needsProfile = error?.includes('hoàn thiện hồ sơ') || error?.includes('cập nhật');

  if (loading) {
    return (
      <div className="max-w-4xl space-y-4" aria-busy="true">
        <div className="h-8 w-56 animate-pulse rounded-sm bg-paper-3" />
        <div className="h-24 animate-pulse rounded-md bg-paper-3" />
        <div className="h-64 animate-pulse rounded-md bg-paper-3" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
          <h1 className="font-display text-2xl font-bold tracking-tight">Lộ trình cá nhân hóa</h1>
          <button
            type="button"
            onClick={() => setHelpOpen(true)}
            className="flex h-8 items-center gap-1.5 rounded-full bg-paper-3 px-2.5 text-xs font-semibold text-ink-2 shadow-xs transition-colors hover:bg-accent-soft hover:text-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
            aria-label="Xem hướng dẫn vận hành lộ trình"
            title="Cách hoạt động của lộ trình"
          >
            <HelpCircle size={15} />
            <span className="hidden sm:inline">Hướng dẫn</span>
          </button>
          </div>
          <p className="mt-1 text-sm font-medium text-ink-2">Kế hoạch dinh dưỡng & tập luyện 7 ngày tới (Mục tiêu chiến lược)</p>
        </div>

        <GenerateButton loading={isGenerating || generatorBusy} onClick={openGenerator}>
          {plan ? 'Bắt đầu chương trình mới' : 'Tạo lộ trình cá nhân hóa'}
        </GenerateButton>
      </header>

      {error && (
        <div className="space-y-2">
          <p className="rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>
          {needsProfile && (
            <Link to="/profile" className="inline-flex min-h-11 items-center rounded-sm bg-accent-strong px-4 py-2 text-sm font-semibold text-accent-ink">
              Cập nhật hồ sơ sức khỏe
            </Link>
          )}
        </div>
      )}

      {!plan ? (
        <section className="space-y-6 rounded-md bg-paper-2 p-6 sm:p-8 shadow-hairline">
          <div className="border-b border-rule pb-4">
            <h2 className="font-body text-xl font-bold text-ink">3 bước để nhận lộ trình dinh dưỡng cá nhân</h2>
            <p className="mt-1 font-body text-sm text-ink-2">
              Hệ thống sẽ thiết kế thực đơn khoa học phù hợp với thể trạng và mục tiêu sức khỏe của bạn.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Bước 1 */}
            <div className="rounded-lg bg-paper-3 p-5 shadow-hairline flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-strong text-accent-ink font-bold text-sm">
                    1
                  </span>
                  <span className="rounded-md bg-accent-soft p-2 text-accent-strong">
                    <UserCheck size={18} />
                  </span>
                </div>
                <h3 className="font-body font-bold text-base mb-2 text-ink">Cập nhật hồ sơ sức khỏe</h3>
                <p className="font-body text-sm leading-relaxed text-ink-2">
                  Khai báo mục tiêu, dị ứng và bệnh lý nền để hệ thống tính calo và loại trừ món không an toàn.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-rule/50">
                <Link to="/profile" className="inline-flex items-center gap-1 font-body text-sm font-semibold text-accent-strong hover:underline">
                  Kiểm tra hồ sơ <ArrowRight size={14} />
                </Link>
              </div>
            </div>

            {/* Bước 2 */}
            <div className="rounded-lg bg-paper-3 p-5 shadow-hairline flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-strong text-accent-ink font-bold text-sm">
                    2
                  </span>
                  <span className="rounded-md bg-accent-soft p-2 text-accent-strong">
                    <UtensilsCrossed size={18} />
                  </span>
                </div>
                <h3 className="font-body font-bold text-base mb-2 text-ink">Tạo lộ trình thực đơn</h3>
                <p className="font-body text-sm leading-relaxed text-ink-2">
                  Bấm nút tạo lộ trình để nhận thực đơn 7 ngày cá nhân hóa kèm gợi ý vận động phù hợp.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-rule/50">
                <span className="font-body text-sm text-ink-2 font-medium">Thiết kế theo thể trạng</span>
              </div>
            </div>

            {/* Bước 3 */}
            <div className="rounded-lg bg-paper-3 p-5 shadow-hairline flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-strong text-accent-ink font-bold text-sm">
                    3
                  </span>
                  <span className="rounded-md bg-accent-soft p-2 text-accent-strong">
                    <Camera size={18} />
                  </span>
                </div>
                <h3 className="font-body font-bold text-base mb-2 text-ink">Ghi nhận nhật ký bữa ăn</h3>
                <p className="font-body text-sm leading-relaxed text-ink-2">
                  Chụp hoặc tải ảnh món ăn ở tab Nhật ký. Hệ thống sẽ tự động tính calo và đánh dấu hoàn thành bữa ăn tương ứng.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-rule/50">
                <Link to="/diary" className="inline-flex items-center gap-1 font-body text-sm font-semibold text-accent-strong hover:underline">
                  Đến trang Nhật ký <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </div>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
            <GenerateButton primary loading={isGenerating || generatorBusy} onClick={openGenerator}>
              Tạo lộ trình AI ngay
            </GenerateButton>
          </div>
        </section>
      ) : (
        <>
          <ProgramSummary plan={plan} />

          {plan.warnings?.length > 0 && (
            <section aria-label="Cảnh báo an toàn của thực đơn" className="space-y-3 rounded-md bg-paper-2 p-5 shadow-hairline">
              <h2 className="font-display font-semibold">Cảnh báo an toàn</h2>
              <WarningList warnings={plan.warnings} showDisclaimer />
            </section>
          )}

          <CheckinPanel
            checkin={plan.current_checkin}
            onChanged={() => { fetchPlan(); fetchHistory(); }}
            onError={setError}
          />

          {periodDates.length > 0 && (
            <>
              <section>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-3">
                    <div>
                      <h2 className="font-display font-semibold">Theo dõi Đợt {plan.current_checkin.period_number}</h2>
                      <p className="text-sm font-medium text-ink-2">Mẫu 7 ngày được lặp lại trong từng Đợt 14 ngày.</p>
                    </div>
                    {completedStreak > 0 && (
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-warning-soft px-3 py-1 text-xs font-bold text-warning-strong shadow-xs">
                        🔥 Chuỗi {completedStreak} ngày kiên trì
                      </span>
                    )}
                  </div>
                  {progressStatus === 'COMPLETED' && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold text-accent-strong">
                      <CheckCircle2 size={14} /> {progressLabel(progressStatus, checkedItems.length, totalItems)}
                    </span>
                  )}
                </div>

                <div role="tablist" aria-label="Chọn ngày trong Đợt" className="flex gap-2 overflow-x-auto pb-2">
                  {periodDates.map((value, index) => {
                    const active = value === activeDate;
                    const count = checkedByDate[value]?.length || 0;
                    const complete = statusByDate[value] === 'COMPLETED';
                    return (
                      <button
                        key={value}
                        role="tab"
                        aria-selected={active}
                        onClick={() => setActiveDate(value)}
                        className={[
                          'flex min-h-16 min-w-28 shrink-0 flex-col items-center rounded-md px-3 py-2 text-sm shadow-hairline transition-colors',
                          active ? 'bg-accent-strong text-accent-ink' : 'bg-paper-2 text-ink-2 hover:bg-paper-3',
                        ].join(' ')}
                      >
                        <span className="font-semibold">Ngày {index + 1}</span>
                        <span className={`text-xs ${active ? 'text-accent-ink/90' : 'text-ink-2'}`}>
                          {dateLabel(value)}
                        </span>
                        <span className={`text-xs ${active ? 'text-accent-ink/90' : 'text-ink-2'}`}>
                          {progressLabel(complete ? 'COMPLETED' : 'IN_PROGRESS', count, totalItems)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>

              {day && (
                <section className="rounded-md bg-paper-2 p-5 shadow-hairline">
                  {futureDate && (
                    <p className="mb-3 rounded-sm bg-warning-soft px-3 py-2 text-sm text-warning-strong">
                      Ngày này ở tương lai nên hiện tại bạn chỉ có thể xem trước.
                    </p>
                  )}
                  {pastDate && !periodLocked && (
                    <p className="mb-3 flex items-center gap-2 rounded-sm bg-info-soft px-3 py-2 text-sm text-info">
                      <CalendarClock size={15} /> Bạn đang cập nhật tiến độ ngày {fullDateLabel(activeDate)}.
                    </p>
                  )}
                  {periodLocked && (
                    <p className="mb-3 flex items-center gap-2 rounded-sm bg-paper-3 px-3 py-2 text-sm font-medium text-ink-2">
                      <LockKeyhole size={15} /> Đợt này đã khóa nên không còn nhận thay đổi.
                    </p>
                  )}

                  {checkedItems.length === totalItems && totalItems > 0 && (
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-accent/30 bg-accent-soft/40 p-4 shadow-sm transition-all duration-300">
                      <div className="flex items-center gap-3">
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-strong text-xl text-white shadow-sm">
                          🏆
                        </span>
                        <div>
                          <p className="font-display font-bold text-accent-strong">Xuất sắc! Đã hoàn thành 100% mục tiêu ngày</p>
                          <p className="text-sm font-medium text-ink-2">Bạn đã hoàn thành đủ các bữa ăn và bài tập thể dục theo lộ trình hôm nay.</p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={fireConfetti}
                        className="shrink-0 rounded-full bg-accent-strong px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm transition-transform duration-short hover:scale-105 active:scale-95"
                      >
                        🎉 Ăn mừng!
                      </button>
                    </div>
                  )}

                  <p className="mb-3 flex items-start gap-2 rounded-md bg-accent-soft px-3 py-2 text-sm text-ink-2">
                    <Lightbulb size={16} className="mt-0.5 shrink-0 text-accent-strong" aria-hidden="true" />
                    <span>
                      <span className="font-semibold text-ink">Mẹo:</span> Khi bạn ghi món ăn trong{' '}
                      <Link to="/diary" className="font-semibold text-accent-strong hover:underline">Nhật ký</Link>{' '}
                      hàng ngày, tiến độ bữa ăn và calo sẽ được tự động đồng bộ sang Lộ trình tại đây.
                    </span>
                  </p>
                  <ol className="relative space-y-1 border-l-2 border-rule-2 pl-5 marker:content-none">
                    {(day.meals || []).map((meal, index) => (
                      <ProgressItem
                        key={`meal:${index}`}
                        icon={mealIcon(meal.type)}
                        checked={checkedItems.includes(`meal:${index}`)}
                        fromDiary={checkedItems.includes(`meal:${index}`) && diaryItems.includes(`meal:${index}`)}
                        disabled={progressLocked}
                        onToggle={() => toggleItem(`meal:${index}`)}
                        title={meal.name}
                        tag={meal.type}
                        trailing={`${meal.kcal} kcal`}
                      />
                    ))}
                    {day.exercise && (
                      <ProgressItem
                        icon={Footprints}
                        checked={checkedItems.includes('exercise')}
                        disabled={progressLocked}
                        onToggle={() => toggleItem('exercise')}
                        title={exercise.name}
                        tag="Vận động"
                        trailing={[
                          exercise.duration ? `${exercise.duration} phút` : null,
                          exercise.calories ? `${exercise.calories} kcal` : null,
                        ].filter(Boolean).join(' · ')}
                        exercise
                      />
                    )}
                  </ol>

                  <div className="mt-5 flex flex-wrap justify-end gap-2 border-t border-rule-2 pt-4">
                    <Btn variant="ghost" disabled={progressBusy || progressLocked || checkedItems.length === 0} onClick={() => runProgress('reset')}>
                      <RotateCcw size={15} /> Đặt lại
                    </Btn>
                    <Btn disabled={progressBusy || progressLocked} onClick={() => runProgress('save')}>
                      <Save size={15} /> {progressStatus === 'COMPLETED' ? 'Lưu thay đổi' : 'Lưu tiến độ'}
                    </Btn>
                    {progressStatus !== 'COMPLETED' && (
                      <Btn variant="primary" disabled={progressBusy || progressLocked} onClick={requestComplete}>
                        <CheckCircle2 size={15} /> Ghi nhận ngày
                      </Btn>
                    )}
                  </div>
                </section>
              )}
            </>
          )}

          {plan.program?.status === 'COMPLETED' && (
            <ProgramCompletion
              plan={plan}
              extendMonths={extendMonths}
              setExtendMonths={setExtendMonths}
              extending={extending}
              onExtend={extendProgram}
              onNew={openGenerator}
            />
          )}

          {history.length > 0 && <CheckinHistory items={history} />}
        </>
      )}

      <Modal
        open={generatorOpen}
        onClose={() => !generatorBusy && setGeneratorOpen(false)}
        icon={<CalendarClock size={20} />}
        title={plan?.status === 'ACTIVE' ? 'Bắt đầu chương trình mới' : 'Tạo chương trình cá nhân hóa'}
        footer={(
          <>
            <Btn variant="ghost" disabled={generatorBusy} onClick={() => setGeneratorOpen(false)}>Hủy</Btn>
            <Btn variant="primary" disabled={generatorBusy || !generatorValid} onClick={submitGenerator}>
              {generatorBusy ? <RefreshCw size={15} className="animate-spin" /> : <CalendarClock size={15} />}
              Xác nhận tạo
            </Btn>
          </>
        )}
      >
        <div className="space-y-4">
          {plan?.status === 'ACTIVE' && (
            <p className="rounded-sm bg-warning-soft px-3 py-2 text-warning-strong">
              Chương trình hiện tại sẽ được lưu vào lịch sử và thay bằng chương trình mới sau khi AI tạo xong.
            </p>
          )}
          <label className="block space-y-1">
            <span className="font-medium text-ink">Chiều cao (cm)</span>
            <Field type="number" min="51" max="249" step="0.1" value={generatorForm.height_cm}
              onChange={(event) => setGeneratorForm((form) => ({ ...form, height_cm: event.target.value }))}
              className="w-full" aria-invalid={!heightValid} />
            {!heightValid && generatorForm.height_cm !== '' && <span className="text-xs text-danger">Chiều cao phải lớn hơn 50 và nhỏ hơn 250 cm.</span>}
          </label>
          <label className="block space-y-1">
            <span className="font-medium text-ink">Cân nặng hiện tại (kg)</span>
            <Field type="number" min="20" max="300" step="0.1" value={generatorForm.weight_kg}
              onChange={(event) => setGeneratorForm((form) => ({ ...form, weight_kg: event.target.value }))}
              className="w-full" aria-invalid={!weightValid || !weightGuardValid} />
            {!weightGuardValid && (
              <span className="text-xs text-danger">Chênh lệch quá 10% so với số đo gần nhất ({baseWeight} kg). Hãy kiểm tra lại hoặc cập nhật hồ sơ.</span>
            )}
          </label>
          <label className="block space-y-1">
            <span className="font-medium text-ink">Thời lượng chương trình</span>
            <Select value={generatorForm.duration_months}
              onChange={(event) => setGeneratorForm((form) => ({ ...form, duration_months: Number(event.target.value) }))}
              className="w-full">
              {Array.from({ length: 12 }, (_, index) => index + 1).map((month) => (
                <option key={month} value={month}>{month} tháng · {month * 28} ngày · {month * 2} Đợt</option>
              ))}
            </Select>
            <span className="text-sm font-medium text-ink-2">Mặc định 3 tháng. Mỗi tháng chương trình gồm 28 ngày.</span>
          </label>
        </div>
      </Modal>
      <Modal
        open={!!missingItems}
        onClose={() => setMissingItems(null)}
        icon={<CheckCircle2 size={20} />}
        tone="warning"
        title="Vẫn còn mục chưa hoàn thành"
        footer={(
          <>
            <Btn variant="ghost" onClick={() => setMissingItems(null)}>Quay lại đánh dấu</Btn>
            <Btn variant="primary" onClick={() => { setMissingItems(null); runProgress('complete'); }}>
              Vẫn ghi nhận ngày
            </Btn>
          </>
        )}
      >
        <p className="mb-2">Các mục sau chưa được đánh dấu:</p>
        <ul className="list-disc space-y-1 pl-5">
          {(missingItems || []).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </Modal>

      <Modal
        open={helpOpen}
        onClose={() => setHelpOpen(false)}
        icon={<HelpCircle size={20} />}
        title="Cách hoạt động của lộ trình"
        footer={(
          <Btn variant="primary" onClick={() => setHelpOpen(false)}>
            Đã hiểu
          </Btn>
        )}
      >
        <div className="space-y-4 pt-1 font-body">
          <p className="text-sm text-ink-2 leading-relaxed">
            Lộ trình NutriSmart kết nối trực tiếp với Nhật ký ăn uống của bạn qua 3 bước vận hành:
          </p>

          <ol className="space-y-4">
            <li className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-bold text-accent-strong">
                1
              </span>
              <div>
                <h4 className="font-bold text-ink text-sm">Cập nhật hồ sơ sức khỏe</h4>
                <p className="text-sm text-ink-2 mt-0.5 leading-relaxed">
                  Khai báo mục tiêu, dị ứng và bệnh lý nền để hệ thống tính calo và loại trừ món không an toàn.
                </p>
              </div>
            </li>

            <li className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-bold text-accent-strong">
                2
              </span>
              <div>
                <h4 className="font-bold text-ink text-sm">Bấm &apos;Tạo lộ trình AI&apos;</h4>
                <p className="text-sm text-ink-2 mt-0.5 leading-relaxed">
                  Nhận thực đơn 7 ngày cá nhân hóa (lặp lại linh hoạt trong từng đợt 14 ngày) kèm bài tập rèn luyện.
                </p>
              </div>
            </li>

            <li className="flex gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-bold text-accent-strong">
                3
              </span>
              <div>
                <h4 className="font-bold text-ink text-sm">Ghi nhận bữa ăn bên tab Nhật ký</h4>
                <p className="text-sm text-ink-2 mt-0.5 leading-relaxed">
                  Chụp hoặc tải ảnh món ăn ở tab Nhật ký. Hệ thống sẽ tự động tính calo và đánh dấu hoàn thành bữa ăn tương ứng ngay trên lộ trình.
                </p>
              </div>
            </li>
          </ol>

          <div className="rounded-md bg-accent-soft p-3.5 text-sm font-medium text-accent-strong leading-relaxed">
            Mẹo: Mỗi 14 ngày, bạn sẽ có một đợt <b>Check-in tiến độ</b> để AI đánh giá kết quả và tự động điều chỉnh mức calo nếu cần.
          </div>
        </div>
      </Modal>

      <Toast toast={toast} />
    </div>
  );
}

function ProgramSummary({ plan }) {
  const program = plan.program;
  return (
    <section className="rounded-md bg-paper-2 p-5 shadow-hairline">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display font-semibold">Chương trình {program ? `${program.duration_months} tháng` : `phiên bản ${plan.version}`}</h2>
          <p className="mt-1 text-sm text-muted">
            {program?.started_at || plan.start_date} → {program?.planned_end_date || plan.end_date}
          </p>
        </div>
        {program && (
          <span className="rounded-full bg-accent-soft px-3 py-1 text-sm font-semibold text-accent-strong">
            Đợt {Math.min(plan.current_checkin?.period_number || program.completed_periods, program.total_periods)}/{program.total_periods}
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        <span className="rounded-full bg-accent-soft px-3 py-1 font-medium text-accent-strong">{plan.goal}</span>
        <span className="rounded-full bg-paper-3 px-3 py-1 text-ink-2">{plan.daily_kcal_target} kcal/ngày</span>
        {plan.bmi && <span className="rounded-full bg-paper-3 px-3 py-1 text-ink-2">BMI {plan.bmi}</span>}
      </div>
    </section>
  );
}

function ProgramCompletion({ plan, extendMonths, setExtendMonths, extending, onExtend, onNew }) {
  const summary = plan.program_summary || {};
  const remaining = Math.max(0, 12 - Number(plan.program.duration_months));
  return (
    <section className="space-y-4 rounded-md bg-accent-soft p-5 text-accent-strong shadow-hairline">
      <div>
        <h2 className="font-display font-semibold">Chương trình đã hoàn thành</h2>
        <p className="mt-1 text-sm">Đây là tổng kết từ ngày bắt đầu đến hết Đợt cuối.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SummaryMetric label="Cân nặng" value={summary.start_weight_kg != null
          ? `${summary.start_weight_kg} → ${summary.end_weight_kg ?? '-'} kg` : 'Chưa có dữ liệu'} />
        <SummaryMetric label="Ngày có nhật ký" value={summary.logged_days ?? 0} />
        <SummaryMetric label="Ngày đã ghi nhận" value={summary.completed_days ?? 0} />
        <SummaryMetric label="Tỷ lệ item" value={`${summary.completion_rate_pct ?? 0}%`} />
        <SummaryMetric label="Kcal nạp trung bình" value={`${summary.avg_kcal_intake ?? 0} kcal`} />
        <SummaryMetric label="Kcal tiêu hao trung bình" value={`${summary.avg_kcal_burned ?? 0} kcal`} />
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-accent/30 pt-4">
        {remaining > 0 && (
          <>
            <Select value={extendMonths} disabled={extending} onChange={(event) => setExtendMonths(Number(event.target.value))}>
              {Array.from({ length: remaining }, (_, index) => index + 1).map((month) => (
                <option key={month} value={month}>Gia hạn {month} tháng</option>
              ))}
            </Select>
            <Btn disabled={extending} onClick={onExtend}>
              {extending && <RefreshCw size={15} className="animate-spin" />} Gia hạn chương trình
            </Btn>
          </>
        )}
        <Btn variant="primary" disabled={extending} onClick={onNew}>Bắt đầu mục tiêu mới</Btn>
      </div>
    </section>
  );
}

function SummaryMetric({ label, value }) {
  return (
    <div className="rounded-sm bg-paper-2/80 p-3">
      <span className="block text-sm font-semibold uppercase tracking-wide text-ink-2">{label}</span>
      <strong className="mt-1 block text-ink">{value}</strong>
    </div>
  );
}

function ProgressItem({ icon: Icon, checked, disabled, onToggle, title, tag, trailing, exercise, fromDiary }) {
  return (
    <li className="relative py-1">
      <span className="absolute -left-[1.72rem] top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-paper-2 bg-rule" />
      <label className={[
        'group flex items-center gap-3 rounded-md p-3 transition-colors',
        disabled ? 'cursor-not-allowed opacity-70' : 'cursor-pointer hover:bg-paper-3',
      ].join(' ')}>
        <span className="relative flex h-6 w-6 shrink-0 items-center justify-center">
          <input type="checkbox" checked={checked} disabled={disabled} onChange={onToggle} className="peer absolute inset-0 h-full w-full opacity-0" />
          <span className={[
            'flex h-5 w-5 items-center justify-center rounded-sm border-2',
            checked ? 'border-accent-strong bg-accent-strong text-accent-ink' : 'border-rule bg-paper-2',
          ].join(' ')}>
            {checked && <Check size={13} strokeWidth={3.2} />}
          </span>
        </span>
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${exercise ? 'bg-info-soft text-info' : 'bg-accent-soft text-accent-strong'}`}>
          <Icon size={17} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold uppercase tracking-wide text-ink-2">{tag}</span>
          <span className={`block text-sm ${checked ? 'font-medium text-muted line-through' : 'font-semibold text-ink'}`}>{title}</span>
          {fromDiary && (
            <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-accent-soft px-2 py-0.5 text-xs font-semibold text-accent-strong">
              <CheckCircle2 size={12} aria-hidden="true" /> Đã đồng bộ từ Nhật ký
            </span>
          )}
        </span>
        {trailing && <span className="shrink-0 text-sm font-medium text-ink-2">{trailing}</span>}
      </label>
    </li>
  );
}

function GenerateButton({ primary, loading, onClick, children }) {
  return (
    <button type="button" onClick={onClick} disabled={loading}
      className={[
        'flex min-h-11 items-center gap-2 rounded-md px-4 py-2 text-sm font-medium shadow-hairline transition-colors disabled:cursor-not-allowed disabled:opacity-60',
        primary ? 'bg-accent-strong text-accent-ink' : 'bg-paper-2 text-accent-strong hover:bg-accent-soft',
      ].join(' ')}>
      {loading ? <RefreshCw size={16} className="animate-spin" /> : <RefreshCw size={16} />}
      {loading ? 'AI đang tạo lộ trình…' : children}
    </button>
  );
}
