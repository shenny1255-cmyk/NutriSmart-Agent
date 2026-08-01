import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import { api } from '../lib/api.js';
import PasswordInput from '../components/PasswordInput.jsx';
import { Btn, Field as TextInput, Select, Alert } from '../components/ui.jsx';
import AuthLayout from '../components/AuthLayout.jsx';
import { LogoMark } from '../components/Logo.jsx';
import { inputCls } from './login.jsx';

const isEmail = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s || '').trim());

// Fallback khi backend chưa chạy — sau này lấy từ API
const FALLBACK_CONDITIONS = [{ id: 1, name: 'Đái tháo đường típ 2' }, { id: 2, name: 'Tăng huyết áp' }, { id: 3, name: 'Rối loạn lipid máu' }];
const FALLBACK_ALLERGENS = [{ id: 1, name: 'Đậu phộng' }, { id: 2, name: 'Hải sản có vỏ' }, { id: 3, name: 'Sữa bò' }, { id: 4, name: 'Gluten' }];

const ACTIVITY_LEVELS = [
  { value: 1, label: 'Ít vận động (ngồi nhiều)' },
  { value: 2, label: 'Vận động nhẹ (1–3 buổi/tuần)' },
  { value: 3, label: 'Vận động vừa (3–5 buổi/tuần)' },
  { value: 4, label: 'Vận động nhiều (6–7 buổi/tuần)' },
  { value: 5, label: 'Vận động rất nhiều (thể thao chuyên nghiệp)' },
];

const GOALS = [
  { value: 'LOSE_WEIGHT', label: 'Giảm cân' },
  { value: 'MAINTAIN', label: 'Duy trì cân nặng' },
  { value: 'GAIN_MUSCLE', label: 'Tăng cơ' },
  { value: 'MEDICAL', label: 'Theo chỉ định y tế' },
];

export default function Register() {
  const [step, setStep] = useState(1);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [conditions, setConditions] = useState(FALLBACK_CONDITIONS);
  const [allergens, setAllergens] = useState(FALLBACK_ALLERGENS);

  const [form, setForm] = useState({
    // Bước 1 — tài khoản
    email: '', password: '', confirm: '', full_name: '',
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
    api.countries().then(setCountries).catch(() => { });
    api.conditions().then(setConditions).catch(() => { });
    api.allergens().then(setAllergens).catch(() => { });
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
    <AuthLayout>
      <form
        onSubmit={step === 1 ? nextStep : submit}
        className="mx-auto w-full max-w-lg rounded-md bg-paper-2 p-6 shadow-card sm:p-8"
      >
        <div className="mb-5 flex items-center gap-3">
          <LogoMark size={44} />
          <div>
            <h1 className="font-display text-xl font-bold tracking-tight text-ink">
              Nutri<span className="text-accent-strong">Smart</span>
            </h1>
            <p className="text-sm text-muted">
              Bước {step}/2 — {step === 1 ? 'Thông tin tài khoản' : 'Hồ sơ sức khỏe'}
            </p>
          </div>
        </div>

        {/* Thanh tiến trình — scaleX (transform), không animate width */}
        <div className="mb-6 h-1 w-full overflow-hidden rounded-full bg-paper-3">
          <div
            className="h-full origin-left rounded-full bg-accent transition-transform duration-long ease-out"
            style={{ transform: step === 1 ? 'scaleX(0.5)' : 'scaleX(1)' }}
          />
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <FieldGroup label="Họ và tên">
              <TextInput required value={form.full_name} onChange={(e) => set('full_name', e.target.value)} className="w-full" />
            </FieldGroup>

            <FieldGroup label="Email">
              <TextInput type="email" required value={form.email} onChange={(e) => set('email', e.target.value)} className="w-full" />
              {form.email && !isEmail(form.email) && (
                <p className="mt-1 text-xs text-warning-strong">Email chưa đúng định dạng</p>
              )}
            </FieldGroup>

            <FieldGroup label="Mật khẩu">
              <PasswordInput required value={form.password} onChange={(e) => set('password', e.target.value)} className={inputCls} />
              <p className={`mt-1 flex items-center gap-1 text-xs ${form.password.length >= 8 ? 'text-accent-strong' : 'text-muted'}`}>
                {form.password.length >= 8 && <Check size={12} strokeWidth={3} />}
                {form.password.length >= 8 ? 'Đủ độ dài' : 'Tối thiểu 8 ký tự'}
              </p>
            </FieldGroup>

            <FieldGroup label="Xác nhận mật khẩu">
              <PasswordInput required value={form.confirm} onChange={(e) => set('confirm', e.target.value)} className={inputCls} />
              {form.confirm && (
                <p className={`mt-1 flex items-center gap-1 text-xs ${form.confirm === form.password ? 'text-accent-strong' : 'text-warning-strong'}`}>
                  {form.confirm === form.password && <Check size={12} strokeWidth={3} />}
                  {form.confirm === form.password ? 'Mật khẩu khớp' : 'Mật khẩu chưa khớp'}
                </p>
              )}
            </FieldGroup>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FieldGroup label="Giới tính">
                <Select value={form.gender} onChange={(e) => set('gender', e.target.value)} className="w-full">
                  <option value="MALE">Nam</option>
                  <option value="FEMALE">Nữ</option>
                  <option value="OTHER">Khác</option>
                </Select>
              </FieldGroup>

              <FieldGroup label="Ngày sinh">
                <TextInput type="date" required value={form.birth_date} onChange={(e) => set('birth_date', e.target.value)} className="w-full" />
              </FieldGroup>

              <FieldGroup label="Chiều cao (cm)">
                <TextInput type="number" min="50" max="250" step="0.1" required
                  value={form.height_cm} onChange={(e) => set('height_cm', e.target.value)} className="w-full" />
              </FieldGroup>

              <FieldGroup label="Cân nặng (kg)">
                <TextInput type="number" min="20" max="300" step="0.1" required
                  value={form.weight_kg} onChange={(e) => set('weight_kg', e.target.value)} className="w-full" />
              </FieldGroup>
            </div>

            {bmi && (
              <p className="rounded-sm bg-accent-soft px-3 py-2 text-sm text-accent-strong">
                BMI dự kiến: <b className="[font-variant-numeric:tabular-nums]">{bmi}</b>
              </p>
            )}

            <FieldGroup label="Mức độ vận động">
              <Select value={form.activity_level} onChange={(e) => set('activity_level', e.target.value)} className="w-full">
                {ACTIVITY_LEVELS.map((a) => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </Select>
            </FieldGroup>

            <FieldGroup label="Mục tiêu">
              <Select value={form.goal} onChange={(e) => set('goal', e.target.value)} className="w-full">
                {GOALS.map((g) => (
                  <option key={g.value} value={g.value}>{g.label}</option>
                ))}
              </Select>
            </FieldGroup>

            <FieldGroup label="Bệnh nền" hint="Chọn nhiều nếu có">
              <CheckGroup items={conditions} selected={form.condition_ids} onToggle={(id) => toggle('condition_ids', id)} />
            </FieldGroup>

            <FieldGroup label="Dị ứng thực phẩm" hint="Chọn nhiều nếu có">
              <CheckGroup items={allergens} selected={form.allergen_ids} onToggle={(id) => toggle('allergen_ids', id)} />
            </FieldGroup>
          </div>
        )}

        {err && <div className="mt-4"><Alert tone="danger">{err}</Alert></div>}

        <div className="mt-6 flex gap-3">
          {step === 2 && (
            <Btn type="button" variant="ghost" onClick={() => setStep(1)}>
              Quay lại
            </Btn>
          )}
          <Btn type="submit" variant="primary" disabled={loading} className="flex-1">
            {step === 1 ? 'Tiếp tục' : loading ? 'Đang tạo tài khoản…' : 'Hoàn tất đăng ký'}
          </Btn>
        </div>

        <p className="mt-5 text-center text-sm text-muted">
          Đã có tài khoản?{' '}
          <Link
            to="/login"
            className="rounded-sm font-medium text-accent-strong underline decoration-accent/40 underline-offset-2 transition-colors duration-micro ease-out hover:decoration-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
          >
            Đăng nhập
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}

function FieldGroup({ label, hint, children }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-ink-2">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
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
            aria-pressed={on}
            onClick={() => onToggle(it.id)}
            className={[
              'inline-flex min-h-9 items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium',
              'transition-[background-color,color,box-shadow,transform] duration-short ease-out',
              'active:scale-95',
              'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
              on
                ? 'bg-accent-strong text-accent-ink shadow-whisper'
                : 'bg-paper-2 text-ink-2 shadow-hairline hover:bg-accent-soft hover:text-accent-strong',
            ].join(' ')}
          >
            {on && <Check size={12} strokeWidth={3} />}
            {it.name}
          </button>
        );
      })}
    </div>
  );
}