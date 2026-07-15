import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

const ROLES = ['USER', 'EXPERT', 'ADMIN'];

export default function AdminUsers() {
    const [users, setUsers] = useState([]);
    const [q, setQ] = useState('');
    const [err, setErr] = useState(null);

    const load = () => api.adminUsers(q).then(setUsers).catch((e) => setErr(e.message));
    useEffect(() => { load(); }, []);

    async function changeRole(id, role) {
        await api.updateUserRole(id, role);
        load();
    }

    async function remove(id) {
        if (!confirm('Xóa người dùng này?')) return;
        await api.deleteUser(id);
        load();
    }

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold">Quản lý người dùng</h1>

            <div className="flex gap-2">
                <input
                    value={q} onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && load()}
                    placeholder="Tìm theo email…"
                    className="w-64 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                />
                <button onClick={load} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white">
                    Tìm
                </button>
            </div>

            {err && <p className="text-sm text-amber-600">{err}</p>}

            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                        <tr>
                            <th className="px-4 py-3">Email</th>
                            <th className="px-4 py-3">Họ tên</th>
                            <th className="px-4 py-3">Vai trò</th>
                            <th className="px-4 py-3"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((u) => (
                            <tr key={u.id} className="border-t border-slate-100">
                                <td className="px-4 py-3">{u.email}</td>
                                <td className="px-4 py-3">{u.full_name || '—'}</td>
                                <td className="px-4 py-3">
                                    <select
                                        value={u.role}
                                        onChange={(e) => changeRole(u.id, e.target.value)}
                                        className="rounded border border-slate-300 px-2 py-1"
                                    >
                                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                                    </select>
                                </td>
                                <td className="px-4 py-3 text-right">
                                    <button onClick={() => remove(u.id)} className="text-sm text-red-600 hover:underline">
                                        Xóa
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}