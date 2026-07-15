import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function AdminDrugs() {
    const [drugs, setDrugs] = useState([]);
    const [form, setForm] = useState({ name: '', active_ingredient: '' });

    const load = () => api.adminDrugs().then(setDrugs).catch(() => { });
    useEffect(() => { load(); }, []);

    async function addDrug() {
        if (!form.name) return;
        await api.createDrug(form);
        setForm({ name: '', active_ingredient: '' });
        load();
    }

    async function setRule(drugId) {
        const country = prompt('Mã quốc gia (VN/US/JP):', 'VN');
        if (!country) return;
        const status = prompt('Trạng thái (ALLOWED/RESTRICTED/BANNED):', 'BANNED');
        if (!status) return;
        await api.setDrugRule(drugId, { country_code: country, status });
        alert('Đã cập nhật quy định.');
    }

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold">Quản lý thuốc</h1>

            <div className="flex gap-2 rounded-xl border border-slate-200 bg-white p-4">
                <input
                    value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Tên thuốc"
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                <input
                    value={form.active_ingredient} onChange={(e) => setForm({ ...form, active_ingredient: e.target.value })}
                    placeholder="Hoạt chất"
                    className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                <button onClick={addDrug} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm text-white">
                    Thêm
                </button>
            </div>

            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
                <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
                        <tr>
                            <th className="px-4 py-3">Tên</th>
                            <th className="px-4 py-3">Hoạt chất</th>
                            <th className="px-4 py-3"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {drugs.map((d) => (
                            <tr key={d.id} className="border-t border-slate-100">
                                <td className="px-4 py-3">{d.name}</td>
                                <td className="px-4 py-3">{d.active_ingredient || '—'}</td>
                                <td className="px-4 py-3 text-right">
                                    <button onClick={() => setRule(d.id)} className="text-sm text-emerald-700 hover:underline">
                                        Đặt quy định quốc gia
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