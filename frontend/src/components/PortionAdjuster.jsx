import { useEffect, useState } from 'react';
import { Plus, Search, Trash2 } from 'lucide-react';
import { api } from '../lib/api.js';

const SCALES = [
  { value: 0.7, label: 'Ít', hint: '70%' },
  { value: 1, label: 'Vừa', hint: '100%' },
  { value: 1.3, label: 'Nhiều', hint: '130%' },
];

export function portionTotals(items) {
  const sum = (key) => items.reduce((total, item) => total + (item.per_100g[key] * item.grams) / 100, 0);
  return {
    kcal: Math.round(sum('energy_kcal')),
    protein: Math.round(sum('protein_g') * 10) / 10,
    carb: Math.round(sum('carb_g') * 10) / 10,
    fat: Math.round(sum('fat_g') * 10) / 10,
  };
}

const sliderMax = (item) => Math.max(300, Math.ceil((item.ai_grams || item.grams) * 2 / 10) * 10);

// Chỉnh gram từng thành phần; kcal tính lại ngay, số cuối cùng do server tính khi lưu.
export default function PortionAdjuster({ items, onChange }) {
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState([]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setMatches([]);
      return undefined;
    }
    let active = true;
    const timer = window.setTimeout(() => {
      api.foodComposition(q).then((rows) => { if (active) setMatches(rows); }).catch(() => { if (active) setMatches([]); });
    }, 250);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query]);

  const setGrams = (index, value) => {
    const grams = Math.min(3000, Math.max(1, Number(value) || 1));
    onChange(items.map((item, i) => (i === index ? { ...item, grams } : item)));
  };

  const applyScale = (factor) => onChange(items.map((item) => ({
    ...item,
    grams: Math.max(1, Math.round((item.ai_grams || item.grams) * factor)),
  })));

  const addFood = (food) => {
    if (!items.some((item) => item.fct_code === food.code)) {
      onChange([...items, {
        name: food.name_vi,
        grams: 100,
        ai_grams: 0,
        source: 'FCT',
        fct_code: food.code,
        fct_name: food.name_vi,
        per_100g: {
          energy_kcal: food.energy_kcal,
          protein_g: food.protein_g ?? 0,
          carb_g: food.carb_g ?? 0,
          fat_g: food.fat_g ?? 0,
        },
      }]);
    }
    setQuery('');
    setMatches([]);
  };

  return (
    <section className="space-y-4 rounded-xl border border-black/5 bg-black/5 p-4" aria-labelledby="portion-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="portion-heading" className="text-sm font-bold text-ink">Thành phần và khẩu phần</h3>
          <p className="mt-0.5 text-xs text-ink-2">Gram do AI ước lượng từ ảnh, bạn có thể chỉnh lại.</p>
        </div>
        <div className="flex gap-1.5" role="group" aria-label="Chỉnh nhanh cả đĩa">
          {SCALES.map((scale) => (
            <button key={scale.value} type="button" onClick={() => applyScale(scale.value)}
              className="min-h-10 rounded-lg bg-white px-3 py-1 text-xs font-semibold text-ink-2 shadow-hairline hover:bg-paper-3">
              {scale.label} <span className="font-normal text-muted">{scale.hint}</span>
            </button>
          ))}
        </div>
      </div>

      <ul className="space-y-3">
        {items.map((item, index) => {
          const kcal = Math.round((item.per_100g.energy_kcal * item.grams) / 100);
          return (
            <li key={`${item.name}-${item.fct_code ?? 'ai'}`} className="rounded-lg bg-white p-3 shadow-hairline">
              <div className="flex flex-wrap items-center gap-2">
                <span className="min-w-0 basis-full text-sm font-semibold text-ink sm:flex-1 sm:basis-0">{item.name}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${item.source === 'FCT' ? 'bg-accent-soft text-accent-strong' : 'bg-warning-soft text-warning-strong'}`}
                  title={item.source === 'FCT' ? `Theo Bảng thành phần thực phẩm: ${item.fct_name}` : 'Chưa có trong bảng, dinh dưỡng do AI ước tính'}>
                  {item.source === 'FCT' ? 'Bảng Viện Dinh dưỡng' : 'AI ước tính'}
                </span>
                <span className="ml-auto w-16 text-right text-sm font-bold text-ink [font-variant-numeric:tabular-nums] sm:ml-0">{kcal} kcal</span>
                <button type="button" onClick={() => onChange(items.filter((_, i) => i !== index))}
                  aria-label={`Xóa ${item.name}`}
                  className="flex h-10 w-10 items-center justify-center rounded-full text-muted hover:bg-paper-3 hover:text-danger">
                  <Trash2 size={16} />
                </button>
              </div>
              <div className="mt-2 flex items-center gap-3">
                <input type="range" min="1" max={sliderMax(item)} step="5" value={Math.min(item.grams, sliderMax(item))}
                  onChange={(e) => setGrams(index, e.target.value)} aria-label={`Khối lượng ${item.name}`}
                  className="h-2 min-w-0 flex-1 accent-[var(--color-accent-strong)]" />
                <label className="flex items-center gap-1 text-xs text-ink-2">
                  <input type="number" min="1" max="3000" value={item.grams} onChange={(e) => setGrams(index, e.target.value)}
                    aria-label={`Số gram ${item.name}`}
                    className="min-h-10 w-20 rounded-md border border-black/10 bg-white px-2 text-right text-sm text-ink" />
                  g
                </label>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="relative">
        <label className="flex min-h-10 items-center gap-2 rounded-lg border border-black/10 bg-white px-3">
          <Search size={15} className="shrink-0 text-muted" aria-hidden="true" />
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Thêm thành phần còn thiếu"
            aria-label="Tìm thành phần trong Bảng thành phần thực phẩm" className="min-w-0 flex-1 bg-transparent py-2 text-sm text-ink outline-none" />
        </label>
        {matches.length > 0 && (
          <ul className="absolute z-10 mt-1 max-h-56 w-full overflow-auto rounded-lg bg-white py-1 shadow-card">
            {matches.map((food) => (
              <li key={food.code}>
                <button type="button" onClick={() => addFood(food)}
                  className="flex min-h-10 w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-ink hover:bg-paper-3">
                  <Plus size={14} className="shrink-0 text-accent-strong" aria-hidden="true" />
                  <span className="min-w-0 flex-1">{food.name_vi}</span>
                  <span className="text-xs text-muted">{Math.round(food.energy_kcal)} kcal/100 g</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
