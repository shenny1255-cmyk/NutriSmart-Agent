import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from 'recharts';
import { api } from '../lib/api.js';

const MOCK = Array.from({ length: 7 }, (_, i) => ({
  day: `T${i + 2}`,
  kcal_intake: 1800 + Math.round(Math.random() * 500),
  kcal_burned: 300 + Math.round(Math.random() * 300),
}));

export default function Dashboard() {
  const [data, setData] = useState(MOCK);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    api.dailySummary(7)
      .then(setData)
      .catch(() => setOffline(true));   // backend chưa chạy → giữ MOCK
  }, []);

  const today = data.at(-1) ?? {};
  const target = today.daily_calorie_target ?? 2000;
  const remaining = target - (today.kcal_intake ?? 0) + (today.kcal_burned ?? 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tổng quan</h1>
      {offline && (
        <p className="text-sm text-amber-600">
          Chưa kết nối backend — đang hiển thị dữ liệu mẫu.
        </p>
      )}

      <div className="grid grid-cols-3 gap-4">
        <Stat label="Mục tiêu hôm nay" value={`${target} kcal`} />
        <Stat label="Đã nạp" value={`${today.kcal_intake ?? 0} kcal`} />
        <Stat
          label={remaining >= 0 ? 'Còn lại' : 'Dư thừa'}
          value={`${Math.abs(remaining)} kcal`}
          warn={remaining < 0}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-4 font-semibold">Calo nạp vào / tiêu hao (7 ngày)</h2>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="day" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip />
            <Line type="monotone" dataKey="kcal_intake" name="Nạp vào" stroke="#059669" strokeWidth={2} />
            <Line type="monotone" dataKey="kcal_burned" name="Tiêu hao" stroke="#f59e0b" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

function Stat({ label, value, warn }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${warn ? 'text-amber-600' : 'text-slate-900'}`}>
        {value}
      </p>
    </div>
  );
}