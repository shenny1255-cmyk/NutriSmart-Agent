import { useEffect, useState } from 'react';
import { Plus, ShieldBan } from 'lucide-react';
import { api } from '../lib/api.js';
import { TableShell, THead, Tr, Td, Btn, Field, EmptyRow, Card, Modal, Toast, useToast } from '../components/ui.jsx';

const RULE_STATUSES = [
    { value: 'ALLOWED', label: 'Cho phép', cls: 'bg-accent-strong text-accent-ink shadow-whisper', idle: 'hover:bg-accent-soft hover:text-accent-strong' },
    { value: 'RESTRICTED', label: 'Hạn chế (Kê đơn)', cls: 'bg-warning-strong text-paper-2 shadow-whisper', idle: 'hover:bg-warning-soft hover:text-warning-strong' },
    { value: 'BANNED', label: 'Cấm lưu hành', cls: 'bg-danger text-paper-2 shadow-whisper', idle: 'hover:bg-danger-soft hover:text-danger' },
];

export default function AdminDrugs() {
    const [drugs, setDrugs] = useState([]);
    const [form, setForm] = useState({ name: '', active_ingredient: '', status: 'ALLOWED', status_note: '' });
    // Modal đặt quy định: null = đóng, ngược lại là thuốc đang chọn
    const [ruleTarget, setRuleTarget] = useState(null);
    const [ruleForm, setRuleForm] = useState({ status: 'BANNED', status_note: '' });
    const [saving, setSaving] = useState(false);
    const { toast, show } = useToast();

    const load = () => api.adminDrugs().then(setDrugs).catch(() => { });
    useEffect(() => { load(); }, []);

    async function addDrug() {
        if (!form.name) return;
        await api.createDrug(form);
        setForm({ name: '', active_ingredient: '', status: 'ALLOWED', status_note: '' });
        show(`Đã thêm thuốc "${form.name}".`);
        load();
    }

    function openRule(drug) {
        setRuleForm({ status: drug.status || 'ALLOWED', status_note: drug.status_note || '' });
        setRuleTarget(drug);
    }

    async function saveRule() {
        setSaving(true);
        try {
            await api.updateDrug(ruleTarget.id, ruleForm);
            const statusLabel = RULE_STATUSES.find((s) => s.value === ruleForm.status)?.label ?? ruleForm.status;
            show(`Đã đặt "${ruleTarget.name}" thành ${statusLabel}.`);
            setRuleTarget(null);
            load();
        } catch (e) {
            show(`Không cập nhật được quy định: ${e.message}`, 'danger');
        } finally {
            setSaving(false);
        }
    }

    return (
        <div className="space-y-6">
            <h1 className="font-display text-2xl font-bold tracking-tight">Quản lý danh mục thuốc</h1>

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
                <THead cols={['Tên thuốc', 'Hoạt chất', 'Trạng thái pháp lý', 'Ghi chú quy định', '']} />
                <tbody>
                    {drugs.length === 0 && <EmptyRow colSpan={5}>Chưa có thuốc nào trong danh mục.</EmptyRow>}
                    {drugs.map((d) => {
                        const statusObj = RULE_STATUSES.find((s) => s.value === d.status);
                        const badgeCls = d.status === 'BANNED' ? 'bg-danger text-paper-2' : d.status === 'RESTRICTED' ? 'bg-warning-strong text-paper-2' : 'bg-accent-strong text-accent-ink';
                        return (
                            <Tr key={d.id}>
                                <Td className="font-medium text-ink">{d.name}</Td>
                                <Td className="text-ink-2">{d.active_ingredient || '—'}</Td>
                                <Td>
                                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-xs font-semibold ${badgeCls}`}>
                                        {statusObj?.label ?? d.status}
                                    </span>
                                </Td>
                                <Td className="text-xs text-ink-2 max-w-xs truncate">{d.status_note || '—'}</Td>
                                <Td className="text-right">
                                    <Btn variant="subtle" size="sm" onClick={() => openRule(d)}>
                                        <ShieldBan size={13} />
                                        Sửa quy định
                                    </Btn>
                                </Td>
                            </Tr>
                        );
                    })}
                </tbody>
            </TableShell>

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
                        <p className="mb-1 text-sm font-medium text-ink-2">Trạng thái lưu hành tại Việt Nam</p>
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
                    </div>

                    <div>
                        <label htmlFor="rule-note" className="mb-1 block text-sm font-medium text-ink-2">Ghi chú quy định / căn cứ pháp lý</label>
                        <Field
                            id="rule-note"
                            value={ruleForm.status_note}
                            onChange={(e) => setRuleForm((f) => ({ ...f, status_note: e.target.value }))}
                            placeholder="Ví dụ: Bị cấm theo quyết định của Bộ Y tế..."
                            className="w-full"
                        />
                    </div>
                </div>
            </Modal>

            <Toast toast={toast} />
        </div>
    );
}