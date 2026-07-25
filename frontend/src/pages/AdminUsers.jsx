import { useEffect, useState } from 'react';
import { Search, Trash2 } from 'lucide-react';
import { api } from '../lib/api.js';
import { TableShell, THead, Tr, Td, Btn, Field, Select, Alert, EmptyRow, Modal, Toast, useToast } from '../components/ui.jsx';

const ROLES = ['USER', 'EXPERT', 'ADMIN'];

export default function AdminUsers() {
    const [users, setUsers] = useState([]);
    const [q, setQ] = useState('');
    const [err, setErr] = useState(null);
    // Modal xóa: null = đóng, ngược lại là user đang chọn
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const { toast, show } = useToast();

    const load = () => api.adminUsers(q).then(setUsers).catch((e) => setErr(e.message));
    useEffect(() => { load(); }, []);

    async function changeRole(id, role) {
        await api.updateUserRole(id, role);
        show(`Đã đổi vai trò thành ${role}.`);
        load();
    }

    async function confirmDelete() {
        setDeleting(true);
        try {
            await api.deleteUser(deleteTarget.id);
            show(`Đã xóa tài khoản ${deleteTarget.email}.`);
            setDeleteTarget(null);
            load();
        } catch (e) {
            show(`Không xóa được: ${e.message}`, 'danger');
        } finally {
            setDeleting(false);
        }
    }

    return (
        <div className="space-y-6">
            <h1 className="font-display text-2xl font-bold tracking-tight">Quản lý người dùng</h1>

            <div className="flex flex-wrap gap-2">
                <Field
                    value={q} onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && load()}
                    placeholder="Tìm theo email…"
                    className="w-full sm:w-64"
                />
                <Btn variant="primary" onClick={load}>
                    <Search size={15} />
                    Tìm
                </Btn>
            </div>

            {err && <Alert tone="warning">{err}</Alert>}

            <TableShell>
                <THead cols={['Email', 'Họ tên', 'Vai trò', '']} />
                <tbody>
                    {users.length === 0 && <EmptyRow colSpan={4}>Không tìm thấy người dùng nào.</EmptyRow>}
                    {users.map((u) => (
                        <Tr key={u.id}>
                            <Td className="font-medium text-ink [overflow-wrap:anywhere]">{u.email}</Td>
                            <Td className="text-ink-2">{u.full_name || '—'}</Td>
                            <Td>
                                <Select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)}>
                                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                </Select>
                            </Td>
                            <Td className="text-right">
                                <Btn variant="danger-subtle" size="sm" onClick={() => setDeleteTarget(u)}>
                                    <Trash2 size={13} />
                                    Xóa
                                </Btn>
                            </Td>
                        </Tr>
                    ))}
                </tbody>
            </TableShell>

            {/* Modal xác nhận xóa — hiện rõ email để không xóa nhầm hàng */}
            <Modal
                open={!!deleteTarget}
                onClose={() => !deleting && setDeleteTarget(null)}
                icon={<Trash2 size={18} />}
                tone="danger"
                title="Xóa người dùng?"
                footer={
                    <>
                        <Btn variant="ghost" onClick={() => setDeleteTarget(null)} disabled={deleting}>
                            Hủy bỏ
                        </Btn>
                        <Btn variant="danger" onClick={confirmDelete} disabled={deleting}>
                            {deleting ? 'Đang xóa…' : 'Xóa vĩnh viễn'}
                        </Btn>
                    </>
                }
            >
                Tài khoản <b className="text-ink [overflow-wrap:anywhere]">{deleteTarget?.email}</b>
                {deleteTarget?.full_name && <> ({deleteTarget.full_name})</>} sẽ bị xóa vĩnh viễn cùng toàn bộ hồ sơ sức khỏe. Hành động này không hoàn tác được.
            </Modal>

            <Toast toast={toast} />
        </div>
    );
}