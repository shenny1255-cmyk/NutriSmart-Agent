import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';

export default function ExpertReview() {
    const [docs, setDocs] = useState([]);
    const [err, setErr] = useState(null);

    const load = () => api.pendingDocs().then(setDocs).catch((e) => setErr(e.message));
    useEffect(() => { load(); }, []);

    async function review(id, status) {
        await api.reviewDoc(id, status);
        load();
    }

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold">Duyệt tài liệu y–dược</h1>
            <p className="text-sm text-slate-500">
                Tài liệu được duyệt sẽ đưa vào kho tri thức (RAG). Từ chối nếu nội dung sai lệch.
            </p>

            {err && <p className="text-sm text-amber-600">{err}</p>}
            {docs.length === 0 && !err && (
                <p className="text-sm text-slate-400">Không có tài liệu nào đang chờ duyệt.</p>
            )}

            <div className="space-y-3">
                {docs.map((d) => (
                    <div key={d.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
                        <div>
                            <p className="font-medium">{d.title}</p>
                            <p className="text-xs text-slate-500">
                                {d.source_name || 'Không rõ nguồn'}
                                {d.source_url && (
                                    <> · <a href={d.source_url} target="_blank" rel="noreferrer" className="underline">nguồn</a></>
                                )}
                            </p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => review(d.id, 'APPROVED')}
                                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm text-white"
                            >
                                Duyệt
                            </button>
                            <button
                                onClick={() => review(d.id, 'REJECTED')}
                                className="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600"
                            >
                                Từ chối
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}