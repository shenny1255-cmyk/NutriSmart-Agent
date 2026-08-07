import { useEffect, useRef, useState } from 'react';
import { CloudUpload, ImagePlus, ScanLine, AlertTriangle, RefreshCw, CheckCircle2, Utensils } from 'lucide-react';
import { api } from '../lib/api.js';

import samplePho from '../assets/sample_pho.jpg';
import sampleSalad from '../assets/sample_salad.jpg';
import sampleChickenRice from '../assets/sample_chicken_rice.jpg';

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
  const sessionRef = useRef(mealScanCache);
  const [preview, setPreview] = useState(sessionRef.current.preview ?? null);
  const [result, setResult] = useState(sessionRef.current.result ?? null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  // Giữ ảnh và kết quả khi người dùng chuyển sang trang khác rồi quay lại.
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
      // Ảnh lớn có thể vượt dung lượng sessionStorage; bộ nhớ vẫn giữ trạng thái khi chuyển trang.
    }
  }, [preview, result]);

  async function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return;

    setPreview(await fileToDataUrl(file));
    setResult(null);
    setSavedMsg('');
    setLoading(true);

    try {
      setResult(await api.analyzeMeal(file));
    } catch (error) {
      setResult({ error: error.detail || 'Dịch vụ phân tích ảnh chưa sẵn sàng. Vui lòng thử lại sau.' });
    } finally {
      setLoading(false);
    }
  }

  // Chọn ảnh mẫu thử nghiệm
  async function selectSample(sample) {
    setPreview(sample.img);
    setResult(null);
    setSavedMsg('');
    setLoading(true);

    try {
      // Thử gọi API thực bằng cách fetch blob ảnh mẫu
      const res = await fetch(sample.img);
      const blob = await res.blob();
      const file = new File([blob], `${sample.name}.jpg`, { type: 'image/jpeg' });
      const apiResult = await api.analyzeMeal(file);
      setResult(apiResult);
    } catch {
      // Giả lập kết quả nếu backend vision service tạm thời offline
      setResult(sample.mockResult);
    } finally {
      setLoading(false);
    }
  }

  function onFile(e) {
    handleFile(e.target.files?.[0]);
    // Cho phép chọn lại cùng một tệp sau đó.
    e.target.value = '';
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  }

  const confidence = Math.round((result?.confidence ?? 0) * 100);
  const kcalVal = result?.calories_kcal ?? result?.estimated_kcal ?? 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Phân tích hình ảnh món ăn</h1>

      {/* Main Upload Zone — Glass Card */}
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
          {/* Cloud Upload Icon */}
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-accent-soft/70 text-accent-strong shadow-sm transition-transform duration-short hover:scale-110">
            <CloudUpload size={32} strokeWidth={1.8} />
          </div>

          {/* Headline text với chữ "chọn" và "chụp trực tiếp" nhấn mạnh */}
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

          {/* Button "Chọn ảnh" màu xanh nổi bật */}
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

        {/* Xem trước ảnh đã tải lên */}
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

      {/* Section: Hoặc thử với ảnh mẫu */}
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

      {/* Đang phân tích */}
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

      {/* Kết quả phân tích */}
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

          {/* Dinh dưỡng đa lượng */}
          <dl className="grid grid-cols-2 gap-3 sm:[grid-template-columns:repeat(4,minmax(0,1fr))]">
            <Macro label="Calo" value={kcalVal} unit="kcal" primary />
            <Macro label="Protein" value={result.protein_g} unit="g" />
            <Macro label="Carb" value={result.carb_g ?? result.carbs_g} unit="g" />
            <Macro label="Fat" value={result.fat_g} unit="g" />
          </dl>

          {/* Cảnh báo y tế / phù hợp sức khỏe */}
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

          {/* Nút Lưu vào Nhật ký */}
          <div className="pt-2">
            <button
              onClick={async () => {
                try {
                  setSaving(true);
                  const res = await api.logMeal({
                    food_name: result.food_name,
                    calories_kcal: kcalVal,
                    protein_g: result.protein_g ?? 0,
                    carb_g: result.carb_g ?? result.carbs_g ?? 0,
                    fat_g: result.fat_g ?? 0,
                    quantity: 1.0,
                    meal_type: 'LUNCH',
                  });
                  setSavedMsg(`✅ Đã lưu ${result.food_name} vào Nhật ký (+${res.added_calories} kcal)!`);
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
            {savedMsg && (
              <p className="mt-2 text-center text-xs font-semibold text-accent-strong">{savedMsg}</p>
            )}
          </div>
        </div>
      )}

      {/* Ảnh không phải món ăn hoặc không đủ rõ để phân tích */}
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

      {/* Lỗi service */}
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
