import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function Plan() {
  const [plan, setPlan] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.activePlan().then(setPlan).catch((e) => setErr(e.message));
  }, []);

if (err)   return <p className="text-sm text-amber-600">Chưa kết nối backend — chưa có lộ trình.</p>;
if (!plan) return <p className="text-sm text-slate-500">Đang tải…</p>;

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold">Lộ trình cá nhân hóa</h1>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">
          Phiên bản {plan.version} · {plan.start_date} → {plan.end_date}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Mục tiêu: <b>{plan.goal}</b> · {plan.daily_kcal_target} kcal/ngày
        </p>
      </div>

      {(plan.content?.days ?? []).map((d, i) => (
        <div key={i} className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-3 font-semibold">Ngày {i + 1}</h3>
          <ul className="space-y-2 text-sm">
            {d.meals?.map((m, j) => (
              <li key={j} className="flex justify-between border-b border-slate-100 pb-2">
                <span><b>{m.type}:</b> {m.name}</span>
                <span className="text-slate-500">{m.kcal} kcal</span>
              </li>
            ))}
          </ul>
          {d.exercise && <p className="mt-3 text-sm text-emerald-700">🏃 {d.exercise}</p>}
        </div>
      ))}
    </div>
  );
}