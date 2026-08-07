import { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend, ReferenceLine, Area, AreaChart } from 'recharts';
import { Target, Flame, Scale, Footprints, Bell, ChevronRight, Utensils } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api.js';

const MOCK = Array.from({ length: 7 }, (_, i) => ({
  day: `T${i + 2}`,
  kcal_intake: 1800 + Math.round(Math.random() * 500),
  kcal_burned: 300 + Math.round(Math.random() * 300),
}));

// Recharts vẽ SVG attribute nên không nhận var() trực tiếp — đọc token 1 lần từ :root,
// giữ đúng kỷ luật "màu chỉ khai báo ở tokens.css, component chỉ tham chiếu".
function useTokens(names) {
  return useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    return Object.fromEntries(names.map((n) => [n, cs.getPropertyValue(n).trim()]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

// Gợi ý bữa ăn tiếp theo dựa theo giờ hiện tại
function getNextMealSuggestion() {
  const hour = new Date().getHours();
  if (hour < 10) return { meal: 'Bữa sáng', suggestion: 'Yến mạch hoa quả tươi', emoji: '🥣' };
  if (hour < 14) return { meal: 'Bữa trưa', suggestion: 'Salad Gà & Bơ', emoji: '🥗' };
  if (hour < 17) return { meal: 'Bữa phụ', suggestion: 'Sữa chua & hạt điều', emoji: '🥜' };
  return { meal: 'Bữa tối', suggestion: 'Cá hồi áp chảo rau củ', emoji: '🐟' };
}

export default function Dashboard() {
  const [data, setData] = useState(MOCK);
  const [offline, setOffline] = useState(false);
  const [activity, setActivity] = useState({ steps: 0, calories_burned: 0 });
  const [syncStatus, setSyncStatus] = useState(null); // null | 'ok' | 'error'
  const [showBell, setShowBell] = useState(false);
  const [notifications, setNotifications] = useState([]);

  const nextMeal = getNextMealSuggestion();

  useEffect(() => {
    api.dailySummary(7)
      .then(setData)
      .catch(() => setOffline(true));   // backend chưa chạy → giữ MOCK
  }, []);

  // Lấy dữ liệu vận động hôm nay từ Mobile (đã sync lên backend)
  useEffect(() => {
    api.todayActivity()
      .then((res) => setActivity(res))
      .catch(() => {}); // Không ảnh hưởng nếu chưa có data Mobile
  }, [syncStatus]); // re-fetch mỗi khi sync thành công

  useEffect(() => {
    api.notifications().then(setNotifications).catch(() => setNotifications([]));
  }, []);

  const t = useTokens([
    '--color-accent', '--color-warning', '--color-warning-strong', '--color-rule-2',
    '--color-muted', '--color-paper-2', '--color-rule', '--color-ink',
  ]);

  const today = data.at(-1) ?? {};
  const target = today.daily_calorie_target ?? 2000;
  // Sử dụng kcal_burned từ activity (Mobile sync) hoặc từ backend summary
  const burnedKcal = activity.calories_burned || today.kcal_burned || 0;
  const intake = today.kcal_intake ?? 0;
  const remaining = target - intake + burnedKcal;
  const over = remaining < 0;

  // Phần trăm tiến độ nạp calo so với mục tiêu
  const intakePct = Math.min(100, target > 0 ? Math.round((intake / target) * 100) : 0);
  const remainingPct = Math.min(100, target > 0 ? Math.round((Math.abs(remaining) / target) * 100) : 0);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="font-display text-2xl font-bold tracking-tight">Tổng quan</h1>
          {offline && (
            <p className="rounded-full bg-warning-soft px-3 py-1 text-xs font-medium text-warning-strong">
              Chưa kết nối backend — đang hiển thị dữ liệu mẫu
            </p>
          )}
          {syncStatus === 'ok' && (
            <p className="rounded-full bg-accent-soft px-3 py-1 text-xs font-medium text-accent-strong">
              ✅ Đã đồng bộ từ Mobile
            </p>
          )}
        </div>

        {/* Nút chuông thông báo */}
        <div className="relative">
          <button
            id="btn-notifications"
            onClick={() => setShowBell((v) => !v)}
            className="relative flex h-10 w-10 items-center justify-center rounded-full glass-card text-ink-2 transition-all duration-short ease-out hover:scale-105 hover:text-accent-strong"
            aria-label="Thông báo"
          >
            <Bell size={20} strokeWidth={2} />
            {notifications.some((item) => !item.is_read) && (
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger" />
            )}
          </button>
          {showBell && (
            <div className="absolute right-0 top-12 z-dropdown w-72 glass-card rounded-xl p-4 shadow-card">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Thông báo</p>
              {notifications.length === 0 ? (
                <p className="text-sm text-muted">Chưa có thông báo mới.</p>
              ) : (
                <div className="max-h-72 space-y-1 overflow-y-auto">
                  {notifications.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={async () => {
                        if (!item.is_read) {
                          await api.markNotificationRead(item.id).catch(() => null);
                          setNotifications((rows) => rows.map((row) => row.id === item.id ? { ...row, is_read: true } : row));
                        }
                      }}
                      className={`w-full rounded-md p-2 text-left hover:bg-paper-3 ${item.is_read ? 'opacity-70' : 'bg-accent-soft/50'}`}
                    >
                      <span className="block text-sm font-medium text-ink">{item.title}</span>
                      {item.body && <span className="mt-0.5 block text-xs text-ink-2">{item.body}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Stats — 1 cột mobile, 4 cột từ md */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:[grid-template-columns:repeat(4,minmax(0,1fr))]">
        <Stat
          icon={Target} label="Mục tiêu hôm nay"
          value={target} unit="kcal"
          progress={intakePct} progressColor="accent"
        />
        <Stat
          icon={Flame} label="Đã nạp"
          value={intake} unit="kcal"
          progress={intakePct} progressColor="accent"
        />
        <Stat
          icon={Footprints}
          label="Đã tiêu hao"
          value={Math.round(burnedKcal)}
          unit="kcal"
          tone="burn"
          hint={activity.steps > 0 ? `${activity.steps.toLocaleString()} bước chân` : undefined}
          progress={Math.min(100, target > 0 ? Math.round((burnedKcal / target) * 100) : 0)}
          progressColor="burn"
        />
        <Stat
          icon={Scale}
          label={over ? 'Dư thừa' : 'Còn lại'}
          value={Math.abs(Math.round(remaining))}
          unit="kcal"
          tone={over ? 'warn' : 'ok'}
          hint={over ? 'Vượt mục tiêu hôm nay' : undefined}
          progress={remainingPct}
          progressColor={over ? 'warn' : 'accent'}
        />
      </div>

      {/* Biểu đồ + Widget gợi ý bữa ăn */}
      <div className="relative">
        <section className="glass-card rounded-xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-base font-semibold">
              Calo nạp vào / tiêu hao <span className="font-body font-normal text-muted">· 7 ngày</span>
            </h2>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
              <defs>
                <linearGradient id="gradIntake" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={t['--color-accent']} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={t['--color-accent']} stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="gradBurn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={t['--color-warning']} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={t['--color-warning']} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={t['--color-rule-2']} strokeDasharray="4 6" vertical={false} />
              <XAxis
                dataKey="day"
                fontSize={12}
                tick={{ fill: t['--color-muted'] }}
                tickLine={false}
                axisLine={{ stroke: t['--color-rule'] }}
              />
              <YAxis
                fontSize={12}
                tick={{ fill: t['--color-muted'] }}
                tickLine={false}
                axisLine={false}
                width={44}
              />
              <Tooltip
                cursor={{ stroke: t['--color-rule'], strokeDasharray: '4 4' }}
                contentStyle={{
                  background: 'rgba(255,255,255,0.85)',
                  backdropFilter: 'blur(12px)',
                  border: `1px solid rgba(255,255,255,0.4)`,
                  borderRadius: '10px',
                  boxShadow: '0 8px 24px rgba(50,100,70,0.12)',
                  fontFamily: 'var(--font-body)',
                  fontSize: 13,
                  color: t['--color-ink'],
                }}
                labelStyle={{ color: t['--color-muted'], marginBottom: 4 }}
              />
              <Legend
                iconType="plainline"
                wrapperStyle={{ fontSize: 13, fontFamily: 'var(--font-body)' }}
              />
              {/* Đường mục tiêu — nhìn phát biết ngày nào Nạp vào vượt mục tiêu */}
              <ReferenceLine
                y={target}
                stroke={t['--color-warning-strong']}
                strokeDasharray="6 4"
                strokeWidth={1.5}
                label={{
                  value: `Mục tiêu ${target} kcal`,
                  position: 'insideTopRight',
                  fill: t['--color-warning-strong'],
                  fontSize: 11,
                  fontFamily: 'var(--font-body)',
                }}
              />
              <Area
                type="monotone"
                dataKey="kcal_intake"
                name="Nạp vào"
                stroke={t['--color-accent']}
                strokeWidth={2.5}
                fill="url(#gradIntake)"
                dot={false}
                activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
              />
              <Area
                type="monotone"
                dataKey="kcal_burned"
                name="Tiêu hao"
                stroke={t['--color-warning']}
                strokeWidth={2.5}
                fill="url(#gradBurn)"
                dot={false}
                activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </section>

        {/* Widget gợi ý bữa ăn tiếp theo — nổi góc phải trên biểu đồ */}
        <div className="absolute right-4 top-4 hidden w-56 glass-card rounded-xl p-3 shadow-card sm:block">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
            Gợi ý bữa ăn tiếp theo
          </p>
          <div className="flex items-center gap-2">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xl">
              {nextMeal.emoji}
            </span>
            <div className="min-w-0">
              <p className="text-xs text-muted">{nextMeal.meal}</p>
              <p className="truncate text-sm font-semibold text-ink">{nextMeal.suggestion}</p>
            </div>
          </div>
          <Link
            to="/plan"
            className="mt-2 flex w-full items-center justify-between rounded-md bg-accent-soft px-2 py-1.5 text-xs font-medium text-accent-strong transition-colors hover:bg-accent/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            aria-label={`Xem lộ trình cho ${nextMeal.meal.toLowerCase()}`}
          >
            <span>Xem lộ trình</span>
            <ChevronRight size={14} />
          </Link>
        </div>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, unit, tone = 'neutral', hint, progress, progressColor = 'accent' }) {
  const warn = tone === 'warn';
  const burn = tone === 'burn';

  const progressBarColor = {
    accent: 'bg-accent-strong',
    burn: 'bg-orange-400',
    warn: 'bg-warning-strong',
  }[progressColor] || 'bg-accent-strong';

  return (
    <div
      className={[
        'group glass-card rounded-xl p-5 transition-[transform,box-shadow] duration-short ease-out',
        'hover:-translate-y-1 hover:shadow-card',
        warn ? 'border-warning/30' : '',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-3">
        <p className={`text-xs font-medium uppercase tracking-wide ${warn ? 'text-warning-strong' : burn ? 'text-orange-400' : 'text-muted'}`}>
          {label}
        </p>
        <span
          className={[
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
            'transition-transform duration-short ease-out group-hover:scale-110',
            warn ? 'bg-warning/20 text-warning-strong' : burn ? 'bg-orange-500/20 text-orange-400' : 'bg-accent-soft text-accent-strong',
          ].join(' ')}
        >
          <Icon size={18} strokeWidth={2.2} />
        </span>
      </div>
      <p
        className={`mt-2 font-display text-3xl font-bold [font-variant-numeric:tabular-nums] ${
          warn ? 'text-warning-strong' : burn ? 'text-orange-400' : 'text-ink'
        }`}
      >
        {value}
        <span className="ml-1 font-body text-base font-medium text-muted">{unit}</span>
      </p>
      {hint && <p className={`mt-1 text-xs ${warn ? 'text-warning-strong' : burn ? 'text-orange-400' : 'text-muted'}`}>{hint}</p>}

      {/* Thanh tiến trình calo */}
      {progress !== undefined && (
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-black/8">
          <div
            className={`h-full rounded-full transition-all duration-long ease-out ${progressBarColor}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
}
