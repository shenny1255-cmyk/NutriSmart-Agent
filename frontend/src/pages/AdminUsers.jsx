import { useEffect, useState } from 'react';
import { Search, Trash2, UserPlus } from 'lucide-react';
import { api } from '../lib/api.js';
import { TableShell, THead, Tr, Td, Btn, Field, Select, Alert, EmptyRow, Modal, Toast, useToast } from '../components/ui.jsx';
import PasswordInput from '../components/PasswordInput.jsx';
import { isValidFullName } from '../lib/validation.js';

const ROLES = ['USER', 'EXPERT', 'ADMIN'];
const GMAIL_USERNAME_PATTERN = /^[a-zA-Z0-9](?:[a-zA-Z0-9._]{0,62}[a-zA-Z0-9])?$/;
const PASSWORD_FIELD_CLASS = [
    'mt-1 min-h-11 w-full rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline',
    'transition-[background-color,box-shadow] duration-short ease-out hover:bg-paper-3 focus:bg-paper-2',
    'focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus',
].join(' ');

export default function AdminUsers() {
    const [users, setUsers] = useState([]);
    const [q, setQ] = useState('');
    const [err, setErr] = useState(null);
    // Modal xóa: null = đóng, ngược lại là user đang chọn
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
    const [currentUserId, setCurrentUserId] = useState(null);
    const [createOpen, setCreateOpen] = useState(false);
    const [creating, setCreating] = useState(false);
    const [confirmAdmin, setConfirmAdmin] = useState(false);
    const [createForm, setCreateForm] = useState({ full_name: '', email: '', password: '', confirm: '', role: 'USER' });
    const [deleting, setDeleting] = useState(false);
    const { toast, show } = useToast();

    // tuKiemTra = true khi người dùng bấm Tìm/Enter → không có kết quả thì báo đỏ.
    // Các lần load lại sau khi đổi vai trò/xóa thì im lặng, khỏi đè toast xác nhận.
    const load = async ({ tuKiemTra = false } = {}) => {
        const tuKhoa = q.trim();
        try {
            const rows = await api.adminUsers(tuKhoa);
            setUsers(rows);
            setSelectedIds(new Set());
            setErr(null);
            if (tuKiemTra && tuKhoa && rows.length === 0) {
                show(`Không tìm thấy người dùng nào khớp "${tuKhoa}".`, 'danger');
            }
        } catch (e) {
            setErr(e.message);
        }
    };
    useEffect(() => {
        load();
        api.me().then((me) => setCurrentUserId(me.id)).catch(() => {});
    }, []);

    const selectableIds = users.filter((u) => u.id !== currentUserId).map((u) => u.id);
    const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selectedIds.has(id));

    function toggleSelected(id) {
        setSelectedIds((current) => {
            const next = new Set(current);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    }

    function toggleAll() {
        setSelectedIds(allSelected ? new Set() : new Set(selectableIds));
    }

    async function changeRole(id, role) {
        try {
            await api.updateUserRole(id, role);
            show(`Đã đổi vai trò thành ${role}.`);
            load();
        } catch (e) {
            show(`Không đổi được vai trò: ${e.message}`, 'danger');
            load();
        }
    }

    async function confirmDelete() {
        setDeleting(true);
        try {
            await api.deleteUser(deleteTarget.id);
            show(`Đã xóa tài khoản ${deleteTarget.full_name || deleteTarget.email}.`);
            setDeleteTarget(null);
            load();
        } catch (e) {
            show(`Không xóa được: ${e.message}`, 'danger');
        } finally {
            setDeleting(false);
        }
    }

    async function confirmBulkDelete() {
        setDeleting(true);
        try {
            const result = await api.bulkDeleteUsers([...selectedIds]);
            show(`Đã xóa ${result.deleted_count} tài khoản.`);
            setBulkDeleteOpen(false);
            setSelectedIds(new Set());
            load();
        } catch (e) {
            show(`Không xóa được: ${e.message}`, 'danger');
        } finally {
            setDeleting(false);
        }
    }

    const createValid = isValidFullName(createForm.full_name)
        && GMAIL_USERNAME_PATTERN.test(createForm.email.trim())
        && createForm.password.length >= 8
        && createForm.password.length <= 128
        && createForm.password === createForm.confirm
        && (createForm.role !== 'ADMIN' || confirmAdmin);

    function resetCreateForm() {
        setCreateOpen(false);
        setConfirmAdmin(false);
        setCreateForm({ full_name: '', email: '', password: '', confirm: '', role: 'USER' });
    }

    function closeCreate() {
        if (!creating) resetCreateForm();
    }

    async function createUser() {
        if (!createValid) return;
        setCreating(true);
        try {
            await api.createAdminUser({
                full_name: createForm.full_name.trim(),
                email: `${createForm.email.trim()}@gmail.com`,
                password: createForm.password,
                role: createForm.role,
            });
            show(`Đã tạo tài khoản ${createForm.email.trim()}@gmail.com.`);
            resetCreateForm();
            load();
        } catch (e) {
            show(`Không tạo được tài khoản: ${e.message}`, 'danger');
        } finally {
            setCreating(false);
        }
    }

    return (
        <div className="space-y-6">
            <h1 className="font-display text-2xl font-bold tracking-tight">Quản lý người dùng</h1>

            <div>
                <Btn variant="primary" onClick={() => setCreateOpen(true)}>
                    <UserPlus size={16} />
                    Tạo người dùng
                </Btn>
            </div>

            <div className="flex flex-wrap gap-2">
                <Field
                    value={q} onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && load({ tuKiemTra: true })}
                    placeholder="Tìm theo tên hoặc email…"
                    className="w-full sm:w-72"
                />
                <Btn variant="primary" onClick={() => load({ tuKiemTra: true })}>
                    <Search size={15} />
                    Tìm
                </Btn>
                {selectedIds.size > 0 && (
                    <Btn variant="danger" onClick={() => setBulkDeleteOpen(true)}>
                        <Trash2 size={15} />
                        Xóa đã chọn ({selectedIds.size})
                    </Btn>
                )}
            </div>

            {err && <Alert tone="warning">{err}</Alert>}

            <TableShell>
                <THead cols={[
                    <input key="select-all" type="checkbox" checked={allSelected} onChange={toggleAll}
                        aria-label="Chọn tất cả người dùng đang hiển thị" className="h-4 w-4 accent-accent-strong" />,
                    'Họ tên', 'Email', 'Vai trò', '',
                ]} />
                <tbody>
                    {users.length === 0 && <EmptyRow colSpan={5}>Không tìm thấy người dùng nào.</EmptyRow>}
                    {users.map((u) => (
                        <Tr key={u.id}>
                            <Td className="w-0">
                                <input type="checkbox" checked={selectedIds.has(u.id)}
                                    onChange={() => toggleSelected(u.id)} disabled={u.id === currentUserId}
                                    aria-label={`Chọn tài khoản ${u.full_name || u.email}`}
                                    title={u.id === currentUserId ? 'Không thể tự xóa tài khoản đang đăng nhập' : undefined}
                                    className="h-4 w-4 accent-accent-strong disabled:cursor-not-allowed disabled:opacity-40" />
                            </Td>
                            <Td className="font-medium text-ink">{u.full_name || '—'}</Td>
                            <Td className="text-ink-2 [overflow-wrap:anywhere]">{u.email}</Td>
                            <Td>
                                <Select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)}
                                    disabled={u.id === currentUserId}
                                    title={u.id === currentUserId ? 'Không thể tự thay đổi vai trò của tài khoản đang đăng nhập' : undefined}>
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
                Tài khoản <b className="text-ink">{deleteTarget?.full_name || deleteTarget?.email}</b>
                {deleteTarget?.full_name && <> (<span className="[overflow-wrap:anywhere]">{deleteTarget.email}</span>)</>} sẽ bị xóa vĩnh viễn cùng toàn bộ hồ sơ sức khỏe. Hành động này không hoàn tác được.
            </Modal>

            <Modal
                open={bulkDeleteOpen}
                onClose={() => !deleting && setBulkDeleteOpen(false)}
                icon={<Trash2 size={18} />}
                tone="danger"
                title={`Xóa ${selectedIds.size} người dùng?`}
                footer={
                    <>
                        <Btn variant="ghost" onClick={() => setBulkDeleteOpen(false)} disabled={deleting}>Hủy bỏ</Btn>
                        <Btn variant="danger" onClick={confirmBulkDelete} disabled={deleting || selectedIds.size === 0}>
                            {deleting ? 'Đang xóa…' : `Xóa vĩnh viễn ${selectedIds.size} tài khoản`}
                        </Btn>
                    </>
                }
            >
                Toàn bộ hồ sơ sức khỏe và dữ liệu liên quan của các tài khoản đã chọn sẽ bị xóa vĩnh viễn. Hành động này không hoàn tác được.
            </Modal>

            <Modal
                open={createOpen}
                onClose={closeCreate}
                icon={<UserPlus size={18} />}
                title="Tạo người dùng"
                footer={
                    <>
                        <Btn variant="ghost" onClick={closeCreate} disabled={creating}>Hủy bỏ</Btn>
                        <Btn variant="primary" onClick={createUser} disabled={!createValid || creating}>
                            {creating ? 'Đang tạo…' : 'Tạo tài khoản'}
                        </Btn>
                    </>
                }
            >
                <div className="space-y-4">
                    <label className="block text-sm font-medium text-ink-2">
                        Họ và tên
                        <Field value={createForm.full_name} maxLength={100}
                            autoComplete="off"
                            onChange={(e) => setCreateForm((f) => ({ ...f, full_name: e.target.value }))}
                            aria-invalid={createForm.full_name !== '' && !isValidFullName(createForm.full_name)}
                            className={`mt-1 w-full ${createForm.full_name !== '' && !isValidFullName(createForm.full_name) ? 'outline outline-2 outline-danger' : ''}`}
                            placeholder="Nguyễn Văn An" />
                        {createForm.full_name !== '' && !isValidFullName(createForm.full_name) && (
                            <span className="mt-1 block text-xs font-medium text-danger">
                                Nhập 2–100 ký tự; không dùng emoji hoặc ký tự đặc biệt.
                            </span>
                        )}
                    </label>
                    <label className="block text-sm font-medium text-ink-2">
                        Email
                        <div className={`mt-1 flex min-h-11 overflow-hidden rounded-sm bg-paper-2 shadow-hairline ${createForm.email !== '' && !GMAIL_USERNAME_PATTERN.test(createForm.email.trim()) ? 'outline outline-2 outline-danger' : ''}`}>
                            <input value={createForm.email} autoComplete="off" maxLength={64}
                                onChange={(e) => setCreateForm((f) => ({ ...f, email: e.target.value }))}
                                aria-invalid={createForm.email !== '' && !GMAIL_USERNAME_PATTERN.test(createForm.email.trim())}
                                className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-ink focus-visible:outline-none"
                                placeholder="ten.nguoidung" />
                            <span className="flex items-center border-l border-rule-2 bg-paper-3 px-3 text-sm text-ink-2">@gmail.com</span>
                        </div>
                        {createForm.email !== '' && !GMAIL_USERNAME_PATTERN.test(createForm.email.trim()) && (
                            <span className="mt-1 block text-xs font-medium text-danger">
                                Chỉ nhập phần tên Gmail bằng chữ, số, dấu chấm hoặc gạch dưới.
                            </span>
                        )}
                    </label>
                    <label className="block text-sm font-medium text-ink-2">
                        Mật khẩu
                        <PasswordInput value={createForm.password}
                            autoComplete="new-password"
                            maxLength={128}
                            onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                            aria-invalid={createForm.password !== '' && createForm.password.length < 8}
                            className={`${PASSWORD_FIELD_CLASS} ${createForm.password !== '' && createForm.password.length < 8 ? 'outline outline-2 outline-danger' : ''}`} />
                        <span className={`mt-1 block text-xs ${createForm.password !== '' && createForm.password.length < 8 ? 'font-medium text-danger' : 'text-muted'}`}>
                            Mật khẩu phải có ít nhất 8 ký tự.
                        </span>
                    </label>
                    <label className="block text-sm font-medium text-ink-2">
                        Xác nhận mật khẩu
                        <PasswordInput value={createForm.confirm}
                            autoComplete="new-password"
                            maxLength={128}
                            onChange={(e) => setCreateForm((f) => ({ ...f, confirm: e.target.value }))}
                            aria-invalid={createForm.confirm !== '' && createForm.confirm !== createForm.password}
                            className={`${PASSWORD_FIELD_CLASS} ${createForm.confirm !== '' && createForm.confirm !== createForm.password ? 'outline outline-2 outline-danger' : ''}`} />
                        {createForm.confirm !== '' && createForm.confirm !== createForm.password && (
                            <span className="mt-1 block text-xs font-medium text-danger">Mật khẩu xác nhận không khớp.</span>
                        )}
                    </label>
                    <label className="block text-sm font-medium text-ink-2">
                        Vai trò
                        <Select value={createForm.role} onChange={(e) => {
                            setCreateForm((f) => ({ ...f, role: e.target.value }));
                            setConfirmAdmin(false);
                        }} className="mt-1 w-full">
                            {ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
                        </Select>
                    </label>
                    {createForm.role === 'ADMIN' && (
                        <label className="flex gap-2 rounded-sm bg-warning-soft p-3 text-sm text-warning-strong">
                            <input type="checkbox" checked={confirmAdmin} onChange={(e) => setConfirmAdmin(e.target.checked)}
                                className="mt-0.5 h-4 w-4 shrink-0 accent-warning-strong" />
                            Tôi xác nhận tài khoản này sẽ có toàn quyền quản trị hệ thống.
                        </label>
                    )}
                </div>
            </Modal>

            <Toast toast={toast} position="top" />
        </div>
    );
}
