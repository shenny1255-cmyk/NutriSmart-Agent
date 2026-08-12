import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloudUpload, ImagePlus, ScanLine, AlertTriangle, RefreshCw, Utensils, Check, Calendar } from 'lucide-react';
import { api } from '../lib/api.js';

import samplePho from '../assets/sample_pho.jpg';
import sampleSalad from '../assets/sample_salad.jpg';
import sampleChickenRice from '../assets/sample_chicken_rice.jpg';

const MEAL_TYPES = [
  { value: 'BREAKFAST', label: 'Bữa Sáng' },
  { value: 'LUNCH', label: 'Bữa Trưa' },
  { value: 'DINNER', label: 'Bữa Tối' },
  { value: 'SNACK', label: 'Bữa Phụ' },
];

const PORTIONS = [
  { value: 0.5, label: '0.5 phần' },
  { value: 1.0, label: '1 phần (chuẩn)' },
  { value: 1.5, label: '1.5 phần' },
  { value: 2.0, label: '2 phần' },
];

function getSuggestedMealType() {
  const hour = new Date().getHours() + new Date().getMinutes() / 60;
  if (hour >= 5 && hour < 10.5) return 'BREAKFAST';
  if (hour >= 10.5 && hour < 14) return 'LUNCH';
  if (hour >= 14 && hour < 17.5) return 'SNACK';
  return 'DINNER';
}

const SAMPLE_FOODS = [
  {
    name: 'Phở bò',
    img: samplePho,
    mockResult: {
      food_name: 'Phở bò Việt Nam',
      confidence: 0.95,
      calories_kcal: 450,
      protein_g: 22.5,
      carb_g: 65.0,
      fat_g: 10.2,
      suitability_note: 'Món ăn giàu dinh dưỡng. Chú ý lượng muối trong nước dùng nếu có bệnh huyết áp.',
    },
  },
  {
    name: 'Salad Gà & Bơ',
    img: sampleSalad,
    mockResult: {
      food_name: 'Salad Gà & Bơ',
      confidence: 0.92,
      calories_kcal: 380,
      protein_g: 28.0,
      carb_g: 15.0,
      fat_g: 22.0,
      suitability_note: 'Món ăn rất lành mạnh, giàu protein và chất xơ. Phù hợp cho mục tiêu giảm cân.',
    },
  },
  {
    name: 'Cơm Gà',
    img: sampleChickenRice,
    mockResult: {
      food_name: 'Cơm Gà Xối Mỡ',
      confidence: 0.89,
      calories_kcal: 620,
      protein_g: 32.0,
      carb_g: 72.0,
      fat_g: 21.0,
      suitability_note: 'Lượng calo và tinh bột khá cao. Phù hợp cho ngày có hoạt động thể chất nhiều.',
    },
  },
];

const MEAL_SCAN_SESSION_KEY = 'nutrismart_meal_scan';

function loadMealScanSession() {
  try {
    return JSON.parse(sessionStorage.getItem(MEAL_SCAN_SESSION_KEY)) || {};
  } catch {
    return {};
  }
}

let mealScanCache = loadMealScanSession();

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function MealScan() {
  const navigate = useNavigate();
  const sessionRef = useRef(mealScanCache);
  const [preview, setPreview] = useState(sessionRef.current.preview ?? null);
  const [result, setResult] = useState(sessionRef.current.result ?? null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [portion, setPortion] = useState(1.0);
  const [mealType, setMealType] = useState(getSuggestedMealType());
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    mealScanCache = { preview, result };
    try {
      if (!preview && !result) {
        sessionStorage.removeItem(MEAL_SCAN_SESSION_KEY);
        return;
      }
      sessionStorage.setItem(
        MEAL_SCAN_SESSION_KEY,
        JSON.stringify(mealScanCache),
      );
    } catch {
      // Ignore storage errors for large images
    }
  }, [preview, result]);

  async function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return;

    setPreview(await fileToDataUrl(file));
    setResult(null);
    setIsSaved(false);
    setSavedMsg('');
    setPortion(1.0);
    setMealType(getSuggestedMealType());
    setLoading(true);

    try {
      setResult(await api.analyzeMeal(file));
    } catch (error) {
      setResult({ error: error.detail || 'Dịch vụ phân tích ảnh chưa sẵn sàng. Vui lòng thử lại sau.' });
    } finally {
      setLoading(false);
    }
  }

  async function selectSample(sample) {
    setPreview(sample.img);
    setResult(null);
    setIsSaved(false);
    setSavedMsg('');
    setPortion(1.0);
    setMealType(getSuggestedMealType());
    setLoading(true);

    try {
      const res = await fetch(sample.img);
      const blob = await res.blob();
      const file = new File([blob], `${sample.name}.jpg`, { type: 'image/jpeg' });
      const apiResult = await api.analyzeMeal(file);
      setResult(apiResult);
    } catch {
      setResult(sample.mockResult);
    } finally {
      setLoading(false);
    }
  }

  function onFile(e) {
    handleFile(e.target.files?.[0]);
    e.target.value = '';
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  }

  const confidence = Math.round((result?.confidence ?? 0) * 100);
  const baseKcal = result?.calories_kcal ?? result?.estimated_kcal ?? 0;
  const kcalVal = Math.round(baseKcal * portion);
  const proteinVal = result?.protein_g ? Math.round(result.protein_g * portion * 10) / 10 : null;
  const carbVal = (result?.carb_g ?? result?.carbs_g) ? Math.round((result.carb_g ?? result.carbs_g) * portion * 10) / 10 : null;
  const fatVal = result?.fat_g ? Math.round(result.fat_g * portion * 10) / 10 : null;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Phân tích hình ảnh món ăn</h1>

      <div className="glass-card rounded-2xl p-6 sm:p-8">
        {!preview && (
          <label
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={[
              'relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed py-10 px-6 text-center transition-all duration-short ease-out',
              dragging
                ? 'scale-[1.01] border-accent-strong bg-accent-soft/50'
                : 'border-accent/40 bg-white/30 hover:border-accent-strong hover:bg-white/50',
            ].join(' ')}
          >
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft/70 text-accent-strong shadow-sm transition-transform duration-short hover:scale-110">
              <CloudUpload size={32} strokeWidth={1.8} />
            </div>

            <p className="max-w-md font-body text-base text-ink-2">
              Kéo thả,{' '}
              <span className="font-bold text-accent-strong underline decoration-accent/40 underline-offset-2">
                chọn
              </span>{' '}
              hoặc{' '}
              <span className="font-bold text-accent-strong">
                chụp trực tiếp
              </span>{' '}
              ảnh món ăn của bạn
            </p>

            <p className="mt-2 text-xs text-muted">
              Hỗ trợ định dạng <b>PNG, JPG</b>. Chụp trên điện thoại rất nhanh!
            </p>

            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="mt-5 inline-flex min-h-10 items-center justify-center rounded-full bg-accent-strong px-6 py-2 text-sm font-semibold text-white shadow-whisper transition-all duration-short ease-out hover:-translate-y-0.5 hover:shadow-card active:translate-y-0"
            >
              Chọn ảnh
            </button>
          </label>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={onFile}
          className="sr-only"
        />

        {preview && (
          <div className="overflow-hidden rounded-xl bg-black/5 p-2 backdrop-blur-sm">
            <img
              src={preview}
              alt="Ảnh món ăn"
              className="mx-auto max-h-72 rounded-lg object-contain"
            />
            <div className="flex justify-center p-3 pb-1">
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                disabled={loading}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-full bg-white px-5 py-2 text-sm font-semibold text-accent-strong shadow-hairline transition-all duration-short ease-out hover:-translate-y-0.5 hover:shadow-card disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ImagePlus size={17} />
                Chọn ảnh khác
              </button>
            </div>
          </div>
        )}
      </div>

      {!loading && !result && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-ink-2">Hoặc thử với ảnh mẫu:</p>
          <div className="flex flex-wrap gap-4">
            {SAMPLE_FOODS.map((sample, idx) => (
              <button
                key={idx}
                onClick={() => selectSample(sample)}
                className="group flex flex-col items-center gap-1.5 transition-transform duration-short hover:scale-105"
              >
                <div className="h-16 w-16 overflow-hidden rounded-full border-2 border-white/60 shadow-whisper transition-all group-hover:border-accent-strong group-hover:shadow-card">
                  <img src={sample.img} alt={sample.name} className="h-full w-full object-cover" />
                </div>
                <span className="text-xs font-medium text-ink-2 group-hover:text-accent-strong">
                  {sample.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="glass-card flex items-center gap-4 rounded-xl p-5" aria-busy="true">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
            <ScanLine size={20} className="animate-pulse" />
          </span>
          <div>
            <p className="font-semibold text-ink">Gemini AI đang phân tích đĩa thức ăn…</p>
            <p className="text-xs text-muted">Nhận diện tên món, lượng calo và thành phần dinh dưỡng</p>
          </div>
        </div>
      )}

      {result && !result.error && result.is_food_image !== false && (
        <div className="glass-card space-y-5 rounded-2xl p-6">
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-black/5 pb-4">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wide text-accent-strong">Món ăn nhận diện</span>
              <h2 className="font-display text-xl font-bold text-ink">{result.food_name ?? 'Kết quả'}</h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">Độ tin cậy</span>
              <span
                className="h-2 w-20 overflow-hidden rounded-full bg-black/10"
                role="img"
                aria-label={`Độ tin cậy ${confidence}%`}
              >
                <span
                  className="block h-full rounded-full bg-accent-strong transition-[width] duration-long ease-out"
                  style={{ width: `${confidence}%` }}
                />
              </span>
              <span className="text-xs font-bold text-ink-2 [font-variant-numeric:tabular-nums]">{confidence}%</span>
            </div>
          </header>

          {!isSaved && (
            <div className="grid grid-cols-1 gap-4 rounded-xl border border-black/5 bg-black/5 p-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wide text-ink-2">Khẩu phần ăn</label>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {PORTIONS.map((p) => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setPortion(p.value)}
                      className={[
                        'rounded-lg px-3 py-1.5 text-xs font-semibold transition-all',
                        portion === p.value
                          ? 'bg-accent-strong text-white shadow-sm'
                          : 'bg-white text-ink-2 hover:bg-paper-3',
                      ].join(' ')}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wide text-ink-2">Bữa ăn</label>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {MEAL_TYPES.map((m) => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setMealType(m.value)}
                      className={[
                        'rounded-lg px-3 py-1.5 text-xs font-semibold transition-all',
                        mealType === m.value
                          ? 'bg-accent-strong text-white shadow-sm'
                          : 'bg-white text-ink-2 hover:bg-paper-3',
                      ].join(' ')}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <dl className="grid grid-cols-2 gap-3 sm:[grid-template-columns:repeat(4,minmax(0,1fr))]">
            <Macro label="Calo" value={kcalVal} unit="kcal" primary />
            <Macro label="Protein" value={proteinVal} unit="g" />
            <Macro label="Carb" value={carbVal} unit="g" />
            <Macro label="Fat" value={fatVal} unit="g" />
          </dl>

          {result.suitability_note && (
            <aside
              role="alert"
              className="flex gap-3 rounded-xl border-l-4 border-warning-strong bg-warning-soft/70 p-4"
            >
              <AlertTriangle size={20} className="mt-0.5 shrink-0 text-warning-strong" />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-warning-strong">Lưu ý sức khỏe</p>
                <p className="mt-1 text-sm text-ink-2">{result.suitability_note}</p>
              </div>
            </aside>
          )}

          <div className="space-y-3 pt-2">
            {!isSaved ? (
              <button
                type="button"
                onClick={async () => {
                  try {
                    setSaving(true);
                    const res = await api.logMeal({
                      food_name: result.food_name,
                      calories_kcal: kcalVal,
                      protein_g: proteinVal ?? 0,
                      carb_g: carbVal ?? 0,
                      fat_g: fatVal ?? 0,
                      quantity: portion,
                      meal_type: mealType,
                    });
                    setIsSaved(true);
                    setSavedMsg(`✅ Đã lưu ${result.food_name} (${portion} phần) vào Nhật ký (+${res.added_calories} kcal)!`);
                  } catch (e) {
                    alert(e.detail || 'Vui lòng đăng nhập để lưu bữa ăn.');
                  } finally {
                    setSaving(false);
                  }
                }}
                disabled={saving}
                className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-accent-strong px-4 py-2.5 text-sm font-semibold text-white shadow-whisper transition-all duration-short ease-out hover:-translate-y-0.5 hover:shadow-card disabled:opacity-50"
              >
                <Utensils size={16} />
                {saving ? 'Đang lưu...' : `Lưu vào Nhật ký bữa ăn (+${kcalVal} kcal)`}
              </button>
            ) : (
              <div className="space-y-3">
                <button
                  type="button"
                  disabled
                  className="flex min-h-11 w-full cursor-not-allowed items-center justify-center gap-2 rounded-xl bg-paper-3 px-4 py-2.5 text-sm font-semibold text-ink-2 opacity-90 shadow-hairline"
                >
                  <Check size={18} className="text-accent-strong" />
                  Đã lưu vào Nhật ký bữa ăn (+{kcalVal} kcal)
                </button>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => navigate('/diary')}
                    className="flex min-h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-accent-strong px-4 py-2 text-sm font-semibold text-white shadow-whisper hover:bg-accent-strong/90"
                  >
                    <Calendar size={16} />
                    Xem Nhật ký
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreview(null);
                      setResult(null);
                      setIsSaved(false);
                      setSavedMsg('');
                    }}
                    className="flex min-h-10 flex-1 items-center justify-center gap-2 rounded-xl border border-rule-2 bg-paper-2 px-4 py-2 text-sm font-semibold text-ink-2 hover:bg-paper-3"
                  >
                    <RefreshCw size={16} />
                    Quét món khác
                  </button>
                </div>
              </div>
            )}

            {savedMsg && (
              <p className="mt-2 text-center text-xs font-semibold text-accent-strong">{savedMsg}</p>
            )}
          </div>
        </div>
      )}

      {result?.is_food_image === false && (
        <div className="glass-card rounded-xl border border-warning-strong/30 bg-warning-soft/90 p-5" role="alert">
          <div className="flex gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/70 text-warning-strong">
              <AlertTriangle size={21} />
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-ink">Không nhận diện được món ăn</h2>
              <p className="mt-1.5 text-base leading-relaxed text-ink-2">
                {result.rejection_reason || 'Ảnh này dường như không chứa món ăn hoặc món ăn không đủ rõ để phân tích.'}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-muted">Hãy chụp món ăn đủ sáng, rõ nét và nằm ở giữa khung hình.</p>
            </div>
          </div>
        </div>
      )}

      {result?.error && (
        <div className="glass-card flex items-center justify-between gap-3 rounded-xl bg-danger-soft/80 p-4">
          <p className="text-sm font-medium text-danger">{result.error}</p>
          <button
            onClick={() => inputRef.current?.click()}
            className="flex min-h-9 items-center gap-2 rounded-lg bg-white px-3 py-1.5 text-xs font-medium text-ink-2 shadow-hairline hover:bg-paper-3"
          >
            <RefreshCw size={14} />
            Thử lại
          </button>
        </div>
      )}
    </div>
  );
}

function Macro({ label, value, unit, primary }) {
  const has = value !== undefined && value !== null;
  return (
    <div
      className={[
        'rounded-xl p-3.5 text-center transition-[transform,box-shadow] duration-short ease-out hover:-translate-y-0.5',
        primary ? 'bg-accent-soft/80 text-accent-strong border border-accent/20' : 'bg-white/50 text-ink',
      ].join(' ')}
    >
      <dt className={`text-xs font-semibold uppercase tracking-wide ${primary ? 'text-accent-strong' : 'text-muted'}`}>
        {label}
      </dt>
      <dd className="mt-1 font-display text-xl font-bold [font-variant-numeric:tabular-nums]">
        {has ? value : '—'}
        {has && <span className="ml-1 font-body text-xs font-normal text-muted">{unit}</span>}
      </dd>
    </div>
  );
}
