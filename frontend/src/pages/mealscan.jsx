import { useRef, useState } from 'react';
import { Upload, ImagePlus, ScanLine, AlertTriangle, RefreshCw } from 'lucide-react';
import { api } from '../lib/api.js';

export default function MealScan() {
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) return;

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

  function onFile(e) {
    handleFile(e.target.files?.[0]);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  }

  const confidence = Math.round((result?.confidence ?? 0) * 100);

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="font-display text-2xl font-bold tracking-tight">Phân tích ảnh món ăn</h1>

      {/* Khung upload — kéo thả + click + camera mobile */}
      <div className="rounded-md bg-paper-2 p-5 shadow-hairline">
        <label
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={[
            'flex cursor-pointer flex-col items-center gap-3 rounded-md border-2 border-dashed py-10 px-4 text-center',
            'transition-[border-color,background-color,transform] duration-short ease-out',
            'has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus',
            dragging
              ? 'scale-[1.01] border-accent bg-accent-soft'
              : 'border-rule hover:border-accent hover:bg-paper-3 active:bg-paper-3',
          ].join(' ')}
        >
          <span
            className={[
              'flex h-12 w-12 items-center justify-center rounded-full transition-colors duration-short ease-out',
              dragging ? 'bg-accent text-accent-ink' : 'bg-accent-soft text-accent-strong',
            ].join(' ')}
          >
            {preview ? <ImagePlus size={22} /> : <Upload size={22} />}
          </span>
          <span className="text-sm font-medium text-ink-2">
            {dragging
              ? 'Thả ảnh vào đây'
              : preview
                ? 'Chọn hoặc kéo thả ảnh khác'
                : 'Kéo thả, chọn hoặc chụp ảnh món ăn'}
          </span>
          <span className="text-xs text-muted">PNG, JPG — chụp trực tiếp trên điện thoại được</span>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={onFile}
            className="sr-only"
          />
        </label>

        {preview && (
          <div className="mt-4 overflow-hidden rounded-md bg-paper-3">
            <img
              src={preview}
              alt="Ảnh món ăn đã chọn"
              className="mx-auto max-h-64 object-contain"
            />
          </div>
        )}
      </div>

      {/* Đang phân tích */}
      {loading && (
        <div className="flex items-center gap-3 rounded-md bg-paper-2 p-4 shadow-hairline" aria-busy="true">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
            <ScanLine size={17} className="animate-pulse" />
          </span>
          <p className="text-sm text-ink-2">Đang nhận diện món ăn…</p>
        </div>
      )}

      {/* Kết quả */}
      {result && !result.error && (
        <div className="space-y-4 rounded-md bg-paper-2 p-5 shadow-hairline">
          <header className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-display text-lg font-semibold">{result.food_name ?? 'Kết quả'}</h2>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted">Độ tin cậy</span>
              <span
                className="h-1.5 w-20 overflow-hidden rounded-full bg-paper-3"
                role="img"
                aria-label={`Độ tin cậy ${confidence}%`}
              >
                <span
                  className="block h-full rounded-full bg-accent transition-[width] duration-long ease-out"
                  style={{ width: `${confidence}%` }}
                />
              </span>
              <span className="text-xs font-medium text-ink-2 [font-variant-numeric:tabular-nums]">{confidence}%</span>
            </div>
          </header>

          {/* Dinh dưỡng đa lượng — kcal nổi bật, 3 macro phụ */}
          <dl className="grid grid-cols-2 gap-3 sm:[grid-template-columns:repeat(4,minmax(0,1fr))]">
            <Macro label="Calo" value={result.estimated_kcal} unit="kcal" primary />
            <Macro label="Protein" value={result.protein_g} unit="g" />
            <Macro label="Carb" value={result.carb_g ?? result.carbs_g} unit="g" />
            <Macro label="Fat" value={result.fat_g} unit="g" />
          </dl>

          {/* Cảnh báo y tế / dị ứng — khối nổi bật tương phản cao */}
          {result.suitability_note && (
            <aside
              role="alert"
              className="flex gap-3 rounded-md border-l-4 border-warning-strong bg-warning-soft p-4"
            >
              <AlertTriangle size={20} className="mt-0.5 shrink-0 text-warning-strong" />
              <div className="min-w-0">
                <p className="text-sm font-semibold text-warning-strong">Lưu ý phù hợp sức khỏe</p>
                <p className="mt-1 text-sm text-ink-2">{result.suitability_note}</p>
              </div>
            </aside>
          )}
        </div>
      )}

      {/* Lỗi service */}
      {result?.error && (
        <div className="flex items-center justify-between gap-3 rounded-md bg-danger-soft p-4">
          <p className="text-sm font-medium text-danger">{result.error}</p>
          <button
            onClick={() => inputRef.current?.value && handleFile(inputRef.current.files?.[0])}
            className="flex min-h-11 items-center gap-2 rounded-md bg-paper-2 px-3 py-2 text-sm font-medium text-ink-2 shadow-hairline transition-colors duration-short ease-out hover:bg-paper-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <RefreshCw size={15} />
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
        'rounded-md p-3 text-center transition-[transform,box-shadow] duration-short ease-out hover:-translate-y-0.5 hover:shadow-whisper',
        primary ? 'bg-accent-soft' : 'bg-paper-3',
      ].join(' ')}
    >
      <dt className={`text-xs font-medium uppercase tracking-wide ${primary ? 'text-accent-strong' : 'text-muted'}`}>
        {label}
      </dt>
      <dd
        className={[
          'mt-1 font-display text-xl font-bold [font-variant-numeric:tabular-nums]',
          primary ? 'text-accent-strong' : 'text-ink',
        ].join(' ')}
      >
        {has ? value : '—'}
        {has && <span className="ml-1 font-body text-xs font-medium text-muted">{unit}</span>}
      </dd>
    </div>
  );
}