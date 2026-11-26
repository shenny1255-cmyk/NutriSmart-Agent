import { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Check, Mail, ShieldCheck } from 'lucide-react';
import { api } from '../lib/api.js';
import { isValidBirthDate, MAX_BIRTH_DATE, MIN_BIRTH_DATE, calculateAge, getBirthDateValidationError } from '../lib/date.js';
import { areBodyMetricsPlausible, bodyMetricsBmi, isValidFullName, calculateTdee, getRegistrationEmailError } from '../lib/validation.js';
import PasswordInput from '../components/PasswordInput.jsx';
import PasswordStrength from '../components/PasswordStrength.jsx';
import { isStrongPassword } from '../lib/password.js';
import CatalogMultiSelect from '../components/CatalogMultiSelect.jsx';
import { Btn, Field as TextInput, Select, Alert } from '../components/ui.jsx';
import AuthLayout from '../components/AuthLayout.jsx';
import { LogoMark } from '../components/Logo.jsx';
import { inputCls } from './login.jsx';
import { POLICY_VERSION } from './Privacy.jsx';

const isEmail = (s) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((s || '').trim());

// Fallback khi backend chưa chạy - sau này lấy từ API
const FALLBACK_CONDITIONS = [{ id: 1, name: 'Đái tháo đường típ 2' }, { id: 2, name: 'Tăng huyết áp' }, { id: 3, name: 'Rối loạn lipid máu' }];
const FALLBACK_ALLERGENS = [{ id: 1, name: 'Đậu phộng' }, { id: 2, name: 'Hải sản có vỏ' }, { id: 3, name: 'Sữa bò' }, { id: 4, name: 'Gluten' }];

const ACTIVITY_LEVELS = [
  { value: 1, label: 'Ít vận động (ngồi nhiều)' },
  { value: 2, label: 'Vận động nhẹ (1-3 buổi/tuần)' },
  { value: 3, label: 'Vận động vừa (3-5 buổi/tuần)' },
  { value: 4, label: 'Vận động nhiều (6-7 buổi/tuần)' },
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
  // Đồng ý (Nghị định 13/2023): KHÔNG tick sẵn - người dùng phải tự chọn từng mục
  consent_terms: false, consent_health: false, consent_cloud: false,
};

const STEP_TITLES = ['Thông tin tài khoản', 'Xác thực Email', 'Hồ sơ sức khỏe', 'Quyền riêng tư'];

const DISPOSABLE_MSG = 'Vui lòng sử dụng địa chỉ email chính thức (không sử dụng email tạm thời/dùng một lần).';

export default function Register() {
  const [step, setStep] = useState(1);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [emailStatus, setEmailStatus] = useState('idle');
  const [emailBlockedMsg, setEmailBlockedMsg] = useState('');
  const emailCheckId = useRef(0);
  const [touched, setTouched] = useState({ full_name: false, email: false, password: false, confirm: false });
  const navigate = useNavigate();

  const [conditions, setConditions] = useState(FALLBACK_CONDITIONS);
  const [allergens, setAllergens] = useState(FALLBACK_ALLERGENS);
  // Quốc gia đã bỏ (mặc định Việt Nam)

  const [form, setForm] = useState(INITIAL_FORM);
  const [showPassword, setShowPassword] = useState(false);
  const [pin, setPin] = useState('');
  const [pinToken, setPinToken] = useState('');
  const [pinCooldown, setPinCooldown] = useState(0);
  const [pinLoading, setPinLoading] = useState(false);
  // Honeypot: ô ẩn với người dùng, bot điền tự động sẽ bị backend chặn
  const [website, setWebsite] = useState('');

  const set = (k, v) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (k === 'email') {
      emailCheckId.current += 1;
      setEmailStatus('idle');
      setPin('');
      setPinToken('');
    }
    setErr(null);
  };
  const touch = (key) => setTouched((current) => ({ ...current, [key]: true }));
  const fullNameValid = isValidFullName(form.full_name);
  const emailValid = isEmail(form.email);
  const emailPolicyError = emailValid ? getRegistrationEmailError(form.email) : '';
  const passwordValid = isStrongPassword(form.password);
  const confirmValid = form.confirm !== '' && form.confirm === form.password;
  const emailRejected = Boolean(emailPolicyError) || emailStatus === 'taken' || emailStatus === 'blocked' || emailStatus === 'disposable';
  const step1Valid = fullNameValid && emailValid && passwordValid && confirmValid && !emailRejected;
  const heightNumber = Number(form.height_cm);
  const weightNumber = Number(form.weight_kg);
  const heightValid = form.height_cm !== '' && Number.isFinite(heightNumber) && heightNumber > 50 && heightNumber < 250;
  const weightValid = form.weight_kg !== '' && Number.isFinite(weightNumber) && weightNumber >= 20 && weightNumber <= 300;
  const metricsValid = heightValid && weightValid && areBodyMetricsPlausible(heightNumber, weightNumber);
  const age = calculateAge(form.birth_date);
  const birthDateValid = isValidBirthDate(form.birth_date);
  const birthDateError = form.birth_date !== '' ? getBirthDateValidationError(form.birth_date) : '';
  const liveTdee = birthDateValid && metricsValid
    ? calculateTdee({
        gender: form.gender,
        age,
        height_cm: heightNumber,
        weight_kg: weightNumber,
        activity_level: Number(form.activity_level) || 3,
      })
    : null;
  const step2PinValid = /^\d{6}$/.test(pin);
  const step3Valid = birthDateValid && metricsValid;
  const step4Valid = form.consent_terms && form.consent_health;
  const stepValid = [step1Valid, step2PinValid, step3Valid, step4Valid][step - 1];

  useEffect(() => {
    if (pinCooldown <= 0) return undefined;
    const timer = setTimeout(() => setPinCooldown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [pinCooldown]);

  useEffect(() => {
    api.conditions().then(setConditions).catch(() => { });
    api.allergens().then(setAllergens).catch(() => { });
  }, []);

  async function checkEmail() {
    if (!emailValid) return 'invalid';
    const localPolicyError = getRegistrationEmailError(form.email);
    if (localPolicyError) {
      setEmailBlockedMsg(localPolicyError);
      setEmailStatus('blocked');
      return 'blocked';
    }
    const email = form.email.trim().toLowerCase();
    const checkId = ++emailCheckId.current;
    setEmailStatus('checking');
    try {
      const result = await api.checkEmail(email);
      if (checkId !== emailCheckId.current) return 'stale';
      const status = result.available
        ? 'available'
        : result.reason === 'not_allowed' || result.reason === 'disposable'
        ? 'blocked'
        : 'taken';
      setEmailBlockedMsg(status === 'blocked' ? (result.message || DISPOSABLE_MSG) : '');
      setEmailStatus(status);
      return status;
    } catch {
      if (checkId === emailCheckId.current) {
        setEmailStatus('error');
        setErr('Không kiểm tra được email. Vui lòng thử lại.');
      }
      return 'error';
    }
  }

  async function sendPinCode() {
    setPinLoading(true);
    setErr(null);
    try {
      await api.sendRegisterPin(form.email.trim().toLowerCase());
      setPinCooldown(60);
      return true;
    } catch (e) {
      if (e.status === 429 && typeof e.detail === 'string') {
        setErr(e.detail);
      } else {
        setErr(typeof e.detail === 'string' ? e.detail : 'Không thể gửi mã PIN. Vui lòng thử lại.');
      }
      return false;
    } finally {
      setPinLoading(false);
    }
  }

  async function nextStep(e) {
    e.preventDefault();
    setTouched({ full_name: true, email: true, password: true, confirm: true });
    if (!fullNameValid) return setErr('Họ và tên chưa hợp lệ.');
    if (!emailValid) return setErr('Email chưa đúng định dạng.');
    if (emailPolicyError) return setErr(emailPolicyError);
    if (!passwordValid) return setErr('Mật khẩu chưa đủ mạnh. Vui lòng đáp ứng đủ 4 tiêu chí bên dưới ô mật khẩu.');
    if (!confirmValid) return setErr('Mật khẩu xác nhận không khớp.');
    if (emailStatus !== 'available') {
      const checked = await checkEmail();
      if (checked !== 'available') {
        if (checked === 'taken') setErr('Email này đã được đăng ký. Hãy dùng email khác hoặc đăng nhập.');
        if (checked === 'blocked' || checked === 'disposable') setErr(emailBlockedMsg || DISPOSABLE_MSG);
        return;
      }
    }
    if (pinToken) {
      setErr(null);
      setStep(3);
      return;
    }
    const ok = await sendPinCode();
    if (ok) {
      setErr(null);
      setStep(2);
    }
  }

  async function verifyPinStep(e) {
    e.preventDefault();
    if (!step2PinValid) return setErr('Vui lòng nhập đủ 6 chữ số của mã PIN.');
    setPinLoading(true);
    setErr(null);
    try {
      const res = await api.verifyRegisterPin(form.email.trim().toLowerCase(), pin);
      setPinToken(res.pin_token);
      setStep(3);
    } catch (e) {
      setErr(typeof e.detail === 'string' ? e.detail : 'Mã PIN không đúng hoặc đã hết hạn.');
    } finally {
      setPinLoading(false);
    }
  }

  function profileError() {
    if (!birthDateValid) {
      return birthDateError || `Ngày sinh không hợp lệ. Độ tuổi hợp lệ từ 15 đến 100 tuổi (từ ${MIN_BIRTH_DATE} đến ${MAX_BIRTH_DATE}).`;
    }
    if (!metricsValid) return 'Chiều cao hoặc cân nặng chưa hợp lệ. Vui lòng kiểm tra lại.';
    return null;
  }

  function toConsent(e) {
    e.preventDefault();
    const msg = profileError();
    setErr(msg);
    if (!msg) setStep(4);
  }

  async function submit(e) {
    e.preventDefault();
    setErr(null);
    if (!pinToken) { setErr('Vui lòng xác thực email bằng mã PIN.'); setStep(2); return; }
    const msg = profileError();
    if (msg) { setErr(msg); setStep(3); return; }
    if (!step4Valid) {
      setErr('Bạn cần đồng ý hai mục bắt buộc để tạo tài khoản.');
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
      consents: {
        terms: form.consent_terms,
        health_data: form.consent_health,
        cloud_ai: form.consent_cloud,
      },
      honeypot: website || null,
      pin_token: pinToken,
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
      else if (e.status === 422) {
        // Lấy thông báo tiếng Việt của validator; lỗi email/mật khẩu thì quay về bước 1 để sửa
        const emailIssue = Array.isArray(e.detail) && e.detail.find((d) => d?.loc?.includes('email'));
        const passwordIssue = Array.isArray(e.detail) && e.detail.find((d) => d?.loc?.includes('password'));
        const issue = emailIssue || passwordIssue || (Array.isArray(e.detail) ? e.detail[0] : null);
        const reason = issue?.msg?.replace(/^Value error,\s*/, '');
        if (reason) setErr(reason);
        else setErr('Thông tin chưa hợp lệ - kiểm tra lại email và mật khẩu.');
        if (emailIssue || passwordIssue) setStep(1);
      }
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
        onSubmit={step === 1 ? nextStep : step === 2 ? verifyPinStep : step === 3 ? toConsent : submit}
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
              Bước {step}/4 - {STEP_TITLES[step - 1]}
            </p>
          </div>
        </div>

        {/* Thanh tiến trình - scaleX (transform), không animate width */}
        <div className="mb-6 h-1 w-full overflow-hidden rounded-full bg-paper-3">
          <div
            className="h-full origin-left rounded-full bg-accent transition-transform duration-long ease-out"
            style={{ transform: `scaleX(${step / 4})` }}
          />
        </div>

        {/* Honeypot chống bot: ẩn khỏi người dùng và trình đọc màn hình, không nhận focus bằng Tab */}
        <div aria-hidden="true" className="pointer-events-none absolute -left-[9999px] h-px w-px overflow-hidden opacity-0">
          <label htmlFor="website_url">Website</label>
          <input
            id="website_url" name="website_url" type="text" tabIndex={-1} autoComplete="off"
            value={website} onChange={(e) => setWebsite(e.target.value)}
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
                  Nhập 2-100 ký tự; không dùng emoji hoặc ký tự đặc biệt.
                </p>
              )}
            </FieldGroup>

            <FieldGroup label="Email" required>
              <TextInput type="email" required name="registration-email" autoComplete="off"
                value={form.email}
                onChange={(e) => {
                  set('email', e.target.value);
                  setTouched((t) => ({ ...t, email: false }));
                }}
                onBlur={() => { touch('email'); if (emailValid) checkEmail(); }}
                aria-invalid={(touched.email && (!emailValid || Boolean(emailPolicyError))) || emailStatus === 'taken' || emailStatus === 'blocked'}
                className={`w-full ${(touched.email && (!emailValid || Boolean(emailPolicyError))) || emailStatus === 'taken' || emailStatus === 'blocked' ? 'outline outline-2 outline-danger' : ''}`} />
              {touched.email && !emailValid && (
                <p className="mt-1 text-xs font-medium text-danger">Email chưa đúng định dạng.</p>
              )}
              {touched.email && emailValid && emailPolicyError && (
                <p className="mt-1 text-xs font-medium text-danger">{emailPolicyError}</p>
              )}
              {emailValid && !emailPolicyError && emailStatus === 'checking' && <p className="mt-1 text-xs text-muted">Đang kiểm tra email…</p>}
              {emailValid && !emailPolicyError && emailStatus === 'available' && (
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-accent-strong"><Check size={12} strokeWidth={3} />Email có thể sử dụng</p>
              )}
              {emailValid && !emailPolicyError && emailStatus === 'disposable' && (
                <p className="mt-1 text-xs font-medium text-danger">{DISPOSABLE_MSG}</p>
              )}
              {emailValid && !emailPolicyError && emailStatus === 'taken' && (
                <p className="mt-1 text-xs font-medium text-danger">Email này đã được đăng ký. Hãy dùng email khác hoặc đăng nhập.</p>
              )}
              {emailValid && !emailPolicyError && emailStatus === 'blocked' && (
                <p className="mt-1 text-xs font-medium text-danger">{emailBlockedMsg}</p>
              )}
              {(!touched.email || (!emailPolicyError && emailValid)) && emailStatus === 'idle' && (
                <p className="mt-1 text-xs text-muted">Ưu tiên Gmail, Outlook, Yahoo, iCloud hoặc email trường học/cơ quan (.edu.vn, .gov.vn).</p>
              )}
            </FieldGroup>

            <FieldGroup label="Mật khẩu" required>
              <PasswordInput required name="registration-password" autoComplete="new-password"
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                onBlur={() => touch('password')}
                visible={showPassword} onVisibleChange={setShowPassword}
                aria-invalid={touched.password && !passwordValid}
                className={`${inputCls} ${touched.password && !passwordValid ? 'outline outline-2 outline-danger' : ''}`} />
              <PasswordStrength password={form.password} />
            </FieldGroup>

            <FieldGroup label="Xác nhận mật khẩu" required>
              <PasswordInput required name="registration-password-confirm" autoComplete="new-password"
                value={form.confirm} onChange={(e) => set('confirm', e.target.value)} onBlur={() => touch('confirm')}
                visible={showPassword} onVisibleChange={setShowPassword}
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
            <div className="flex gap-3 rounded-sm bg-accent-soft p-4 text-sm text-ink-2">
              <Mail size={20} className="mt-0.5 shrink-0 text-accent-strong" aria-hidden="true" />
              <div className="space-y-1">
                <p>
                  Mã PIN gồm <strong>6 chữ số</strong> đã được gửi tới{' '}
                  <strong className="text-ink">{form.email.trim().toLowerCase()}</strong>.
                </p>
                <p className="text-xs text-muted">
                  Vui lòng kiểm tra hộp thư đến (hoặc mục Spam/Quảng cáo). Mã có hiệu lực trong 10 phút.
                </p>
              </div>
            </div>

            <FieldGroup label="Mã PIN xác nhận (6 chữ số)" required>
              <TextInput
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                required
                placeholder="Nhập 6 chữ số (vd: 123456)"
                value={pin}
                onChange={(e) => {
                  setPin(e.target.value.replace(/\D/g, '').slice(0, 6));
                  setErr(null);
                }}
                className="w-full text-center font-mono text-lg tracking-[0.4em]"
              />
            </FieldGroup>

            <div className="flex items-center justify-between text-xs">
              <span className="text-muted">Chưa nhận được mã?</span>
              <button
                type="button"
                disabled={pinCooldown > 0 || pinLoading}
                onClick={sendPinCode}
                className="font-semibold text-accent-strong hover:underline disabled:cursor-not-allowed disabled:text-muted disabled:no-underline"
              >
                {pinCooldown > 0 ? `Gửi lại mã sau ${pinCooldown}s` : 'Gửi lại mã PIN'}
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
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
                  aria-invalid={form.birth_date !== '' && !birthDateValid}
                  className={`w-full ${form.birth_date !== '' && !birthDateValid ? 'outline outline-2 outline-danger' : ''}`}
                />
                {form.birth_date !== '' && !birthDateValid && (
                  <p className="mt-1 text-xs font-medium text-danger">
                    {birthDateError || `Ngày sinh phải từ ${MIN_BIRTH_DATE} đến ${MAX_BIRTH_DATE} (từ 15 đến 100 tuổi).`}
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
            <Alert tone="danger">Tổ hợp chiều cao và cân nặng không hợp lý. BMI cần nằm trong khoảng 10-80.</Alert>
          )}

          {metricsValid && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {bmi && (
                <span className="rounded-sm bg-accent-soft px-3 py-2 text-sm text-accent-strong">
                  BMI dự kiến: <b className="[font-variant-numeric:tabular-nums]">{bmi}</b>
                </span>
              )}
              <span className={`rounded-sm px-3 py-2 text-sm ${liveTdee ? 'bg-accent-soft text-accent-strong' : 'bg-paper-3 text-muted'}`}>
                ⚡ TDEE ước tính live:{' '}
                <b className="[font-variant-numeric:tabular-nums]">{liveTdee ? `${liveTdee} kcal` : '-- kcal'}</b>
              </span>
            </div>
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

            <FieldGroup label={`Bệnh nền${form.condition_ids.length ? ` (${form.condition_ids.length})` : ''}`}>
              <CatalogMultiSelect kind="condition" items={conditions} selected={form.condition_ids}
                onChange={(values) => set('condition_ids', values)} />
            </FieldGroup>

            <FieldGroup label={`Dị ứng thực phẩm${form.allergen_ids.length ? ` (${form.allergen_ids.length})` : ''}`}>
              <CatalogMultiSelect kind="allergen" items={allergens} selected={form.allergen_ids}
                onChange={(values) => set('allergen_ids', values)} />
            </FieldGroup>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <div className="flex gap-3 rounded-sm bg-accent-soft p-4 text-sm text-ink-2">
              <ShieldCheck size={20} className="mt-0.5 shrink-0 text-accent-strong" aria-hidden="true" />
              <div className="space-y-1.5">
                <p>Hồ sơ sức khỏe (bệnh nền, dị ứng, số đo cơ thể) là <strong>dữ liệu cá nhân nhạy cảm</strong>.
                  NutriSmart chỉ dùng nó để tính calo, gợi ý thực đơn và cảnh báo an toàn cho chính bạn,
                  không bán và không dùng cho quảng cáo.</p>
                <p>Bạn đổi lựa chọn về AI đám mây bất cứ lúc nào trong trang Hồ sơ.{' '}
                  <Link to="/privacy" target="_blank" rel="noopener"
                    className="font-medium text-accent-strong underline underline-offset-2">Đọc chính sách đầy đủ</Link>
                </p>
              </div>
            </div>

            <ConsentBox checked={form.consent_terms} onChange={(v) => set('consent_terms', v)} required
              title="Tôi đã đọc và đồng ý Điều khoản sử dụng và Chính sách quyền riêng tư"
              desc={`Phiên bản ${POLICY_VERSION}. NutriSmart hỗ trợ tham khảo, không thay thế chẩn đoán hay tư vấn của bác sĩ.`} />

            <ConsentBox checked={form.consent_health} onChange={(v) => set('consent_health', v)} required
              title="Tôi đồng ý cho NutriSmart xử lý dữ liệu sức khỏe của tôi"
              desc="Gồm bệnh nền, dị ứng, số đo cơ thể và nhật ký ăn uống - cần để tính calo mục tiêu, lập lộ trình và cảnh báo món không an toàn. Thiếu mục này ứng dụng không hoạt động được." />

            <ConsentBox checked={form.consent_cloud} onChange={(v) => set('consent_cloud', v)}
              title="Cho phép dùng AI đám mây (Google Gemini) - không bắt buộc"
              desc="Trả lời nhanh hơn (khoảng 3 giây thay vì 15-20 giây) và mở khóa phân tích ảnh món ăn. Trước khi gửi, hệ thống xóa họ tên, email, số điện thoại và chỉ gửi khoảng tuổi. Không chọn: mọi xử lý chạy bằng AI nội bộ trên máy chủ NutriSmart, tính năng phân tích ảnh tạm khóa." />
          </div>
        )}

        {err && <div className="mt-4"><Alert tone="danger">{err}</Alert></div>}

        <div className="mt-6 flex gap-3">
          {step > 1 && (
            <Btn type="button" variant="ghost" onClick={() => {
              setErr(null);
              setStep(step === 3 && pinToken ? 1 : step - 1);
            }}>
              Quay lại
            </Btn>
          )}
          <Btn type="submit" variant="primary"
            disabled={loading || pinLoading || emailStatus === 'checking' || !stepValid} className="flex-1">
            {step === 1 && emailStatus === 'checking' ? 'Đang kiểm tra email…'
              : (step === 1 || step === 2) && pinLoading ? 'Đang xử lý…'
              : step === 2 ? 'Xác nhận mã PIN'
              : step < 4 ? 'Tiếp tục'
              : loading ? 'Đang tạo tài khoản…' : 'Đồng ý và tạo tài khoản'}
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

function ConsentBox({ checked, onChange, title, desc, required }) {
  return (
    <label className={`flex cursor-pointer items-start gap-3 rounded-sm border p-3.5 transition-colors duration-micro ${
      checked ? 'border-accent bg-accent-soft/40' : 'border-rule-2 bg-paper'}`}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 shrink-0 accent-[var(--color-accent-strong)]" aria-required={required || undefined} />
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-ink">
          {title}{required && <span className="ml-1 text-danger" aria-hidden="true">*</span>}
        </span>
        <span className="mt-1 block text-sm text-ink-2">{desc}</span>
      </span>
    </label>
  );
}
