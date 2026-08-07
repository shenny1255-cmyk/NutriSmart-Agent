import { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import { api } from '../lib/api.js';
import { isValidBirthDate, MAX_BIRTH_DATE, MIN_BIRTH_DATE } from '../lib/date.js';
import { areBodyMetricsPlausible, bodyMetricsBmi, isValidFullName } from '../lib/validation.js';
import PasswordInput from '../components/PasswordInput.jsx';
import CustomHealthTerms from '../components/CustomHealthTerms.jsx';
import CatalogMultiSelect from '../components/CatalogMultiSelect.jsx';
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

const INITIAL_FORM = {
  email: '', password: '', confirm: '', full_name: '',
  gender: 'MALE', birth_date: '', height_cm: '', weight_kg: '',
  activity_level: 3, goal: 'MAINTAIN',
  condition_ids: [], allergen_ids: [],
  custom_conditions: [], custom_allergens: [],
};

export default function Register() {
  const [step, setStep] = useState(1);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [emailStatus, setEmailStatus] = useState('idle');
  const emailCheckId = useRef(0);
  const [touched, setTouched] = useState({ full_name: false, email: false, password: false, confirm: false });
  const navigate = useNavigate();

  const [conditions, setConditions] = useState(FALLBACK_CONDITIONS);
  const [allergens, setAllergens] = useState(FALLBACK_ALLERGENS);
  // Quốc gia đã bỏ (mặc định Việt Nam)

  const [form, setForm] = useState(INITIAL_FORM);

  const set = (k, v) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (k === 'email') {
      emailCheckId.current += 1;
      setEmailStatus('idle');
    }
    setErr(null);
  };
  const touch = (key) => setTouched((current) => ({ ...current, [key]: true }));
  const fullNameValid = isValidFullName(form.full_name);
  const emailValid = isEmail(form.email);
  const passwordValid = form.password.length >= 8;
  const confirmValid = form.confirm !== '' && form.confirm === form.password;
  const step1Valid = fullNameValid && emailValid && passwordValid && confirmValid && emailStatus !== 'taken';
  const heightNumber = Number(form.height_cm);
  const weightNumber = Number(form.weight_kg);
  const heightValid = form.height_cm !== '' && Number.isFinite(heightNumber) && heightNumber > 50 && heightNumber < 250;
  const weightValid = form.weight_kg !== '' && Number.isFinite(weightNumber) && weightNumber >= 20 && weightNumber <= 300;
  const metricsValid = heightValid && weightValid && areBodyMetricsPlausible(heightNumber, weightNumber);
  const step2Valid = isValidBirthDate(form.birth_date) && metricsValid;

  useEffect(() => {
    api.conditions().then(setConditions).catch(() => { });
    api.allergens().then(setAllergens).catch(() => { });
  }, []);

  async function checkEmail() {
    if (!emailValid) return 'invalid';
    const email = form.email.trim().toLowerCase();
    const checkId = ++emailCheckId.current;
    setEmailStatus('checking');
    try {
      const result = await api.checkEmail(email);
      if (checkId !== emailCheckId.current) return 'stale';
      setEmailStatus(result.available ? 'available' : 'taken');
      return result.available ? 'available' : 'taken';
    } catch {
      if (checkId === emailCheckId.current) {
        setEmailStatus('error');
        setErr('Không kiểm tra được email. Vui lòng thử lại.');
      }
      return 'error';
    }
  }

  async function nextStep(e) {
    e.preventDefault();
    setTouched({ full_name: true, email: true, password: true, confirm: true });
    if (!fullNameValid) return setErr('Họ và tên chưa hợp lệ.');
    if (!emailValid) return setErr('Email chưa đúng định dạng.');
    if (!passwordValid) return setErr('Mật khẩu tối thiểu 8 ký tự.');
    if (!confirmValid) return setErr('Mật khẩu xác nhận không khớp.');
    if (emailStatus !== 'available') {
      const checked = await checkEmail();
      if (checked !== 'available') {
        if (checked === 'taken') setErr('Email này đã được đăng ký. Hãy dùng email khác hoặc đăng nhập.');
        return;
      }
    }
    setErr(null);
    setStep(2);
  }

  async function submit(e) {
    e.preventDefault();
    setErr(null);
    if (!isValidBirthDate(form.birth_date)) {
      setErr('Ngày sinh không hợp lệ. Vui lòng chọn ngày từ lịch và không vượt quá hôm nay.');
      return;
    }
    if (!metricsValid) {
      setErr('Chiều cao hoặc cân nặng chưa hợp lệ. Vui lòng kiểm tra lại.');
      return;
    }
    setLoading(true);

    // Chuẩn hóa: input trả string, DB cần number
    const payload = {
      email: form.email.trim().toLowerCase(),
      password: form.password,
      full_name: form.full_name,
      profile: {
        gender: form.gender,
        birth_date: form.birth_date,
        height_cm: Number(form.height_cm),
        weight_kg: Number(form.weight_kg),
        activity_level: Number(form.activity_level),
        goal: form.goal,
        condition_ids: form.condition_ids,
        allergen_ids: form.allergen_ids,
        custom_conditions: form.custom_conditions,
        custom_allergens: form.custom_allergens,
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
  const bmi = metricsValid
    ? bodyMetricsBmi(heightNumber, weightNumber).toFixed(1)
    : null;

  return (
    <AuthLayout>
      <form
        onSubmit={step === 1 ? nextStep : submit}
        autoComplete="off"
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
            <FieldGroup label="Họ và tên" required>
              <TextInput
                required
                name="registration-full-name"
                autoComplete="name"
                maxLength={100}
                value={form.full_name}
                onChange={(e) => set('full_name', e.target.value)}
                onBlur={() => touch('full_name')}
                aria-invalid={touched.full_name && !fullNameValid}
                className={`w-full ${touched.full_name && !fullNameValid ? 'outline outline-2 outline-danger' : ''}`}
              />
              {touched.full_name && !fullNameValid && (
                <p className="mt-1 text-xs font-medium text-danger">
                  Nhập 2–100 ký tự; không dùng emoji hoặc ký tự đặc biệt.
                </p>
              )}
            </FieldGroup>

            <FieldGroup label="Email" required>
              <TextInput type="email" required name="registration-email" autoComplete="off"
                value={form.email} onChange={(e) => set('email', e.target.value)}
                onBlur={() => { touch('email'); if (emailValid) checkEmail(); }}
                aria-invalid={(touched.email && !emailValid) || emailStatus === 'taken'}
                className={`w-full ${(touched.email && !emailValid) || emailStatus === 'taken' ? 'outline outline-2 outline-danger' : ''}`} />
              {touched.email && !emailValid && (
                <p className="mt-1 text-xs font-medium text-danger">Email chưa đúng định dạng.</p>
              )}
              {emailValid && emailStatus === 'checking' && <p className="mt-1 text-xs text-muted">Đang kiểm tra email…</p>}
              {emailValid && emailStatus === 'available' && (
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-accent-strong"><Check size={12} strokeWidth={3} />Email có thể sử dụng</p>
              )}
              {emailValid && emailStatus === 'taken' && (
                <p className="mt-1 text-xs font-medium text-danger">Email này đã được đăng ký. Hãy dùng email khác hoặc đăng nhập.</p>
              )}
            </FieldGroup>

            <FieldGroup label="Mật khẩu" required>
              <PasswordInput required name="registration-password" autoComplete="new-password"
                value={form.password} onChange={(e) => set('password', e.target.value)} onBlur={() => touch('password')}
                aria-invalid={touched.password && !passwordValid}
                className={`${inputCls} ${touched.password && !passwordValid ? 'outline outline-2 outline-danger' : ''}`} />
              <p className={`mt-1 flex items-center gap-1 text-xs ${passwordValid ? 'text-accent-strong' : touched.password ? 'text-danger' : 'text-muted'}`}>
                {passwordValid && <Check size={12} strokeWidth={3} />}
                Ít nhất 8 ký tự
              </p>
            </FieldGroup>

            <FieldGroup label="Xác nhận mật khẩu" required>
              <PasswordInput required name="registration-password-confirm" autoComplete="new-password"
                value={form.confirm} onChange={(e) => set('confirm', e.target.value)} onBlur={() => touch('confirm')}
                aria-invalid={touched.confirm && !confirmValid}
                className={`${inputCls} ${touched.confirm && !confirmValid ? 'outline outline-2 outline-danger' : ''}`} />
              {(form.confirm || touched.confirm) && (
                <p className={`mt-1 flex items-center gap-1 text-xs font-medium ${confirmValid ? 'text-accent-strong' : 'text-danger'}`}>
                  {confirmValid && <Check size={12} strokeWidth={3} />}
                  {confirmValid ? 'Mật khẩu khớp' : 'Mật khẩu xác nhận không khớp.'}
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
                <TextInput
                  type="date"
                  required
                  min={MIN_BIRTH_DATE}
                  max={MAX_BIRTH_DATE}
                  value={form.birth_date}
                  onChange={(e) => set('birth_date', e.target.value)}
                  aria-invalid={form.birth_date !== '' && !isValidBirthDate(form.birth_date)}
                  className={`w-full ${form.birth_date !== '' && !isValidBirthDate(form.birth_date) ? 'outline outline-2 outline-danger' : ''}`}
                />
                {form.birth_date !== '' && !isValidBirthDate(form.birth_date) && (
                  <p className="mt-1 text-xs font-medium text-danger">
                    Ngày sinh phải từ {MIN_BIRTH_DATE} đến {MAX_BIRTH_DATE}.
                  </p>
                )}
              </FieldGroup>

              <FieldGroup label="Chiều cao (cm)">
                <TextInput type="number" min="50.1" max="249.9" step="0.1" required
                  value={form.height_cm} onChange={(e) => set('height_cm', e.target.value)}
                  aria-invalid={form.height_cm !== '' && !heightValid}
                  className={`w-full ${form.height_cm !== '' && !heightValid ? 'outline outline-2 outline-danger' : ''}`} />
                {form.height_cm !== '' && !heightValid && (
                  <p className="mt-1 text-xs font-medium text-danger">Chiều cao phải lớn hơn 50 cm và nhỏ hơn 250 cm.</p>
                )}
              </FieldGroup>

              <FieldGroup label="Cân nặng (kg)">
                <TextInput type="number" min="20" max="300" step="0.1" required
                  value={form.weight_kg} onChange={(e) => set('weight_kg', e.target.value)}
                  aria-invalid={form.weight_kg !== '' && !weightValid}
                  className={`w-full ${form.weight_kg !== '' && !weightValid ? 'outline outline-2 outline-danger' : ''}`} />
                {form.weight_kg !== '' && !weightValid && (
                  <p className="mt-1 text-xs font-medium text-danger">Cân nặng phải từ 20 đến 300 kg.</p>
                )}
              </FieldGroup>
          </div>

          {heightValid && weightValid && !metricsValid && (
            <Alert tone="danger">Tổ hợp chiều cao và cân nặng không hợp lý. BMI cần nằm trong khoảng 10–80.</Alert>
          )}

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

            <FieldGroup label={`Bệnh nền${form.condition_ids.length + form.custom_conditions.length ? ` (${form.condition_ids.length + form.custom_conditions.length})` : ''}`}>
              <CatalogMultiSelect kind="condition" items={conditions} selected={form.condition_ids}
                onChange={(values) => set('condition_ids', values)} />
              <CustomHealthTerms kind="condition" values={form.custom_conditions}
                existingNames={conditions.map((item) => item.name)} onChange={(values) => set('custom_conditions', values)} />
            </FieldGroup>

            <FieldGroup label={`Dị ứng thực phẩm${form.allergen_ids.length + form.custom_allergens.length ? ` (${form.allergen_ids.length + form.custom_allergens.length})` : ''}`}>
              <CatalogMultiSelect kind="allergen" items={allergens} selected={form.allergen_ids}
                onChange={(values) => set('allergen_ids', values)} />
              <CustomHealthTerms kind="allergen" values={form.custom_allergens}
                existingNames={allergens.map((item) => item.name)} onChange={(values) => set('custom_allergens', values)} />
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
          <Btn type="submit" variant="primary"
            disabled={loading || emailStatus === 'checking' || (step === 1 ? !step1Valid : !step2Valid)} className="flex-1">
            {step === 1 ? emailStatus === 'checking' ? 'Đang kiểm tra email…' : 'Tiếp tục' : loading ? 'Đang tạo tài khoản…' : 'Hoàn tất đăng ký'}
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
function FieldGroup({ label, hint, required, children }) {
  return (
    <div>
      <label className="mb-1 block text-base font-medium text-ink-2">
        {label}{required && <span className="ml-0.5 text-danger" aria-hidden="true">*</span>}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}
