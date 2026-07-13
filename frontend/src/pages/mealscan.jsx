import { useState } from 'react';
import { Upload } from 'lucide-react';
import { api } from '../lib/api.js';

export default function MealScan() {
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  async function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setPreview(URL.createObjectURL(file));
    setResult(null);
    setLoading(true);

    try {
      setResult(await api.analyzeMeal(file));
    } catch {
      setResult({ error: 'Vision Service chưa sẵn sàng.' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Phân tích ảnh món ăn</h1>

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <label className="flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-slate-300 py-12 hover:border-emerald-500">
          <Upload className="text-slate-400" />
          <span className="text-sm text-slate-500">Chọn hoặc chụp ảnh món ăn</span>
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={onFile}
            className="hidden"
          />
        </label>

        {preview && (
          <img src={preview} alt="preview" className="mt-4 max-h-64 rounded-lg object-contain" />
        )}
      </div>

      {loading && <p className="text-sm text-slate-500">Đang nhận diện…</p>}

      {result && !result.error && (
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 font-semibold">Kết quả</h2>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <Row label="Món ăn" value={result.food_name} />
            <Row label="Độ tin cậy" value={`${Math.round((result.confidence ?? 0) * 100)}%`} />
            <Row label="Calo ước tính" value={`${result.estimated_kcal} kcal`} />
            <Row label="Protein" value={`${result.protein_g} g`} />
          </dl>

          {result.suitability_note && (
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              {result.suitability_note}
            </p>
          )}
        </div>
      )}

      {result?.error && <p className="text-sm text-amber-600">{result.error}</p>}
    </div>
  );
}

const Row = ({ label, value }) => (
  <div>
    <dt className="text-xs uppercase text-slate-500">{label}</dt>
    <dd className="font-medium">{value ?? '—'}</dd>
  </div>
);