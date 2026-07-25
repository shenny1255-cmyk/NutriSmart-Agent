import { useEffect, useState } from 'react';
import { Plus, Globe, ShieldBan } from 'lucide-react';
import { api } from '../lib/api.js';
import { TableShell, THead, Tr, Td, Btn, Field, Select, EmptyRow, Card, Modal, Toast, useToast } from '../components/ui.jsx';

// Fallback khi backend catalog chưa chạy — cùng pattern với Register
const FALLBACK_COUNTRIES = [{ code: 'VN', name: 'Việt Nam' }, { code: 'US', name: 'Hoa Kỳ' }, { code: 'JP', name: 'Nhật Bản' }];

const RULE_STATUSES = [
    { value: 'ALLOWED', label: 'Cho phép', cls: 'bg-accent-strong text-accent-ink shadow-whisper', idle: 'hover:bg-accent-soft hover:text-accent-strong' },
    { value: 'RESTRICTED', label: 'Hạn chế', cls: 'bg-warning-strong text-paper-2 shadow-whisper', idle: 'hover:bg-warning-soft hover:text-warning-strong' },
    { value: 'BANNED', label: 'Cấm', cls: 'bg-danger text-paper-2 shadow-whisper', idle: 'hover:bg-danger-soft hover:text-danger' },
];

export default function AdminDrugs() {
    const [drugs, setDrugs] = useState([]);
    const [form, setForm] = useState({ name: '', active_ingredient: '' });
    const [countries, setCountries] = useState(FALLBACK_COUNTRIES);
    // Modal đặt quy định: null = đóng, ngược lại là thuốc đang chọn
    const [ruleTarget, setRuleTarget] = useState(null);
    const [ruleForm, setRuleForm] = useState({ country_code: 'VN', status: 'BANNED' });
    const [saving, setSaving] = useState(false);
    const { toast, show } = useToast();

    const load = () => api.adminDrugs().then(setDrugs).catch(() => { });
    useEffect(() => {
        load();
        api.countries().then(setCountries).catch(() => { });
    }, []);

    async function addDrug() {
        if (!form.name) return;
        await api.createDrug(form);
        setForm({ name: '', active_ingredient: '' });
        show(`Đã thêm thuốc "${form.name}".`);
        load();
    }

    function openRule(drug) {
        setRuleForm({ country_code: 'VN', status: 'BANNED' });
        setRuleTarget(drug);
    }

    async function saveRule() {
        setSaving(true);
        try {
            await api.setDrugRule(ruleTarget.id, ruleForm);
            const countryName = countries.find((c) => c.code === ruleForm.country_code)?.name ?? ruleForm.country_code;
            const statusLabel = RULE_STATUSES.find((s) => s.value === ruleForm.status)?.label ?? ruleForm.status;
            show(`Đã đặt "${ruleTarget.name}" thành ${statusLabel} tại ${countryName}.`);
            setRuleTarget(null);
        } catch (e) {
            show(`Không cập nhật được quy định: ${e.message}`, 'danger');
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-6">
            <h1 className="font-display text-2xl font-bold tracking-tight">Quản lý thuốc</h1>

            <Card className="flex flex-wrap gap-2 p-4">
                <Field
                    value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Tên thuốc"
                    className="w-full flex-1 sm:w-auto"
                />
                <Field
                    value={form.active_ingredient} onChange={(e) => setForm({ ...form, active_ingredient: e.target.value })}
                    placeholder="Hoạt chất"
                    className="w-full flex-1 sm:w-auto"
                />
                <Btn variant="primary" onClick={addDrug} disabled={!form.name}>
                    <Plus size={15} />
                    Thêm
                </Btn>
            </Card>

            <TableShell>
                <THead cols={['Tên', 'Hoạt chất', '']} />
                <tbody>
                    {drugs.length === 0 && <EmptyRow colSpan={3}>Chưa có thuốc nào trong danh mục.</EmptyRow>}
                    {drugs.map((d) => (
                        <Tr key={d.id}>
                            <Td className="font-medium text-ink">{d.name}</Td>
                            <Td className="text-ink-2">{d.active_ingredient || '—'}</Td>
                            <Td className="text-right">
                                <Btn variant="subtle" size="sm" onClick={() => openRule(d)}>
                                    <Globe size={13} />
                                    Đặt quy định quốc gia
                                </Btn>
                            </Td>
                        </Tr>
                    ))}
                </tbody>
            </TableShell>

            {/* Modal đặt quy định — dropdown quốc gia từ catalog + chọn trạng thái đóng khung, hết gõ tay */}
            <Modal
                open={!!ruleTarget}
                onClose={() => !saving && setRuleTarget(null)}
                icon={<ShieldBan size={20} />}
                tone="accent"
                title={`Quy định cho "${ruleTarget?.name ?? ''}"`}
                footer={
                    <>
                        <Btn variant="ghost" onClick={() => setRuleTarget(null)} disabled={saving}>
                            Hủy bỏ
                        </Btn>
                        <Btn variant="primary" onClick={saveRule} disabled={saving}>
                            {saving ? 'Đang lưu…' : 'Lưu quy định'}
                        </Btn>
                    </>
                }
            >
                <div className="space-y-4">
                    <div>
                        <label htmlFor="rule-country" className="mb-1 block text-sm font-medium text-ink-2">Quốc gia</label>
                        <Select
                            id="rule-country"
                            value={ruleForm.country_code}
                            onChange={(e) => setRuleForm((f) => ({ ...f, country_code: e.target.value }))}
                            className="w-full"
                        >
                            {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                        </Select>
                    </div>

                    <div>
                        <p className="mb-1 text-sm font-medium text-ink-2">Trạng thái</p>
                        <div role="radiogroup" aria-label="Trạng thái quy định" className="grid grid-cols-3 gap-2">
                            {RULE_STATUSES.map((s) => {
                                const on = ruleForm.status === s.value;
                                return (
                                    <button
                                        key={s.value}
                                        type="button"
                                        role="radio"
                                        aria-checked={on}
                                        onClick={() => setRuleForm((f) => ({ ...f, status: s.value }))}
                                        className={[
                                            'min-h-11 rounded-sm px-2 py-2 text-sm font-medium',
                                            'transition-[background-color,color,box-shadow,transform] duration-short ease-out active:scale-[0.97]',
                                            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
                                            on ? s.cls : `bg-paper-3 text-ink-2 ${s.idle}`,
                                        ].join(' ')}
                                    >
                                        {s.label}
                                    </button>
                                );
                            })}
                        </div>
                        <p className="mt-1 text-xs text-muted">
                            Quy định dùng để cảnh báo người dùng tại quốc gia tương ứng.
                        </p>
                    </div>
                </div>
            </Modal>

            <Toast toast={toast} />
        </div>
    );
}