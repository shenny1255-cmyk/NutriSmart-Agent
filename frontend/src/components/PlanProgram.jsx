import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  CalendarClock, Check, CheckCircle2, Cookie, Footprints, LockKeyhole,
  Moon, RefreshCw, RotateCcw, Save, Sparkles, Sun, Sunrise, UtensilsCrossed,
} from 'lucide-react';
import { api } from '../lib/api.js';
import { Btn, Field, Modal, Select, Toast, useToast } from './ui.jsx';

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
    return {
      name: value.name || 'Vận động theo lộ trình',
      duration: Number(value.duration_min || 0),
      calories: Number(value.calories_kcal || 0),
    };
  }
  const text = String(value || '').trim();
  if (!text) return { name: 'Vận động theo lộ trình', duration: 0, calories: 0 };
  const durationMatch = text.match(/(\d+(?:[.,]\d+)?)\s*(?:phút|phut|minutes?|mins?)/i);
  const caloriesMatch = text.match(/(\d+(?:[.,]\d+)?)\s*kcal/i);
  const metricStarts = [durationMatch?.index, caloriesMatch?.index]
    .filter((index) => Number.isInteger(index));
  const name = metricStarts.length
    ? text.slice(0, Math.min(...metricStarts)).replace(/[\s\-–—·,:]+$/u, '')
    : text;
  return {
    name: name || 'Vận động theo lộ trình',
    duration: durationMatch ? Math.trunc(Number(durationMatch[1].replace(',', '.'))) : 0,
    calories: caloriesMatch ? Number(caloriesMatch[1].replace(',', '.')) : 0,
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
  const [statusByDate, setStatusByDate] = useState({});
  const [progressBusy, setProgressBusy] = useState(false);
  const [missingItems, setMissingItems] = useState(null);
  const [generatorOpen, setGeneratorOpen] = useState(false);
  const [generatorBusy, setGeneratorBusy] = useState(false);
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
    for (const row of nextPlan.daily_progress || []) {
      checked[row.progress_date] = row.checked_items || [];
      statuses[row.progress_date] = row.status;
    }
    setCheckedByDate(checked);
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
    setStatusByDate((current) => ({ ...current, [result.progress_date]: result.status }));
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
        <h1 className="font-display text-2xl font-bold tracking-tight">Lộ trình cá nhân hóa</h1>
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
        <section className="flex flex-col items-center gap-4 rounded-md bg-paper-2 p-8 text-center shadow-hairline">
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
            <Sparkles size={26} />
          </span>
          <div>
            <h2 className="font-display text-xl font-bold">Chưa có chương trình nào</h2>
            <p className="mt-1 text-sm text-muted">Chọn thời lượng từ 1 đến 12 tháng để bắt đầu.</p>
          </div>
          <GenerateButton primary loading={isGenerating || generatorBusy} onClick={openGenerator}>
            Tạo lộ trình cá nhân hóa
          </GenerateButton>
        </section>
      ) : (
        <>
          <ProgramSummary plan={plan} />

          <CheckinPanel
            checkin={plan.current_checkin}
            onChanged={() => { fetchPlan(); fetchHistory(); }}
            onError={setError}
          />

          {periodDates.length > 0 && (
            <>
              <section>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="font-display font-semibold">Theo dõi Đợt {plan.current_checkin.period_number}</h2>
                    <p className="text-sm text-muted">Mẫu 7 ngày được lặp lại trong từng Đợt 14 ngày.</p>
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
                        <span className={`text-xs ${active ? 'text-accent-ink/80' : 'text-muted'}`}>
                          {dateLabel(value)}
                        </span>
                        <span className={`text-xs ${active ? 'text-accent-ink/80' : 'text-muted'}`}>
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
                    <p className="mb-3 flex items-center gap-2 rounded-sm bg-paper-3 px-3 py-2 text-sm text-muted">
                      <LockKeyhole size={15} /> Đợt này đã khóa nên không còn nhận thay đổi.
                    </p>
                  )}
                  <ol className="relative space-y-1 border-l-2 border-rule-2 pl-5 marker:content-none">
                    {(day.meals || []).map((meal, index) => (
                      <ProgressItem
                        key={`meal:${index}`}
                        icon={mealIcon(meal.type)}
                        checked={checkedItems.includes(`meal:${index}`)}
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
              {generatorBusy ? <RefreshCw size={15} className="animate-spin" /> : <Sparkles size={15} />}
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
            <span className="text-xs text-muted">Mặc định 3 tháng. Mỗi tháng chương trình gồm 28 ngày.</span>
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
          ? `${summary.start_weight_kg} → ${summary.end_weight_kg ?? '—'} kg` : 'Chưa có dữ liệu'} />
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
      <span className="block text-xs uppercase tracking-wide text-muted">{label}</span>
      <strong className="mt-1 block text-ink">{value}</strong>
    </div>
  );
}

function ProgressItem({ icon: Icon, checked, disabled, onToggle, title, tag, trailing, exercise }) {
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
          <span className="block text-xs font-medium uppercase tracking-wide text-muted">{tag}</span>
          <span className={`block text-sm font-medium ${checked ? 'text-muted line-through' : 'text-ink'}`}>{title}</span>
        </span>
        {trailing && <span className="shrink-0 text-sm text-ink-2">{trailing}</span>}
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
