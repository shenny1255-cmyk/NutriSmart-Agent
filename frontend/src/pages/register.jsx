import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../lib/api.js';
import PasswordInput from '../components/PasswordInput.jsx';

const isEmail = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s || '').trim());

// Fallback khi backend chưa chạy — sau này lấy từ API
const FALLBACK_COUNTRIES  = [{ code: 'VN', name: 'Việt Nam' }, { code: 'US', name: 'Hoa Kỳ' }, { code: 'JP', name: 'Nhật Bản' }];
const FALLBACK_CONDITIONS = [{ id: 1, name: 'Đái tháo đường típ 2' }, { id: 2, name: 'Tăng huyết áp' }, { id: 3, name: 'Rối loạn lipid máu' }];
const FALLBACK_ALLERGENS  = [{ id: 1, name: 'Đậu phộng' }, { id: 2, name: 'Hải sản có vỏ' }, { id: 3, name: 'Sữa bò' }, { id: 4, name: 'Gluten' }];

const ACTIVITY_LEVELS = [
  { value: 1, label: 'Ít vận động (ngồi nhiều)' },
  { value: 2, label: 'Vận động nhẹ (1–3 buổi/tuần)' },
  { value: 3, label: 'Vận động vừa (3–5 buổi/tuần)' },
  { value: 4, label: 'Vận động nhiều (6–7 buổi/tuần)' },
  { value: 5, label: 'Vận động rất nhiều (thể thao chuyên nghiệp)' },
];

const GOALS = [
  { value: 'LOSE_WEIGHT', label: 'Giảm cân' },
  { value: 'MAINTAIN',    label: 'Duy trì cân nặng' },
  { value: 'GAIN_MUSCLE', label: 'Tăng cơ' },
  { value: 'MEDICAL',     label: 'Theo chỉ định y tế' },
];

export default function Register() {
  const [step, setStep] = useState(1);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [countries, setCountries]   = useState(FALLBACK_COUNTRIES);
  const [conditions, setConditions] = useState(FALLBACK_CONDITIONS);
  const [allergens, setAllergens]   = useState(FALLBACK_ALLERGENS);

  const [form, setForm] = useState({
    // Bước 1 — tài khoản
    email: '', password: '', confirm: '', full_name: '', country_code: 'VN',
    // Bước 2 — hồ sơ sức khỏe
    gender: 'MALE', birth_date: '', height_cm: '', weight_kg: '',
    activity_level: 3, goal: 'MAINTAIN',
    condition_ids: [], allergen_ids: [],
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const toggle = (key, id) =>
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(id) ? f[key].filter((x) => x !== id) : [...f[key], id],
    }));

  useEffect(() => {
    api.countries().then(setCountries).catch(() => {});
    api.conditions().then(setConditions).catch(() => {});
    api.allergens().then(setAllergens).catch(() => {});
  }, []);

  function nextStep(e) {
    e.preventDefault();
    if (form.password.length < 8) return setErr('Mật khẩu tối thiểu 8 ký tự.');
    if (form.password !== form.confirm) return setErr('Mật khẩu xác nhận không khớp.');
    setErr(null);
    setStep(2);
  }

  async function submit(e) {
    e.preventDefault();
    setErr(null);
    setLoading(true);

    // Chuẩn hóa: input trả string, DB cần number
    const payload = {
      email: form.email,
      password: form.password,
      full_name: form.full_name,
      country_code: form.country_code,
      profile: {
        gender: form.gender,
        birth_date: form.birth_date,
        height_cm: Number(form.height_cm),
        weight_kg: Number(form.weight_kg),
        activity_level: Number(form.activity_level),
        goal: form.goal,
        condition_ids: form.condition_ids,
        allergen_ids: form.allergen_ids,
      },
    };

    try {
      const res = await api.register(payload);
      if (res?.access_token) {
        localStorage.setItem('access_token', res.access_token);
        try {
          const me = await api.me();
          localStorage.setItem('role', me.role);   // đồng bộ role như luồng đăng nhập
        } catch { /* role không bắt buộc để vào app */ }
      }
      navigate('/');
    } catch (e) {
      if (e.status === 409) setErr('Email này đã được đăng ký. Hãy đăng nhập.');
      else if (e.status === 422) setErr('Thông tin chưa hợp lệ — kiểm tra lại email và mật khẩu.');
      else if (e.status === undefined) setErr('Không kết nối được máy chủ. Backend đã chạy chưa?');
      else setErr(typeof e.detail === 'string' ? e.detail : 'Đăng ký thất bại, thử lại sau.');
    } finally {
      setLoading(false);
    }
  }

  // BMI xem trước, tính ngay trên client
  const bmi =
    form.height_cm && form.weight_kg
      ? (Number(form.weight_kg) / (Number(form.height_cm) / 100) ** 2).toFixed(1)
      : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 py-10">
      <form
        onSubmit={step === 1 ? nextStep : submit}
        className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-8"
      >
        <h1 className="text-xl font-bold text-emerald-700">NutriSmart</h1>
        <p className="mb-6 text-sm text-slate-500">
          Bước {step}/2 — {step === 1 ? 'Thông tin tài khoản' : 'Hồ sơ sức khỏe'}
        </p>

        {/* thanh tiến trình */}
        <div className="mb-6 h-1 w-full rounded bg-slate-200">
          <div
            className="h-1 rounded bg-emerald-600 transition-all"
            style={{ width: step === 1 ? '50%' : '100%' }}
          />
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <Field label="Họ và tên">
              <input required value={form.full_name} onChange={(e) => set('full_name', e.target.value)} className={inputCls} />
            </Field>

            <Field label="Email">
              <input type="email" required value={form.email} onChange={(e) => set('email', e.target.value)} className={inputCls} />
              {form.email && !isEmail(form.email) && (
                <p className="mt-1 text-xs text-amber-600">Email chưa đúng định dạng</p>
              )}
            </Field>

            <Field label="Mật khẩu">
              <PasswordInput required value={form.password} onChange={(e) => set('password', e.target.value)} className={inputCls} />
              <p className={`mt-1 text-xs ${form.password.length >= 8 ? 'text-emerald-600' : 'text-slate-400'}`}>
                {form.password.length >= 8 ? '✓ Đủ độ dài' : 'Tối thiểu 8 ký tự'}
              </p>
            </Field>

            <Field label="Xác nhận mật khẩu">
              <PasswordInput required value={form.confirm} onChange={(e) => set('confirm', e.target.value)} className={inputCls} />
              {form.confirm && (
                <p className={`mt-1 text-xs ${form.confirm === form.password ? 'text-emerald-600' : 'text-amber-600'}`}>
                  {form.confirm === form.password ? '✓ Mật khẩu khớp' : 'Mật khẩu chưa khớp'}
                </p>
              )}
            </Field>

            <Field label="Quốc gia" hint="Dùng để lọc thuốc/hoạt chất bị cấm theo quy định sở tại">
              <select value={form.country_code} onChange={(e) => set('country_code', e.target.value)} className={inputCls}>
                {countries.map((c) => (
                  <option key={c.code} value={c.code}>{c.name}</option>
                ))}
              </select>
            </Field>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Giới tính">
                <select value={form.gender} onChange={(e) => set('gender', e.target.value)} className={inputCls}>
                  <option value="MALE">Nam</option>
                  <option value="FEMALE">Nữ</option>
                  <option value="OTHER">Khác</option>
                </select>
              </Field>

              <Field label="Ngày sinh">
                <input type="date" required value={form.birth_date} onChange={(e) => set('birth_date', e.target.value)} className={inputCls} />
              </Field>

              <Field label="Chiều cao (cm)">
                <input type="number" min="50" max="250" step="0.1" required
                  value={form.height_cm} onChange={(e) => set('height_cm', e.target.value)} className={inputCls} />
              </Field>

              <Field label="Cân nặng (kg)">
                <input type="number" min="20" max="300" step="0.1" required
                  value={form.weight_kg} onChange={(e) => set('weight_kg', e.target.value)} className={inputCls} />
              </Field>
            </div>

            {bmi && (
              <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                BMI dự kiến: <b>{bmi}</b>
              </p>
            )}

            <Field label="Mức độ vận động">
              <select value={form.activity_level} onChange={(e) => set('activity_level', e.target.value)} className={inputCls}>
                {ACTIVITY_LEVELS.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </Field>

            <Field label="Mục tiêu">
              <select value={form.goal} onChange={(e) => set('goal', e.target.value)} className={inputCls}>
                {GOALS.map((g) => (
                  <option key={g.value} value={g.value}>{g.label}</option>
                ))}
              </select>
            </Field>

            <Field label="Bệnh nền" hint="Chọn nhiều nếu có">
              <CheckGroup items={conditions} selected={form.condition_ids} onToggle={(id) => toggle('condition_ids', id)} />
            </Field>

            <Field label="Dị ứng thực phẩm" hint="Chọn nhiều nếu có">
              <CheckGroup items={allergens} selected={form.allergen_ids} onToggle={(id) => toggle('allergen_ids', id)} />
            </Field>
          </div>
        )}

        {err && <p className="mt-4 text-sm text-red-600">{err}</p>}

        <div className="mt-6 flex gap-3">
          {step === 2 && (
            <button type="button" onClick={() => setStep(1)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm">
              Quay lại
            </button>
          )}
          <button type="submit" disabled={loading}
            className="flex-1 rounded-lg bg-emerald-600 py-2 text-sm font-medium text-white disabled:opacity-50">
            {step === 1 ? 'Tiếp tục' : loading ? 'Đang tạo tài khoản…' : 'Hoàn tất đăng ký'}
          </button>
        </div>

        <p className="mt-4 text-center text-sm text-slate-500">
          Đã có tài khoản? <Link to="/login" className="text-emerald-700 underline">Đăng nhập</Link>
        </p>
      </form>
    </div>
  );
}

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500';

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function CheckGroup({ items, selected, onToggle }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => {
        const on = selected.includes(it.id);
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => onToggle(it.id)}
            className={`rounded-full border px-3 py-1 text-xs transition ${
              on
                ? 'border-emerald-600 bg-emerald-50 text-emerald-700'
                : 'border-slate-300 text-slate-600 hover:border-slate-400'
            }`}
          >
            {it.name}
          </button>
        );
      })}
    </div>
  );
}