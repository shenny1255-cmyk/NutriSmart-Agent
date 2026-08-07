import { useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, FolderTree, Pill, Check, X } from 'lucide-react';
import { api } from '../lib/api.js';
import { categoryNameError } from '../lib/validation.js';
import { TableShell, THead, Tr, Td, Btn, Field, EmptyRow, Card, Modal, Toast, useToast } from '../components/ui.jsx';

export default function AdminCategories() {
    const { toast, show } = useToast();
    return (
        <div className="space-y-8">
            <h1 className="font-display text-2xl font-bold tracking-tight">Danh mục</h1>

            <BangDanhMuc
                icon={FolderTree}
                tieuDe="Danh mục tài liệu"
                moTa="Dùng để phân loại tài liệu tri thức trước khi đưa vào RAG."
                cot="Số tài liệu"
                demKey="so_tai_lieu"
                coSlug
                tai={api.docCategories}
                them={api.createDocCategory}
                sua={api.updateDocCategory}
                xoa={api.deleteDocCategory}
                show={show}
            />

            <Toast toast={toast} position="top" />
        </div>
    );
}

function BangDanhMuc({ icon: Icon, tieuDe, moTa, cot, demKey, coSlug, tai, them, sua, xoa, show }) {
    const [items, setItems] = useState([]);
    const [ten, setTen] = useState('');
    const [daChamTen, setDaChamTen] = useState(false);
    const [dangSua, setDangSua] = useState(null);     // id đang sửa inline
    const [tenSua, setTenSua] = useState('');
    const [xoaTarget, setXoaTarget] = useState(null);
    const [busy, setBusy] = useState(false);
    const loiTen = categoryNameError(ten);
    const loiTenSua = categoryNameError(tenSua);

    const load = () => tai().then(setItems).catch(() => setItems([]));
    useEffect(() => { load(); }, []);

    async function themMoi() {
        const t = ten.trim();
        setDaChamTen(true);
        if (loiTen) return;
        setBusy(true);
        try {
            await them({ name: t });
            setTen('');
            setDaChamTen(false);
            show(`Đã thêm "${t}".`);
            load();
        } catch (e) {
            show(`Không thêm được: ${e.message}`, 'danger');
        } finally {
            setBusy(false);
        }
    }

    async function luuSua(id) {
        const t = tenSua.trim();
        if (loiTenSua) return;
        setBusy(true);
        try {
            await sua(id, { name: t });
            setDangSua(null);
            show('Đã cập nhật tên danh mục.');
            load();
        } catch (e) {
            show(`Không sửa được: ${e.message}`, 'danger');
        } finally {
            setBusy(false);
        }
    }

    async function xacNhanXoa() {
        setBusy(true);
        try {
            await xoa(xoaTarget.id);
            show(`Đã xóa "${xoaTarget.name}".`);
            setXoaTarget(null);
            load();
        } catch (e) {
            show(`Không xóa được: ${e.message}`, 'danger');
        } finally {
            setBusy(false);
        }
    }

    const dangDung = (xoaTarget?.[demKey] ?? 0) > 0;

    return (
        <section className="space-y-3">
            <div className="flex items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
                    <Icon size={17} strokeWidth={2.2} />
                </span>
                <div>
                    <h2 className="font-display font-semibold">{tieuDe}</h2>
                    <p className="text-sm text-muted">{moTa}</p>
                </div>
            </div>

            <Card className="flex flex-wrap items-start gap-2 p-4">
                <div className="min-w-0 flex-1">
                    <Field
                        value={ten} onChange={(e) => setTen(e.target.value)}
                        onBlur={() => setDaChamTen(true)}
                        onKeyDown={(e) => e.key === 'Enter' && themMoi()}
                        placeholder={`Tên ${tieuDe.toLowerCase()} mới`}
                        maxLength={100}
                        disabled={busy}
                        aria-invalid={daChamTen && !!loiTen}
                        className={`w-full ${daChamTen && loiTen ? 'outline outline-2 outline-danger' : ''}`}
                    />
                    <p className={`mt-1 min-h-4 text-xs ${daChamTen && loiTen ? 'text-danger' : 'text-muted'}`}>
                        {daChamTen && loiTen ? loiTen : 'Tên danh mục từ 2–100 ký tự và phải chứa chữ cái.'}
                    </p>
                </div>
                <Btn variant="primary" onClick={themMoi} disabled={!!loiTen || busy}>
                    <Plus size={15} />
                    Thêm
                </Btn>
            </Card>

            <TableShell>
                <THead cols={coSlug ? ['Tên', 'Đường dẫn (tự động)', cot, ''] : ['Tên', cot, '']} />
                <tbody>
                    {items.length === 0 && (
                        <EmptyRow colSpan={coSlug ? 4 : 3}>Chưa có danh mục nào.</EmptyRow>
                    )}
                    {items.map((c) => (
                        <Tr key={c.id}>
                            <Td className="font-medium text-ink">
                                {dangSua === c.id ? (
                                    <div>
                                      <div className="flex items-center gap-1">
                                        <Field
                                            value={tenSua} onChange={(e) => setTenSua(e.target.value)} maxLength={100}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') luuSua(c.id);
                                                if (e.key === 'Escape') setDangSua(null);
                                            }}
                                            autoFocus
                                            aria-invalid={!!loiTenSua}
                                            className={`w-48 ${loiTenSua ? 'outline outline-2 outline-danger' : ''}`}
                                        />
                                        <Btn variant="primary" size="sm" onClick={() => luuSua(c.id)} disabled={busy || !!loiTenSua} aria-label="Lưu">
                                            <Check size={13} />
                                        </Btn>
                                        <Btn variant="ghost" size="sm" onClick={() => setDangSua(null)} aria-label="Hủy">
                                            <X size={13} />
                                        </Btn>
                                      </div>
                                      {loiTenSua && <p className="mt-1 text-xs font-normal text-danger">{loiTenSua}</p>}
                                    </div>
                                ) : c.name}
                            </Td>
                            {coSlug && (
                                <Td className="font-mono text-xs text-muted [overflow-wrap:anywhere]">{c.slug}</Td>
                            )}
                            <Td className="text-ink-2 [font-variant-numeric:tabular-nums]">{c[demKey] ?? 0}</Td>
                            <Td className="text-right">
                                {dangSua !== c.id && (
                                    <div className="flex justify-end gap-1">
                                        <Btn
                                            variant="subtle" size="sm"
                                            disabled={busy}
                                            onClick={() => { setDangSua(c.id); setTenSua(c.name); }}
                                        >
                                            <Pencil size={13} />
                                            Sửa
                                        </Btn>
                                        <Btn variant="danger-subtle" size="sm" disabled={busy} onClick={() => setXoaTarget(c)}>
                                            <Trash2 size={13} />
                                            Xóa
                                        </Btn>
                                    </div>
                                )}
                            </Td>
                        </Tr>
                    ))}
                </tbody>
            </TableShell>

            <Modal
                open={!!xoaTarget}
                onClose={() => !busy && setXoaTarget(null)}
                icon={<Trash2 size={18} />}
                tone="danger"
                title="Xóa danh mục?"
                footer={
                    <>
                        <Btn variant="ghost" onClick={() => setXoaTarget(null)} disabled={busy}>Hủy bỏ</Btn>
                        <Btn variant="danger" onClick={xacNhanXoa} disabled={busy}>
                            {busy ? 'Đang xóa…' : 'Xóa'}
                        </Btn>
                    </>
                }
            >
                Danh mục <b className="text-ink">{xoaTarget?.name}</b> sẽ bị xóa.
                {dangDung ? (
                    <> {xoaTarget[demKey]} mục đang thuộc danh mục này <b>vẫn được giữ nguyên</b>, chỉ bị bỏ trống phần phân loại.</>
                ) : (
                    <> Danh mục này chưa có mục nào bên trong.</>
                )}
            </Modal>
        </section>
    );
}
