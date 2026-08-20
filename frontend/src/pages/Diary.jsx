import { useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { Plus, Trash2, UtensilsCrossed, Dumbbell, Scale, TrendingDown, TrendingUp } from 'lucide-react';
import { api } from '../lib/api.js';
import { isValidFoodName } from '../lib/validation.js';
import { Btn, Field, Select, Alert, Toast, useToast } from '../components/ui.jsx';

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

// Recharts vẽ SVG nên không nhận var() — đọc token 1 lần từ :root như Dashboard
function useTokens(names) {
  return useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    return Object.fromEntries(names.map((n) => [n, cs.getPropertyValue(n).trim()]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

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
    api.foods().then(setFoods).catch(() => setFoods([]));
    api.exercises().then(setExercises).catch(() => setExercises([]));
    taiCanNang();
  }, []);

  useEffect(() => { taiNhatKy(ngay); }, [ngay]);

  const taiNhatKy = (d) => {
    api.meals(d).then(setMeals).catch((e) => setErr(e.message));
    api.activities(d).then(setActs).catch((e) => setErr(e.message));
  };
  const taiCanNang = () => api.weightHistory(90).then(setWeights).catch(() => setWeights([]));

  const tongNap = meals.reduce((s, m) => s + m.calories_kcal, 0);
  const tongDot = acts.reduce((s, a) => s + a.calories_burned, 0);

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
        ngay={ngay} meals={meals} foods={foods}
        onSaved={(msg) => { taiNhatKy(ngay); show(msg); }}
        onError={(msg) => show(msg, 'danger')}
      />

      <VanDong
        ngay={ngay} acts={acts} exercises={exercises}
        onSaved={(msg) => { taiNhatKy(ngay); show(msg); }}
        onError={(msg) => show(msg, 'danger')}
      />

      <CanNang
        weights={weights}
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
          {Math.round(value)}
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

function DongNhatKy({ chinh, phu, tri, nguon, onDelete, dangXoa }) {
  return (
    <li className="flex items-center gap-3 rounded-sm px-3 py-2 transition-colors duration-short ease-out hover:bg-paper-3">
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-ink">{chinh}</span>
        <span className="flex flex-wrap items-center gap-1 text-xs text-muted">
          {phu}
          {nguon && (
            <span className="rounded-full bg-paper-3 px-2 py-0.5 font-medium text-ink-2">
              {SOURCE_LABEL[nguon] || nguon}
            </span>
          )}
        </span>
      </span>
      <span className="shrink-0 text-sm text-ink-2 [font-variant-numeric:tabular-nums]">{tri}</span>
      <Btn variant="danger-subtle" size="sm" onClick={onDelete} disabled={dangXoa} aria-label="Xóa khỏi nhật ký">
        <Trash2 size={13} />
      </Btn>
    </li>
  );
}

function BuaAn({ ngay, meals, foods, onSaved, onError }) {
  const [foodId, setFoodId] = useState('');
  const [tenMoi, setTenMoi] = useState('');
  const [kcal, setKcal] = useState('');
  const [loai, setLoai] = useState('LUNCH');
  const [phan, setPhan] = useState('1');
  const [dangLuu, setDangLuu] = useState(false);

  const monMoi = foodId === '__new__';
  const monDaChon = foods.find((f) => f.id === foodId);
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
    <KhungThe icon={UtensilsCrossed} title="Bữa ăn" subtitle="Chọn món có sẵn hoặc tự nhập món mới">
      <div className="flex flex-wrap items-start gap-2">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Món ăn
          <Select value={foodId} onChange={(e) => setFoodId(e.target.value)} className="w-52">
            <option value="">— Chọn món —</option>
            {foods.map((f) => (
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

      {meals.length === 0 ? (
        <p className="text-sm text-muted">Chưa ghi bữa nào trong ngày này.</p>
      ) : (
        <ul className="divide-y divide-rule-2">
          {meals.map((m) => (
            <DongNhatKy
              key={m.id}
              chinh={m.food_name}
              phu={`${MEAL_LABEL[m.meal_type] ?? m.meal_type} · ${m.quantity} phần`}
              nguon={m.source_type}
              tri={`${Math.round(m.calories_kcal)} kcal`}
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
      const res = await api.addActivity({
        exercise_id: Number(exId),
        duration_min: soPhut,
        log_date: ngay,
        ...(dungKcalThietBi ? { calories_burned: kcalNhap } : {}),
      });
      setKcal('');
      setDungKcalThietBi(false);
      onSaved(`Đã ghi ${res.exercise_name} (−${Math.round(res.calories_burned)} kcal).`);
    } catch (e) {
      onError(`Không ghi được buổi tập: ${e.message}`);
    } finally {
      setDangLuu(false);
    }
  }

  return (
    <KhungThe icon={Dumbbell} title="Vận động" subtitle="Bỏ trống ô kcal thì hệ thống tự tính theo MET và cân nặng của bạn">
      <div className="flex flex-wrap items-start gap-2">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Bài tập
          <Select value={exId} onChange={(e) => setExId(e.target.value)} className="w-52">
            <option value="">— Chọn bài tập —</option>
            {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </Select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted">
          Số phút
          <Field type="number" min="1" max="600" value={phut} onChange={(e) => setPhut(e.target.value)}
            className={`w-24 ${phut !== '' && !phutHopLe ? 'outline outline-2 outline-danger' : ''}`} />
          {phut !== '' && !phutHopLe && <span className="font-medium text-danger">Nhập từ 1 đến 600 phút</span>}
        </label>
        <label className="mt-5 flex min-h-11 items-center gap-2 rounded-sm bg-paper-3 px-3 text-xs font-medium text-ink-2 shadow-hairline">
          <input type="checkbox" checked={dungKcalThietBi} onChange={(e) => {
            setDungKcalThietBi(e.target.checked);
            if (!e.target.checked) setKcal('');
          }} className="h-4 w-4 accent-accent-strong" />
          Dùng kcal từ thiết bị
        </label>
        {dungKcalThietBi && (
          <label className="flex flex-col gap-1 text-xs text-muted">
            Kcal thiết bị ghi nhận
            <Field type="number" min="1" max="5000" value={kcal} onChange={(e) => setKcal(e.target.value)}
              placeholder="VD: 250" className={`w-32 ${!kcalHopLe ? 'outline outline-2 outline-danger' : ''}`} />
            {!kcalHopLe && <span className="font-medium text-danger">Nhập từ 1 đến 5000 kcal</span>}
          </label>
        )}
        <Btn variant="primary" onClick={them} disabled={!exId || !phutHopLe || !kcalHopLe || dangLuu} className="mt-5">
          <Plus size={15} />
          Thêm
        </Btn>
      </div>

      {acts.length === 0 ? (
        <p className="text-sm text-muted">Chưa ghi buổi tập nào trong ngày này.</p>
      ) : (
        <ul className="divide-y divide-rule-2">
          {acts.map((a) => (
            <DongNhatKy
              key={a.id}
              chinh={a.exercise_name}
              phu={`${a.duration_min} phút`}
              nguon={a.source_type}
              tri={`${Math.round(a.calories_burned)} kcal`}
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
  const t = useTokens([
    '--color-accent', '--color-rule-2', '--color-rule', '--color-muted',
    '--color-paper-2', '--color-ink', '--color-warning-strong',
  ]);

  const dauKy = weights[0];
  const cuoiKy = weights.at(-1);
  const chenhLech = dauKy && cuoiKy ? cuoiKy.weight_kg - dauKy.weight_kg : null;
  const Xu = (chenhLech ?? 0) <= 0 ? TrendingDown : TrendingUp;
  const kgNumber = Number(kg);
  const kgHopLe = kg !== '' && Number.isFinite(kgNumber) && kgNumber >= 20 && kgNumber <= 300;

  async function luu() {
    if (!kgHopLe) return;
    setDangLuu(true);
    try {
      const res = await api.updateWeight({ weight_kg: kgNumber });
      setKg('');
      onSaved(`Đã cập nhật cân nặng ${res.weight_kg} kg${res.bmi ? ` · BMI ${res.bmi}` : ''}.`);
    } catch (e) {
      if (e.status === 422) onError('Cân nặng phải từ 20 đến 300 kg.');
      else onError(typeof e.detail === 'string' ? e.detail : 'Không lưu được cân nặng. Vui lòng thử lại.');
    } finally {
      setDangLuu(false);
    }
  }

  // Recharts cần mảng số; rút gọn nhãn ngày còn dd/MM cho đỡ chật trục X
  const duLieu = weights.map((w) => ({
    ngay: w.recorded_at.slice(8, 10) + '/' + w.recorded_at.slice(5, 7),
    kg: w.weight_kg,
  }));

  return (
    <KhungThe icon={Scale} title="Cân nặng" subtitle="Cập nhật mỗi tuần một lần là đủ để hệ thống chấm lộ trình">
      <div className="flex flex-wrap items-start gap-2">
        <label className="flex flex-col gap-1 text-xs text-muted">
          Cân nặng hôm nay (kg)
          <Field
            type="number" min="20" max="300" step="0.1" value={kg}
            onChange={(e) => setKg(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && kgHopLe && luu()}
            aria-invalid={kg !== '' && !kgHopLe}
            placeholder="VD: 68.5" className="w-32"
          />
          {kg !== '' && !kgHopLe && (
            <span className="max-w-36 text-danger">Nhập từ 20 đến 300 kg</span>
          )}
        </label>
        <Btn variant="primary" onClick={luu} disabled={!kgHopLe || dangLuu} className="mt-5">
          {dangLuu ? 'Đang lưu…' : 'Cập nhật'}
        </Btn>

        {cuoiKy && (
          <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-full bg-paper-3 px-3 py-1 text-ink-2 [font-variant-numeric:tabular-nums]">
              Hiện tại {cuoiKy.weight_kg} kg
            </span>
            {cuoiKy.bmi && (
              <span className="rounded-full bg-paper-3 px-3 py-1 text-ink-2 [font-variant-numeric:tabular-nums]">
                BMI {cuoiKy.bmi}
              </span>
            )}
            {chenhLech !== null && weights.length > 1 && (
              <span className="flex items-center gap-1 rounded-full bg-accent-soft px-3 py-1 font-medium text-accent-strong [font-variant-numeric:tabular-nums]">
                <Xu size={14} />
                {chenhLech > 0 ? '+' : ''}{chenhLech.toFixed(1)} kg
              </span>
            )}
          </div>
        )}
      </div>

      {duLieu.length < 2 ? (
        <p className="text-sm text-muted">
          Cần ít nhất 2 lần cân để vẽ biểu đồ. Ghi cân nặng đều đặn để theo dõi xu hướng.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={duLieu} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
            <CartesianGrid stroke={t['--color-rule-2']} strokeDasharray="4 6" vertical={false} />
            <XAxis dataKey="ngay" fontSize={12} tick={{ fill: t['--color-muted'] }}
                   tickLine={false} axisLine={{ stroke: t['--color-rule'] }} />
            <YAxis fontSize={12} tick={{ fill: t['--color-muted'] }} tickLine={false}
                   axisLine={false} width={44} domain={['dataMin - 2', 'dataMax + 2']} />
            <Tooltip
              formatter={(v) => [`${v} kg`, 'Cân nặng']}
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
            {/* Mốc xuất phát — nhìn phát biết đang trên hay dưới điểm bắt đầu */}
            {dauKy && (
              <ReferenceLine
                y={dauKy.weight_kg}
                stroke={t['--color-warning-strong']}
                strokeDasharray="6 4"
                strokeWidth={1.5}
                label={{
                  value: `Bắt đầu ${dauKy.weight_kg} kg`,
                  position: 'insideTopRight',
                  fill: t['--color-warning-strong'],
                  fontSize: 11,
                  fontFamily: 'var(--font-body)',
                }}
              />
            )}
            <Line
              type="monotone" dataKey="kg" name="Cân nặng"
              stroke={t['--color-accent']} strokeWidth={2.5}
              dot={{ r: 3, strokeWidth: 0, fill: t['--color-accent'] }}
              activeDot={{ r: 5, strokeWidth: 2, stroke: t['--color-paper-2'] }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </KhungThe>
  );
}
