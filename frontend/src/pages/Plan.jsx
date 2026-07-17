import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function Plan() {
  const [plan, setPlan] = useState(null);
  const [err, setErr] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);

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
    } catch (e) {
      setErr('Có lỗi khi tạo lộ trình: ' + e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  if (err && !plan) {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 rounded-xl border border-slate-200 bg-white p-8 text-center max-w-4xl">
        <h2 className="text-xl font-bold text-slate-700">Chưa có lộ trình nào</h2>
        <p className="text-sm text-slate-500">Hệ thống chưa tạo lộ trình dinh dưỡng cho bạn.</p>
        <button
          onClick={handleGeneratePlan}
          disabled={isGenerating}
          className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
        >
          {isGenerating ? '✨ AI đang suy nghĩ (có thể mất 15-30s)…' : 'Tạo lộ trình cá nhân hóa mới'}
        </button>
        {err && !err.includes('HTTP 404') && <p className="text-sm text-red-600">{err}</p>}
      </div>
    );
  }

  if (!plan) return <p className="text-sm text-slate-500">Đang tải…</p>;

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Lộ trình cá nhân hóa</h1>
        <button
          onClick={handleGeneratePlan}
          disabled={isGenerating}
          className="rounded-lg border border-emerald-600 px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
        >
          {isGenerating ? 'Đang tạo lại...' : '🔄 Tạo lộ trình mới'}
        </button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="font-semibold">
          Phiên bản {plan.version} · {plan.start_date} → {plan.end_date}
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Mục tiêu: <b>{plan.goal}</b> · {plan.daily_kcal_target} kcal/ngày
          {plan.bmi && <span> · BMI: <b>{plan.bmi}</b></span>}
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