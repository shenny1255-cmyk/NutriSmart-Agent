import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Check, Save, ShieldCheck, User } from 'lucide-react';
import { api } from '../lib/api.js';
import { isValidBirthDate, MAX_BIRTH_DATE, MIN_BIRTH_DATE, calculateAge, getBirthDateValidationError } from '../lib/date.js';
import { areBodyMetricsPlausible, bodyMetricsBmi, isValidFullName, calculateTdee } from '../lib/validation.js';
import { Btn, Field as TextInput, Select, Alert, Modal, useToast, Toast } from '../components/ui.jsx';
import CatalogMultiSelect from '../components/CatalogMultiSelect.jsx';
import CustomHealthTerms from '../components/CustomHealthTerms.jsx';

// Danh sách fallback khi backend chưa chạy
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

const ROLE_LABELS = { ADMIN: 'Quản trị viên', EXPERT: 'Chuyên gia', USER: 'Người dùng' };

export default function Profile() {
  const navigate = useNavigate();
  const { toast, show } = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedRecently, setSavedRecently] = useState(false);
  const [pendingTarget, setPendingTarget] = useState(null);
  const [err, setErr] = useState(null);
  const initialFormRef = useRef('');
  const countLabel = (label, n) => (n ? `${label} (${n})` : label);

  // Dữ liệu dropdown
  const [conditions, setConditions] = useState(FALLBACK_CONDITIONS);
  const [allergens, setAllergens] = useState(FALLBACK_ALLERGENS);

  // Form state
  const [form, setForm] = useState({
    email: '', role: '', full_name: '',
    gender: 'MALE', birth_date: '', height_cm: '', weight_kg: '',
    activity_level: 3, goal: 'MAINTAIN',
    condition_ids: [], allergen_ids: [],
    custom_conditions: [], custom_allergens: [],
    daily_calorie_target: null,
    ai_local_only: false,
  });

  const set = (k, v) => {
    setSavedRecently(false);
    setForm((f) => ({ ...f, [k]: v }));
  };

  const [termsConsent, setTermsConsent] = useState(null);

  // Lấy thông tin người dùng hiện tại + dropdown khi mount
  useEffect(() => {
    Promise.all([
      api.me(),
      api.conditions().catch(() => FALLBACK_CONDITIONS),
      api.allergens().catch(() => FALLBACK_ALLERGENS),
    ]).then(([me, conds, alls]) => {
      setConditions(conds);
      setAllergens(alls);

      const p = me.profile;
      const loadedForm = {
        email: me.email || '',
        role: me.role || 'USER',
        full_name: me.full_name || '',
        // country_code đã bỏ (mặc định Việt Nam)
        gender: p?.gender || 'MALE',
        birth_date: p?.birth_date || '',
        height_cm: p?.height_cm ?? '',
        weight_kg: p?.weight_kg ?? '',
        activity_level: p?.activity_level ?? 3,
        goal: p?.goal || 'MAINTAIN',
        condition_ids: (p?.conditions || []).map((c) => c.id),
        allergen_ids: (p?.allergens || []).map((a) => a.id),
        custom_conditions: p?.custom_conditions || [],
        custom_allergens: p?.custom_allergens || [],
        daily_calorie_target: p?.daily_calorie_target ?? null,
        ai_local_only: Boolean(p?.ai_local_only),
      };
      setForm(loadedForm);
      initialFormRef.current = JSON.stringify(loadedForm);
      setLoading(false);
    }).catch(() => setLoading(false));
    // Lần đồng ý điều khoản gần nhất (mới nhất trước); lỗi thì chỉ ẩn dòng thông tin
    api.consents()
      .then((rows) => setTermsConsent(rows.find((r) => r.consent_type === 'TERMS' && r.granted) || null))
      .catch(() => {});
  }, []);

  const fullNameValid = isValidFullName(form.full_name);
  const age = calculateAge(form.birth_date);
  const birthDateValid = isValidBirthDate(form.birth_date);
  const birthDateError = form.birth_date !== '' ? getBirthDateValidationError(form.birth_date) : '';
  const heightNumber = Number(form.height_cm);
  const weightNumber = Number(form.weight_kg);
  const heightValid = form.height_cm !== '' && Number.isFinite(heightNumber) && heightNumber > 50 && heightNumber < 250;
  const weightValid = form.weight_kg !== '' && Number.isFinite(weightNumber) && weightNumber >= 20 && weightNumber <= 300;
  const metricsValid = heightValid && weightValid && areBodyMetricsPlausible(heightNumber, weightNumber);
  // Chỉ hiển thị BMI khi cả hai số đo đều hợp lệ.
  const bmi = metricsValid
    ? bodyMetricsBmi(heightNumber, weightNumber).toFixed(1)
    : null;
  // Tính TDEE live khi số đo và ngày sinh đều hợp lệ (15 <= tuổi <= 100).
  const liveTdee = birthDateValid && metricsValid
    ? calculateTdee({
        gender: form.gender,
        age,
        height_cm: heightNumber,
        weight_kg: weightNumber,
        activity_level: Number(form.activity_level) || 3,
      })
    : null;
  const dirty = !loading && initialFormRef.current !== '' && JSON.stringify(form) !== initialFormRef.current;

  useEffect(() => {
    const warnBeforeUnload = (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warnBeforeUnload);
    return () => window.removeEventListener('beforeunload', warnBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    if (!dirty) return undefined;
    const interceptInternalLink = (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = event.target.closest?.('a[href]');
      if (!anchor || anchor.target === '_blank' || anchor.hasAttribute('download')) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      const target = `${url.pathname}${url.search}${url.hash}`;
      const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (target === current) return;
      event.preventDefault();
      event.stopPropagation();
      setPendingTarget(target);
    };
    document.addEventListener('click', interceptInternalLink, true);
    return () => document.removeEventListener('click', interceptInternalLink, true);
  }, [dirty]);

  function navigateAway(target) {
    if (target === -1) navigate(-1);
    else navigate(target);
  }

  function requestLeave(target = -1) {
    if (dirty) setPendingTarget(target);
    else navigateAway(target);
  }

  function discardAndLeave() {
    const target = pendingTarget;
    initialFormRef.current = JSON.stringify(form);
    setPendingTarget(null);
    window.setTimeout(() => navigateAway(target), 0);
  }

  async function saveProfile() {
    setErr(null);
    if (!fullNameValid) {
      setErr('Họ và tên chưa hợp lệ. Vui lòng kiểm tra lại.');
      return false;
    }
    if (!birthDateValid) {
      setErr(birthDateError || `Ngày sinh không hợp lệ. Độ tuổi hợp lệ từ 15 đến 100 tuổi (từ ${MIN_BIRTH_DATE} đến ${MAX_BIRTH_DATE}).`);
      return false;
    }
    if (!metricsValid) {
      setErr('Chiều cao hoặc cân nặng chưa hợp lệ. Vui lòng kiểm tra lại.');
      return false;
    }
    setSaving(true);
    try {
      const payload = {
        full_name: form.full_name,
        // country_code đã bỏ khỏi user_info
        gender: form.gender,
        birth_date: form.birth_date || null,
        height_cm: heightNumber,
        weight_kg: weightNumber,
        activity_level: Number(form.activity_level),
        goal: form.goal,
        condition_ids: form.condition_ids,
        allergen_ids: form.allergen_ids,
      };
      // Mục tự khai báo chỉ gửi khi người dùng thật sự xóa bớt. Gửi mặc định có rủi ro: nếu lúc
      // tải trang lỗi, form còn [] và bấm Lưu sẽ xóa sạch dị ứng mà Warning Engine đang dùng.
      const initial = initialFormRef.current ? JSON.parse(initialFormRef.current) : {};
      for (const key of ['custom_conditions', 'custom_allergens']) {
        if (JSON.stringify(form[key]) !== JSON.stringify(initial[key])) payload[key] = form[key];
      }
      const updated = await api.updateProfile(payload);

      // Cập nhật lại form với dữ liệu mới từ server (bao gồm calo mục tiêu đã tính lại)
      const savedForm = {
        ...form,
        daily_calorie_target: updated.profile?.daily_calorie_target ?? form.daily_calorie_target,
      };
      setForm(savedForm);
      initialFormRef.current = JSON.stringify(savedForm);
      setSavedRecently(true);
      window.setTimeout(() => setSavedRecently(false), 1800);
      show('Đã lưu thông tin thành công!', 'success');
      return true;
    } catch (e) {
      if (e.status === 422) setErr('Thông tin chưa hợp lệ - vui lòng kiểm tra lại.');
      else setErr(typeof e.detail === 'string' ? e.detail : 'Lưu thất bại, thử lại sau.');
      return false;
    } finally {
      setSaving(false);
    }
  }

  // Công tắc quyền riêng tư lưu NGAY, độc lập với form hồ sơ: người chưa điền đủ số đo
  // (nút Lưu bị khóa) vẫn phải bật/tắt được việc gửi dữ liệu ra AI bên ngoài.
  const [privacySaving, setPrivacySaving] = useState(false);
  async function togglePrivacy(next) {
    setPrivacySaving(true);
    setForm((f) => ({ ...f, ai_local_only: next }));
    try {
      await api.updateProfile({ ai_local_only: next });
      const base = JSON.parse(initialFormRef.current || '{}');
      initialFormRef.current = JSON.stringify({ ...base, ai_local_only: next });
      show(next ? 'Đã bật: chỉ xử lý bằng AI nội bộ.' : 'Đã tắt: cho phép dùng AI bên ngoài (đã ẩn danh).', 'success');
    } catch (e) {
      setForm((f) => ({ ...f, ai_local_only: !next }));
      show(typeof e.detail === 'string' ? e.detail : 'Không lưu được cài đặt, thử lại sau.', 'danger');
    } finally {
      setPrivacySaving(false);
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    await saveProfile();
  }

  async function saveAndLeave() {
    const target = pendingTarget;
    if (await saveProfile()) {
      setPendingTarget(null);
      navigateAway(target);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <p className="text-sm text-muted">Đang tải thông tin…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button
          onClick={() => requestLeave(-1)}
          className="flex h-9 w-9 items-center justify-center rounded-md text-ink-2 transition-colors duration-short ease-out hover:bg-paper-3"
          aria-label="Quay lại"
        >
          <ArrowLeft size={18} />
        </button>
        <h1 className="font-display text-2xl font-bold tracking-tight">Thông tin cá nhân</h1>
      </header>

      <form onSubmit={handleSave} className="space-y-6">
        {/* ── Thông tin tài khoản ─────────────────────────────────── */}
        <section className="rounded-md bg-paper-2 p-5 shadow-hairline sm:p-6">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
              <User size={20} />
            </span>
            <h2 className="font-display text-lg font-bold">Tài khoản</h2>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FieldGroup label="Họ và tên">
              <TextInput
                required
                maxLength={100}
                value={form.full_name}
                onChange={(e) => set('full_name', e.target.value)}
                aria-invalid={form.full_name !== '' && !fullNameValid}
                className={`w-full ${form.full_name !== '' && !fullNameValid ? 'outline outline-2 outline-danger' : ''}`}
              />
              {form.full_name !== '' && !fullNameValid && (
                <p className="mt-1 text-xs font-medium text-danger">
                  Nhập 2-100 ký tự; không dùng emoji hoặc ký tự đặc biệt.
                </p>
              )}
            </FieldGroup>

            <FieldGroup label="Email" hint="Không thể thay đổi">
              <TextInput value={form.email} disabled className="w-full" />
            </FieldGroup>

            <FieldGroup label="Vai trò">
              <TextInput value={ROLE_LABELS[form.role] || form.role} disabled className="w-full" />
            </FieldGroup>
          </div>
        </section>

        {/* ── Hồ sơ sức khỏe & Thể chất ─────────────────────────── */}
        <section className="rounded-md bg-paper-2 p-5 shadow-hairline sm:p-6">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-warning-soft text-warning-strong">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3.332.835-4.5 2.165C10.832 3.835 9.24 3 7.5 3A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
            </span>
            <h2 className="font-display text-lg font-bold">Hồ sơ sức khỏe</h2>
          </div>

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
              <TextInput
                type="number" min="50.1" max="249.9" step="0.1" required
                value={form.height_cm}
                onChange={(e) => set('height_cm', e.target.value)}
                aria-invalid={form.height_cm !== '' && !heightValid}
                className={`w-full ${form.height_cm !== '' && !heightValid ? 'outline outline-2 outline-danger' : ''}`}
              />
              {form.height_cm !== '' && !heightValid && (
                <p className="mt-1 text-xs font-medium text-danger">Chiều cao phải lớn hơn 50 cm và nhỏ hơn 250 cm.</p>
              )}
            </FieldGroup>

            <FieldGroup label="Cân nặng (kg)">
              <TextInput
                type="number" min="20" max="300" step="0.1" required
                value={form.weight_kg}
                onChange={(e) => set('weight_kg', e.target.value)}
                aria-invalid={form.weight_kg !== '' && !weightValid}
                className={`w-full ${form.weight_kg !== '' && !weightValid ? 'outline outline-2 outline-danger' : ''}`}
              />
              {form.weight_kg !== '' && !weightValid && (
                <p className="mt-1 text-xs font-medium text-danger">Cân nặng phải từ 20 đến 300 kg.</p>
              )}
            </FieldGroup>
          </div>

          {heightValid && weightValid && !metricsValid && (
            <div className="mt-3"><Alert tone="danger">Tổ hợp chiều cao và cân nặng không hợp lý. BMI cần nằm trong khoảng 10-80.</Alert></div>
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

          {metricsValid && birthDateValid && form.daily_calorie_target && (
            <p className="mt-2 rounded-sm bg-accent-soft px-3 py-2 text-sm text-accent-strong">
              🎯 Mục tiêu calo hàng ngày: <b className="[font-variant-numeric:tabular-nums]">{form.daily_calorie_target}</b> kcal
            </p>
          )}

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
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
          </div>

          <div className="mt-4 space-y-4">
            <FieldGroup label={countLabel('Bệnh nền', form.condition_ids.length + form.custom_conditions.length)}>
              <CatalogMultiSelect kind="condition" items={conditions} selected={form.condition_ids}
                hideEmpty={form.custom_conditions.length > 0} onChange={(values) => set('condition_ids', values)} />
              <CustomHealthTerms kind="condition" allowAdd={false} values={form.custom_conditions}
                onChange={(values) => set('custom_conditions', values)} />
            </FieldGroup>

            <FieldGroup label={countLabel('Dị ứng thực phẩm', form.allergen_ids.length + form.custom_allergens.length)}>
              <CatalogMultiSelect kind="allergen" items={allergens} selected={form.allergen_ids}
                hideEmpty={form.custom_allergens.length > 0} onChange={(values) => set('allergen_ids', values)} />
              <CustomHealthTerms kind="allergen" allowAdd={false} values={form.custom_allergens}
                onChange={(values) => set('custom_allergens', values)} />
            </FieldGroup>
          </div>
        </section>

        <section className="rounded-md bg-paper-2 p-5 shadow-hairline sm:p-6" aria-labelledby="privacy-heading">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
              <ShieldCheck size={18} aria-hidden="true" />
            </span>
            <h2 id="privacy-heading" className="font-display text-lg font-bold">Quyền riêng tư và AI</h2>
          </div>
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 shrink-0 accent-[var(--color-accent-strong)]"
              checked={form.ai_local_only}
              disabled={privacySaving}
              onChange={(e) => togglePrivacy(e.target.checked)}
            />
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-ink">Chỉ xử lý bằng AI nội bộ</span>
              <span className="mt-1 block text-sm text-ink-2">
                Khi bật, hồ sơ sức khỏe và tin nhắn của bạn chỉ được xử lý trên máy chủ của NutriSmart,
                không gửi tới nhà cung cấp AI bên ngoài. Câu trả lời có thể chậm hơn.
              </span>
              <span className="mt-1 block text-xs text-muted">
                Khi dùng AI bên ngoài, hệ thống luôn ẩn họ tên, email, số điện thoại và chỉ gửi khoảng tuổi.
                Phân tích ảnh món ăn cần gửi ảnh tới AI bên ngoài nên sẽ tạm khóa khi bật mục này.
              </span>
            </span>
          </label>
          <p className="mt-4 border-t border-rule-2 pt-3 text-xs text-muted">
            {termsConsent
              ? `Bạn đã đồng ý Chính sách quyền riêng tư phiên bản ${termsConsent.version} ngày ${new Date(termsConsent.created_at).toLocaleDateString('vi-VN')}. `
              : 'Chưa có bản ghi đồng ý (tài khoản tạo trước khi có bước đồng ý). '}
            <Link to="/privacy" className="font-medium text-accent-strong underline underline-offset-2">Xem chính sách</Link>
          </p>
        </section>

        {err && <Alert tone="danger">{err}</Alert>}

        <div className="sticky bottom-3 z-10 flex justify-end gap-3 rounded-md border border-rule-2 bg-paper-2 p-3 shadow-card">
          <Btn type="button" variant="subtle" className="min-w-24 text-base" onClick={() => requestLeave(-1)}>
            Huỷ
          </Btn>
          <Btn type="submit" variant="primary" className="text-base" disabled={saving || !fullNameValid || !birthDateValid || !metricsValid}>
            {savedRecently ? <Check size={16} /> : <Save size={16} />}
            {saving ? 'Đang lưu…' : savedRecently ? 'Đã lưu' : 'Lưu thay đổi'}
          </Btn>
        </div>
      </form>

      <Toast toast={toast} position="top" />

      <Modal open={pendingTarget !== null} onClose={() => setPendingTarget(null)}
        icon={<AlertTriangle size={18} />} tone="warning" title="Bạn chưa lưu thay đổi"
        footer={<>
          <Btn variant="ghost" onClick={() => setPendingTarget(null)} disabled={saving}>Ở lại</Btn>
          <Btn variant="danger-subtle" onClick={discardAndLeave} disabled={saving}>Bỏ thay đổi</Btn>
          <Btn variant="primary" onClick={saveAndLeave} disabled={saving || !fullNameValid || !birthDateValid || !metricsValid}>
            {saving ? 'Đang lưu…' : 'Lưu và rời đi'}
          </Btn>
        </>}>
        <p className="text-sm text-ink-2">Bạn đang chỉnh sửa hồ sơ. Nếu rời trang bây giờ, các thay đổi chưa lưu sẽ bị mất.</p>
      </Modal>
    </div>
  );
}

// ── Helper components ──────────────────────────────────────────

function FieldGroup({ label, hint, children }) {
  return (
    <div>
      <label className="mb-1 block text-base font-medium text-ink-2">{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}
