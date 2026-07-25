import { useEffect, useMemo, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';
import { Target, Flame, Scale, Footprints } from 'lucide-react';
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

export default function Dashboard() {
  const [data, setData] = useState(MOCK);
  const [offline, setOffline] = useState(false);
  const [activity, setActivity] = useState({ steps: 0, calories_burned: 0 });
  const [syncStatus, setSyncStatus] = useState(null); // null | 'ok' | 'error'

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

  const t = useTokens([
    '--color-accent', '--color-warning', '--color-warning-strong', '--color-rule-2',
    '--color-muted', '--color-paper-2', '--color-rule', '--color-ink',
  ]);

  const today = data.at(-1) ?? {};
  const target = today.daily_calorie_target ?? 2000;
  // Sử dụng kcal_burned từ activity (Mobile sync) hoặc từ backend summary
  const burnedKcal = activity.calories_burned || today.kcal_burned || 0;
  const remaining = target - (today.kcal_intake ?? 0) + burnedKcal;
  const over = remaining < 0;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
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
      </header>

      {/* Stats — 1 cột mobile, 4 cột từ md */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:[grid-template-columns:repeat(4,minmax(0,1fr))]">
        <Stat icon={Target} label="Mục tiêu hôm nay" value={target} unit="kcal" />
        <Stat icon={Flame} label="Đã nạp" value={today.kcal_intake ?? 0} unit="kcal" />
        <Stat
          icon={Footprints}
          label="Đã tiêu hao"
          value={Math.round(burnedKcal)}
          unit="kcal"
          tone="burn"
          hint={activity.steps > 0 ? `${activity.steps.toLocaleString()} bước chân` : undefined}
        />
        <Stat
          icon={Scale}
          label={over ? 'Dư thừa' : 'Còn lại'}
          value={Math.abs(Math.round(remaining))}
          unit="kcal"
          tone={over ? 'warn' : 'ok'}
          hint={over ? 'Vượt mục tiêu hôm nay' : undefined}
        />
      </div>

      <section className="rounded-md bg-paper-2 p-5 shadow-hairline">
        <h2 className="mb-4 font-display text-base font-semibold">
          Calo nạp vào / tiêu hao <span className="font-body font-normal text-muted">· 7 ngày</span>
        </h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
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
                background: t['--color-paper-2'],
                border: `1px solid ${t['--color-rule']}`,
                borderRadius: 'var(--radius-sm)',
                boxShadow: 'var(--shadow-whisper)',
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
            <Line
              type="monotone"
              dataKey="kcal_intake"
              name="Nạp vào"
              stroke={t['--color-accent']}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: t['--color-paper-2'] }}
            />
            <Line
              type="monotone"
              dataKey="kcal_burned"
              name="Tiêu hao"
              stroke={t['--color-warning']}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, strokeWidth: 2, stroke: t['--color-paper-2'] }}
            />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

function Stat({ icon: Icon, label, value, unit, tone = 'neutral', hint }) {
  const warn = tone === 'warn';
  const burn = tone === 'burn';
  return (
    <div
      className={[
        'group rounded-md p-5 transition-[transform,box-shadow] duration-short ease-out',
        'hover:-translate-y-0.5 hover:shadow-card',
        warn ? 'bg-warning-soft shadow-hairline' : 'bg-paper-2 shadow-hairline',
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
    </div>
  );
}