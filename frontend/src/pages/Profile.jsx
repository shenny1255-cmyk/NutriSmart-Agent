import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, Save, User } from 'lucide-react';
import { api } from '../lib/api.js';
import { Btn, Field as TextInput, Select, Alert, useToast, Toast } from '../components/ui.jsx';

// Danh sách fallback khi backend chưa chạy
const FALLBACK_COUNTRIES = [{ code: 'VN', name: 'Việt Nam' }, { code: 'US', name: 'Hoa Kỳ' }, { code: 'JP', name: 'Nhật Bản' }];
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

const ROLE_LABELS = { ADMIN: 'Quản trị viên', EXPERT: 'Chuyên gia', USER: 'Người dùng' };

export default function Profile() {
  const navigate = useNavigate();
  const { toast, show } = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  // Dữ liệu dropdown
  const [countries, setCountries] = useState(FALLBACK_COUNTRIES);
  const [conditions, setConditions] = useState(FALLBACK_CONDITIONS);
  const [allergens, setAllergens] = useState(FALLBACK_ALLERGENS);

  // Form state
  const [form, setForm] = useState({
    email: '', role: '', full_name: '', country_code: 'VN',
    gender: 'MALE', birth_date: '', height_cm: '', weight_kg: '',
    activity_level: 3, goal: 'MAINTAIN',
    condition_ids: [], allergen_ids: [],
    daily_calorie_target: null,
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const toggle = (key, id) =>
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(id) ? f[key].filter((x) => x !== id) : [...f[key], id],
    }));

  // Lấy thông tin người dùng hiện tại + dropdown khi mount
  useEffect(() => {
    Promise.all([
      api.me(),
      api.countries().catch(() => FALLBACK_COUNTRIES),
      api.conditions().catch(() => FALLBACK_CONDITIONS),
      api.allergens().catch(() => FALLBACK_ALLERGENS),
    ]).then(([me, ctrs, conds, alls]) => {
      setCountries(ctrs);
      setConditions(conds);
      setAllergens(alls);

      const p = me.profile;
      setForm({
        email: me.email || '',
        role: me.role || 'USER',
        full_name: me.full_name || '',
        country_code: me.country_code || 'VN',
        gender: p?.gender || 'MALE',
        birth_date: p?.birth_date || '',
        height_cm: p?.height_cm ?? '',
        weight_kg: p?.weight_kg ?? '',
        activity_level: p?.activity_level ?? 3,
        goal: p?.goal || 'MAINTAIN',
        condition_ids: (p?.conditions || []).map((c) => c.id),
        allergen_ids: (p?.allergens || []).map((a) => a.id),
        daily_calorie_target: p?.daily_calorie_target ?? null,
      });
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // BMI preview tính ngay trên client
  const bmi =
    form.height_cm && form.weight_kg
      ? (Number(form.weight_kg) / (Number(form.height_cm) / 100) ** 2).toFixed(1)
      : null;

  async function handleSave(e) {
    e.preventDefault();
    setErr(null);
    setSaving(true);
    try {
      const payload = {
        full_name: form.full_name,
        country_code: form.country_code,
        gender: form.gender,
        birth_date: form.birth_date || null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        activity_level: Number(form.activity_level),
        goal: form.goal,
        condition_ids: form.condition_ids,
        allergen_ids: form.allergen_ids,
      };
      const updated = await api.updateProfile(payload);

      // Cập nhật lại form với dữ liệu mới từ server (bao gồm calo mục tiêu đã tính lại)
      if (updated.profile) {
        setForm((f) => ({
          ...f,
          daily_calorie_target: updated.profile.daily_calorie_target,
        }));
      }
      show('Đã lưu thông tin thành công!', 'success');
    } catch (e) {
      if (e.status === 422) setErr('Thông tin chưa hợp lệ — vui lòng kiểm tra lại.');
      else setErr(typeof e.detail === 'string' ? e.detail : 'Lưu thất bại, thử lại sau.');
    } finally {
      setSaving(false);
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
          onClick={() => navigate(-1)}
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
                value={form.full_name}
                onChange={(e) => set('full_name', e.target.value)}
                className="w-full"
              />
            </FieldGroup>

            <FieldGroup label="Email" hint="Không thể thay đổi">
              <TextInput value={form.email} disabled className="w-full" />
            </FieldGroup>

            <FieldGroup label="Vai trò">
              <TextInput value={ROLE_LABELS[form.role] || form.role} disabled className="w-full" />
            </FieldGroup>

            <FieldGroup label="Quốc gia">
              <Select value={form.country_code} onChange={(e) => set('country_code', e.target.value)} className="w-full">
                {countries.map((c) => (
                  <option key={c.code} value={c.code}>{c.name}</option>
                ))}
              </Select>
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
                value={form.birth_date}
                onChange={(e) => set('birth_date', e.target.value)}
                className="w-full"
              />
            </FieldGroup>

            <FieldGroup label="Chiều cao (cm)">
              <TextInput
                type="number" min="50" max="250" step="0.1" required
                value={form.height_cm}
                onChange={(e) => set('height_cm', e.target.value)}
                className="w-full"
              />
            </FieldGroup>

            <FieldGroup label="Cân nặng (kg)">
              <TextInput
                type="number" min="20" max="300" step="0.1" required
                value={form.weight_kg}
                onChange={(e) => set('weight_kg', e.target.value)}
                className="w-full"
              />
            </FieldGroup>
          </div>

          {bmi && (
            <p className="mt-3 rounded-sm bg-accent-soft px-3 py-2 text-sm text-accent-strong">
              BMI dự kiến: <b className="[font-variant-numeric:tabular-nums]">{bmi}</b>
            </p>
          )}

          {form.daily_calorie_target && (
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
            <FieldGroup label="Bệnh nền" hint="Chọn nhiều nếu có">
              <CheckGroup items={conditions} selected={form.condition_ids} onToggle={(id) => toggle('condition_ids', id)} />
            </FieldGroup>

            <FieldGroup label="Dị ứng thực phẩm" hint="Chọn nhiều nếu có">
              <CheckGroup items={allergens} selected={form.allergen_ids} onToggle={(id) => toggle('allergen_ids', id)} />
            </FieldGroup>
          </div>
        </section>

        {err && <Alert tone="danger">{err}</Alert>}

        <div className="flex justify-end gap-3">
          <Btn type="button" variant="ghost" onClick={() => navigate(-1)}>
            Huỷ
          </Btn>
          <Btn type="submit" variant="primary" disabled={saving}>
            <Save size={16} />
            {saving ? 'Đang lưu…' : 'Lưu thay đổi'}
          </Btn>
        </div>
      </form>

      <Toast toast={toast} position="top" />
    </div>
  );
}

// ── Helper components ──────────────────────────────────────────

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
