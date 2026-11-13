import { useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
} from 'recharts';
import {
  Plus, Trash2, UtensilsCrossed, Dumbbell, Scale, TrendingDown, TrendingUp, Maximize2, Eye, X,
} from 'lucide-react';
import { api } from '../lib/api.js';
import { isValidFoodName } from '../lib/validation.js';
import { Btn, Field, Select, Alert, Toast, useToast } from '../components/ui.jsx';

import samplePho from '../assets/sample_pho.jpg';
import sampleSalad from '../assets/sample_salad.jpg';
import sampleChickenRice from '../assets/sample_chicken_rice.jpg';

function getFoodImage(name = '') {
  const n = (name || '').toLowerCase();
  if (n.includes('phở') || n.includes('pho') || n.includes('bún') || n.includes('hủ tiếu') || n.includes('mì') || n.includes('mi')) return samplePho;
  if (n.includes('salad') || n.includes('rau') || n.includes('gỏi') || n.includes('bơ') || n.includes('trái cây') || n.includes('hoa quả')) return sampleSalad;
  if (n.includes('cơm') || n.includes('gà') || n.includes('thịt') || n.includes('bò') || n.includes('heo') || n.includes('cá') || n.includes('trứng')) return sampleChickenRice;
  return samplePho;
}

const MEAL_TYPES = [
  ['BREAKFAST', 'Bữa sáng'],
  ['LUNCH', 'Bữa trưa'],
  ['DINNER', 'Bữa tối'],
  ['SNACK', 'Bữa phụ'],
];
const MEAL_LABEL = Object.fromEntries(MEAL_TYPES);
const SOURCE_LABEL = {
  PLAN: 'Lộ trình',
  VISION: 'Phân tích ảnh',
  MOBILE: 'Thiết bị',
  MANUAL: 'Thủ công',
};

const homNay = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export default function Diary() {
  const [ngay, setNgay] = useState(homNay());
  const [meals, setMeals] = useState([]);
  const [acts, setActs] = useState([]);
  const [weights, setWeights] = useState([]);
  const [foods, setFoods] = useState([]);
  const [exercises, setExercises] = useState([]);
  const [err, setErr] = useState(null);
  const { toast, show } = useToast();

  useEffect(() => {
    api.foods().then((res) => setFoods(Array.isArray(res) ? res : [])).catch(() => setFoods([]));
    api.exercises().then((res) => setExercises(Array.isArray(res) ? res : [])).catch(() => setExercises([]));
    taiCanNang();
  }, []);

  useEffect(() => {
    taiNhatKy(ngay);
  }, [ngay]);

  const taiNhatKy = (d) => {
    api.meals(d).then((res) => setMeals(Array.isArray(res) ? res : [])).catch((e) => {
      setMeals([]);
      setErr(e.message);
    });
    api.activities(d).then((res) => setActs(Array.isArray(res) ? res : [])).catch((e) => {
      setActs([]);
      setErr(e.message);
    });
  };

  const taiCanNang = () => {
    api.weightHistory(90).then((res) => setWeights(Array.isArray(res) ? res : [])).catch(() => setWeights([]));
  };

  const safeMeals = Array.isArray(meals) ? meals : [];
  const safeActs = Array.isArray(acts) ? acts : [];
  const tongNap = safeMeals.reduce((s, m) => s + (Number(m.calories_kcal) || 0), 0);
  const tongDot = safeActs.reduce((s, a) => s + (Number(a.calories_burned) || 0), 0);

  return (
    <div className="max-w-4xl space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-bold tracking-tight">Nhật ký hằng ngày</h1>
        <label className="flex items-center gap-2 text-sm text-muted">
          Ngày
          <Field type="date" value={ngay} max={homNay()} onChange={(e) => setNgay(e.target.value || homNay())} />
        </label>
      </header>

      {err && <Alert tone="warning">{err}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2">
        <TongKet icon={UtensilsCrossed} label="Đã nạp" value={tongNap} tone="accent" />
        <TongKet icon={Dumbbell} label="Đã tiêu hao" value={tongDot} tone="info" />
      </div>

      <BuaAn
        ngay={ngay}
        meals={safeMeals}
        foods={Array.isArray(foods) ? foods : []}
        onSaved={(msg) => { taiNhatKy(ngay); show(msg); }}
        onError={(msg) => show(msg, 'danger')}
      />

      <VanDong
        ngay={ngay}
        acts={safeActs}
        exercises={Array.isArray(exercises) ? exercises : []}
        onSaved={(msg) => { taiNhatKy(ngay); show(msg); }}
        onError={(msg) => show(msg, 'danger')}
      />

      <CanNang
        weights={Array.isArray(weights) ? weights : []}
        onSaved={(msg) => { taiCanNang(); show(msg); }}
        onError={(msg) => show(msg, 'danger')}
      />

      <Toast toast={toast} position="top" />
    </div>
  );
}

function TongKet({ icon: Icon, label, value, tone }) {
  const accent = tone === 'accent';
  return (
    <div className="flex items-center gap-3 rounded-md bg-paper-2 p-4 shadow-hairline">
      <span className={`flex h-10 w-10 items-center justify-center rounded-full ${accent ? 'bg-accent-soft text-accent-strong' : 'bg-info-soft text-info'}`}>
        <Icon size={18} strokeWidth={2.2} />
      </span>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
        <p className="font-display text-2xl font-bold [font-variant-numeric:tabular-nums]">
          {Math.round(value || 0)}
          <span className="ml-1 font-body text-sm font-medium text-muted">kcal</span>
        </p>
      </div>
    </div>
  );
}

function KhungThe({ icon: Icon, title, subtitle, children }) {
  return (
    <section className="space-y-4 rounded-md bg-paper-2 p-5 shadow-hairline">
      <div className="flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
          <Icon size={17} strokeWidth={2.2} />
        </span>
        <div>
          <h2 className="font-display font-semibold">{title}</h2>
          {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function DongNhatKy({ chinh, phu, tri, nguon, onOpenDetail, onDelete, dangXoa }) {
  const imgSrc = getFoodImage(chinh);
  return (
    <li className="flex items-center gap-3 rounded-sm px-3 py-2.5 transition-colors duration-short ease-out hover:bg-paper-3">
      {onOpenDetail ? (
        <button
          type="button"
          onClick={onOpenDetail}
          className="group relative h-11 w-11 shrink-0 overflow-hidden rounded-lg bg-paper-3 shadow-xs transition-transform duration-short hover:scale-105 active:scale-95"
          title="Bấm để phóng to ảnh & xem dinh dưỡng chi tiết"
        >
          <img src={imgSrc} alt={chinh} className="h-full w-full object-cover" />
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
            <Eye size={14} className="text-white" />
          </div>
        </button>
      ) : null}
      <span className={`min-w-0 flex-1 ${onOpenDetail ? 'cursor-pointer' : ''}`} onClick={onOpenDetail}>
        <span className="block truncate text-sm font-semibold text-ink hover:text-accent-strong">{chinh}</span>
        <span className="flex flex-wrap items-center gap-1 text-xs text-muted">
          {phu}
          {nguon && (
            <span className="rounded-full bg-paper-3 px-2 py-0.5 font-medium text-ink-2">
              {SOURCE_LABEL[nguon] || nguon}
            </span>
          )}
        </span>
      </span>
      <span className="shrink-0 text-sm font-medium text-ink-2 [font-variant-numeric:tabular-nums]">{tri}</span>
      {onOpenDetail && (
        <Btn variant="subtle" size="sm" onClick={onOpenDetail} aria-label="Xem chi tiết">
          <Maximize2 size={13} />
        </Btn>
      )}
      <Btn variant="danger-subtle" size="sm" onClick={onDelete} disabled={dangXoa} aria-label="Xóa khỏi nhật ký">
        <Trash2 size={13} />
      </Btn>
    </li>
  );
}

function FoodLightboxModal({ meal, open, onClose }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose();
    }
    if (open) window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open || !meal) return null;

  const imgSrc = getFoodImage(meal.food_name);

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center bg-black/75 p-4 backdrop-blur-md animate-fade-in"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="relative w-full max-w-md overflow-hidden rounded-2xl bg-paper p-0 shadow-2xl animate-modal-in border border-white/20"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-black/60 text-white backdrop-blur-sm transition-transform hover:scale-110 active:scale-95"
          aria-label="Đóng"
        >
          <X size={18} />
        </button>

        <div className="relative aspect-video w-full overflow-hidden bg-black/10">
          <img
            src={imgSrc}
            alt={meal.food_name}
            className="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
          <div className="absolute bottom-4 left-4 right-4 text-white">
            <span className="inline-block rounded-full bg-accent-strong px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-white shadow-sm">
              {MEAL_LABEL[meal.meal_type] ?? meal.meal_type}
            </span>
            <h3 className="mt-1 font-display text-xl font-bold text-white">{meal.food_name}</h3>
          </div>
        </div>

        <div className="space-y-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule-2 pb-3 text-xs text-muted">
            <div className="flex items-center gap-1.5">
              <span>Nguồn:</span>
              <span className="font-semibold text-ink-2">{SOURCE_LABEL[meal.source_type] || meal.source_type || 'Thủ công'}</span>
            </div>
            <div>
              <span>Khẩu phần: </span>
              <b className="text-ink-2">{meal.quantity} phần</b>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="rounded-xl bg-accent-soft/60 p-2.5 border border-accent/20">
              <span className="block text-xs font-semibold text-accent-strong uppercase">Calo</span>
              <span className="font-display text-lg font-bold text-accent-strong [font-variant-numeric:tabular-nums]">
                {Math.round(meal.calories_kcal || 0)}
              </span>
              <span className="block text-[10px] text-muted">kcal</span>
            </div>
            <div className="rounded-xl bg-paper-2 p-2.5 border border-rule-2">
              <span className="block text-xs font-medium text-muted uppercase">Đạm</span>
              <span className="font-display text-base font-bold text-ink [font-variant-numeric:tabular-nums]">
                {meal.protein_g != null ? `${meal.protein_g}g` : '—'}
              </span>
            </div>
            <div className="rounded-xl bg-paper-2 p-2.5 border border-rule-2">
              <span className="block text-xs font-medium text-muted uppercase">Carbs</span>
              <span className="font-display text-base font-bold text-ink [font-variant-numeric:tabular-nums]">
                {meal.carb_g != null ? `${meal.carb_g}g` : '—'}
              </span>
            </div>
            <div className="rounded-xl bg-paper-2 p-2.5 border border-rule-2">
              <span className="block text-xs font-medium text-muted uppercase">Béo</span>
              <span className="font-display text-base font-bold text-ink [font-variant-numeric:tabular-nums]">
                {meal.fat_g != null ? `${meal.fat_g}g` : '—'}
              </span>
            </div>
          </div>

          <div className="flex justify-end pt-1">
            <Btn variant="primary" size="sm" onClick={onClose} className="w-full">
              Đóng xem ảnh
            </Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

function BuaAn({ ngay, meals, foods, onSaved, onError }) {
  const [foodId, setFoodId] = useState('');
  const [tenMoi, setTenMoi] = useState('');
  const [kcal, setKcal] = useState('');
  const [loai, setLoai] = useState('LUNCH');
  const [phan, setPhan] = useState('1');
  const [dangLuu, setDangLuu] = useState(false);
  const [selectedMeal, setSelectedMeal] = useState(null);

  const monMoi = foodId === '__new__';
  const monDaChon = (foods || []).find((f) => f.id === foodId);
  const tenMonHopLe = isValidFoodName(tenMoi);
  const kcalNumber = Number(kcal);
  const kcalHopLe = kcal !== '' && Number.isFinite(kcalNumber) && kcalNumber >= 1 && kcalNumber <= 5000;
  const phanNumber = Number(phan);
  const phanHopLe = phan !== '' && Number.isFinite(phanNumber) && phanNumber >= 0.5 && phanNumber <= 20;

  async function them() {
    if (!hopLe) return;
    setDangLuu(true);
    try {
      const payload = {
        meal_type: loai,
        quantity: phanNumber,
        log_date: ngay,
        ...(monMoi
          ? { food_name: tenMoi.trim(), calories_kcal: kcalNumber }
          : { food_id: foodId }),
      };
      const res = await api.addMeal(payload);
      setTenMoi(''); setKcal(''); setPhan('1');
      onSaved(`Đã ghi ${res.food_name} (+${Math.round(res.calories_kcal)} kcal).`);
    } catch (e) {
      if (e.status === 422) onError('Thông tin món ăn chưa hợp lệ. Vui lòng kiểm tra tên món, kcal và số phần.');
      else onError(typeof e.detail === 'string' ? e.detail : 'Không ghi được bữa ăn. Vui lòng thử lại.');
    } finally {
      setDangLuu(false);
    }
  }

  const hopLe = phanHopLe && (monMoi ? tenMonHopLe && kcalHopLe : !!foodId);

  return (
    <KhungThe icon={UtensilsCrossed} title="Bữa ăn" subtitle="Chọn món có sẵn hoặc tự nhập món mới (bấm vào món để phóng to ảnh chi tiết)">
      <div className="flex flex-wrap items-start gap-2">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Món ăn
          <Select value={foodId} onChange={(e) => setFoodId(e.target.value)} className="w-52">
            <option value="">— Chọn món —</option>
            {(foods || []).map((f) => (
              <option key={f.id} value={f.id}>{f.name} ({Math.round(f.calories_kcal)} kcal)</option>
            ))}
            <option value="__new__">+ Món khác…</option>
          </Select>
        </label>

        {monMoi && (
          <>
            <label className="flex flex-col gap-1 text-xs text-muted">
              Tên món
              <Field
                value={tenMoi}
                maxLength={100}
                onChange={(e) => setTenMoi(e.target.value)}
                aria-invalid={tenMoi !== '' && !tenMonHopLe}
                placeholder="VD: Bánh xèo"
                className={`w-40 ${tenMoi !== '' && !tenMonHopLe ? 'outline outline-2 outline-danger' : ''}`}
              />
              {tenMoi !== '' && !tenMonHopLe && (
                <span className="max-w-44 text-danger">Tên món từ 2–100 ký tự, không chứa emoji hoặc ký tự đặc biệt</span>
              )}
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted">
              Kcal / phần
              <Field
                type="number" min="1" max="5000" step="1" value={kcal}
                onChange={(e) => setKcal(e.target.value)}
                aria-invalid={kcal !== '' && !kcalHopLe}
                className={`w-24 ${kcal !== '' && !kcalHopLe ? 'outline outline-2 outline-danger' : ''}`}
              />
              {kcal !== '' && !kcalHopLe && (
                <span className="max-w-32 text-danger">Nhập từ 1–5.000 kcal</span>
              )}
            </label>
          </>
        )}

        <label className="flex flex-col gap-1 text-xs text-muted">
          Bữa
          <Select value={loai} onChange={(e) => setLoai(e.target.value)} className="w-32">
            {MEAL_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-muted">
          Số phần
          <Field
            type="number" min="0.5" max="20" step="0.5" value={phan}
            onChange={(e) => setPhan(e.target.value)}
            aria-invalid={!phanHopLe}
            className={`w-20 ${!phanHopLe ? 'outline outline-2 outline-danger' : ''}`}
          />
          {!phanHopLe && <span className="max-w-28 text-danger">Từ 0,5–20 phần</span>}
        </label>

        <Btn variant="primary" onClick={them} disabled={!hopLe || dangLuu} className="mt-5">
          <Plus size={15} />
          Thêm
        </Btn>
      </div>

      {monDaChon && !monMoi && (
        <p className="text-xs text-muted">
          {monDaChon.serving_desc ? `${monDaChon.serving_desc} · ` : ''}
          {Math.round(monDaChon.calories_kcal)} kcal/phần → tổng{' '}
          <b className="text-ink-2">{Math.round(monDaChon.calories_kcal * (Number(phan) || 1))} kcal</b>
        </p>
      )}

      {(!meals || meals.length === 0) ? (
        <p className="text-sm text-muted">Chưa ghi bữa nào trong ngày này.</p>
      ) : (
        <ul className="divide-y divide-rule-2">
          {meals.map((m) => (
            <DongNhatKy
              key={m.id}
              chinh={m.food_name}
              phu={`${MEAL_LABEL[m.meal_type] ?? m.meal_type} · ${m.quantity} phần`}
              nguon={m.source_type}
              tri={`${Math.round(m.calories_kcal || 0)} kcal`}
              onOpenDetail={() => setSelectedMeal(m)}
              onDelete={async () => {
                try {
                  await api.deleteMeal(m.id);
                  onSaved('Đã xóa khỏi nhật ký.');
                } catch (e) { onError(`Không xóa được: ${e.message}`); }
              }}
            />
          ))}
        </ul>
      )}

      <FoodLightboxModal
        meal={selectedMeal}
        open={Boolean(selectedMeal)}
        onClose={() => setSelectedMeal(null)}
      />
    </KhungThe>
  );
}

function VanDong({ ngay, acts, exercises, onSaved, onError }) {
  const [exId, setExId] = useState('');
  const [phut, setPhut] = useState('30');
  const [kcal, setKcal] = useState('');
  const [dungKcalThietBi, setDungKcalThietBi] = useState(false);
  const [dangLuu, setDangLuu] = useState(false);
  const soPhut = Number(phut);
  const kcalNhap = Number(kcal);
  const phutHopLe = phut !== '' && Number.isFinite(soPhut) && soPhut >= 1 && soPhut <= 600;
  const kcalHopLe = !dungKcalThietBi
    || (kcal !== '' && Number.isFinite(kcalNhap) && kcalNhap >= 1 && kcalNhap <= 5000);

  async function them() {
    if (!phutHopLe || !kcalHopLe) {
      onError('Vui lòng kiểm tra lại số phút và kcal vận động.');
      return;
    }
    setDangLuu(true);
    try {
      const payload = {
        exercise_id: Number(exId),
        duration_min: soPhut,
        started_at: `${ngay}T00:00:00Z`,
        ...(dungKcalThietBi && kcal ? { calories_burned: kcalNhap } : {}),
      };
      const res = await api.addActivity(payload);
      setPhut('30'); setKcal(''); setDungKcalThietBi(false);
      onSaved(`Đã ghi buổi tập (-${Math.round(res.calories_burned)} kcal).`);
    } catch (e) {
      if (e.status === 422) onError('Thông tin bài tập chưa hợp lệ. Vui lòng kiểm tra thời lượng và calo.');
      else onError(typeof e.detail === 'string' ? e.detail : 'Không ghi được vận động. Vui lòng thử lại.');
    } finally {
      setDangLuu(false);
    }
  }

  const exChon = (exercises || []).find((e) => e.id === Number(exId));

  return (
    <KhungThe icon={Dumbbell} title="Vận động & Thể thao" subtitle="Chọn bài tập để tự tính calo tiêu hao">
      <div className="flex flex-wrap items-start gap-2">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Bài tập
          <Select value={exId} onChange={(e) => setExId(e.target.value)} className="w-56">
            <option value="">— Chọn bài tập —</option>
            {(exercises || []).map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </Select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-muted">
          Thời lượng (phút)
          <Field
            type="number" min="1" max="600" step="5" value={phut}
            onChange={(e) => setPhut(e.target.value)}
            aria-invalid={!phutHopLe}
            className={`w-28 ${!phutHopLe ? 'outline outline-2 outline-danger' : ''}`}
          />
          {!phutHopLe && <span className="max-w-36 text-danger">Từ 1–600 phút</span>}
        </label>

        <div className="flex flex-col gap-1 text-xs text-muted">
          <label className="flex items-center gap-1.5 pt-5">
            <input
              type="checkbox"
              checked={dungKcalThietBi}
              onChange={(e) => setDungKcalThietBi(e.target.checked)}
              className="accent-accent-strong"
            />
            Nhập kcal từ đồng hồ
          </label>
          {dungKcalThietBi && (
            <Field
              type="number" min="1" max="5000" step="1" value={kcal}
              placeholder="VD: 180"
              onChange={(e) => setKcal(e.target.value)}
              aria-invalid={!kcalHopLe}
              className={`w-28 ${!kcalHopLe ? 'outline outline-2 outline-danger' : ''}`}
            />
          )}
          {dungKcalThietBi && !kcalHopLe && (
            <span className="max-w-32 text-danger">Từ 1–5.000 kcal</span>
          )}
        </div>

        <Btn variant="primary" onClick={them} disabled={!exId || !phutHopLe || !kcalHopLe || dangLuu} className="mt-5">
          <Plus size={15} />
          Thêm
        </Btn>
      </div>

      {exChon && !dungKcalThietBi && (
        <p className="text-xs text-muted">
          Hệ số MET: <b className="text-ink-2">{exChon.met_value}</b> · Ước tính tiêu hao theo cân nặng hiện tại
        </p>
      )}

      {(!acts || acts.length === 0) ? (
        <p className="text-sm text-muted">Chưa ghi vận động nào trong ngày này.</p>
      ) : (
        <ul className="divide-y divide-rule-2">
          {acts.map((a) => (
            <DongNhatKy
              key={a.id}
              chinh={a.item_name_snapshot || a.exercise_name || (a.steps ? `${a.steps} bước chân` : 'Hoạt động')}
              phu={`${a.duration_min} phút${a.steps ? ` · ${a.steps} bước` : ''}`}
              nguon={a.source_type}
              tri={`-${Math.round(a.calories_burned || 0)} kcal`}
              onDelete={async () => {
                try {
                  await api.deleteActivity(a.id);
                  onSaved('Đã xóa khỏi nhật ký.');
                } catch (e) { onError(`Không xóa được: ${e.message}`); }
              }}
            />
          ))}
        </ul>
      )}
    </KhungThe>
  );
}

function CanNang({ weights, onSaved, onError }) {
  const [kg, setKg] = useState('');
  const [dangLuu, setDangLuu] = useState(false);
  const kgNumber = Number(kg);
  const kgHopLe = kg !== '' && Number.isFinite(kgNumber) && kgNumber >= 20 && kgNumber <= 300;

  async function them() {
    if (!kgHopLe) return;
    setDangLuu(true);
    try {
      await api.updateWeight({ weight_kg: kgNumber });
      setKg('');
      onSaved(`Đã ghi cân nặng ${kgNumber} kg.`);
    } catch (e) {
      if (e.status === 422) onError('Cân nặng không hợp lệ. Vui lòng nhập từ 20–300 kg.');
      else onError(typeof e.detail === 'string' ? e.detail : 'Không ghi được cân nặng. Vui lòng thử lại.');
    } finally {
      setDangLuu(false);
    }
  }

  const safeWeights = Array.isArray(weights) ? weights : [];
  const sorted = [...safeWeights].sort((a, b) => new Date(a.recorded_at || a.log_date) - new Date(b.recorded_at || b.log_date));
  const chartData = sorted.map((w) => ({
    date: new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit' }).format(new Date(w.recorded_at || w.log_date)),
    kg: Number(w.weight_kg),
  }));

  const ganNhat = sorted[sorted.length - 1]?.weight_kg;
  const truocDo = sorted[sorted.length - 2]?.weight_kg;
  const chenh = ganNhat && truocDo ? (ganNhat - truocDo).toFixed(1) : null;

  return (
    <KhungThe icon={Scale} title="Cân nặng" subtitle="Theo dõi xu hướng cân nặng qua thời gian">
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-muted">
          Cân nặng hôm nay
          <Field
            type="number" min="20" max="300" step="0.1" value={kg}
            placeholder="VD: 65.5"
            onChange={(e) => setKg(e.target.value)}
            aria-invalid={kg !== '' && !kgHopLe}
            className={`w-28 ${kg !== '' && !kgHopLe ? 'outline outline-2 outline-danger' : ''}`}
          />
          kg
        </label>
        <Btn variant="primary" onClick={them} disabled={!kgHopLe || dangLuu}>
          <Plus size={15} />
          Ghi nhận
        </Btn>
        {kg !== '' && !kgHopLe && (
          <span className="text-xs text-danger">Nhập cân nặng từ 20–300 kg</span>
        )}

        {ganNhat && (
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-muted">Gần nhất:</span>
            <span className="font-display font-bold text-ink">{ganNhat} kg</span>
            {chenh && (
              <span className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold ${
                Number(chenh) < 0 ? 'bg-accent-soft text-accent-strong' : Number(chenh) > 0 ? 'bg-warning-soft text-warning-strong' : 'bg-paper-3 text-muted'
              }`}>
                {Number(chenh) < 0 ? <TrendingDown size={12} /> : <TrendingUp size={12} />}
                {Number(chenh) > 0 ? `+${chenh}` : chenh} kg
              </span>
            )}
          </div>
        )}
      </div>

      {chartData.length >= 2 ? (
        <div className="h-48 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#374151', fontSize: 11 }} />
              <YAxis domain={['dataMin - 1', 'dataMax + 1']} tick={{ fill: '#374151', fontSize: 11 }} />
              <Tooltip
                formatter={(val) => [`${val} kg`, 'Cân nặng']}
                contentStyle={{
                  backgroundColor: '#ffffff',
                  borderColor: '#e5e7eb',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="kg"
                stroke="#10b981"
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#10b981' }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-xs text-muted">Cần ít nhất 2 lần ghi nhận để hiển thị biểu đồ xu hướng.</p>
      )}
    </KhungThe>
  );
}
