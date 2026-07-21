import { useEffect, useState } from 'react';
import { RotateCcw, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api.js';

export default function ExpertReview() {
    const [docs, setDocs] = useState([]);
    const [err, setErr] = useState(null);
    const [crawlUrl, setCrawlUrl] = useState('');
    const [crawling, setCrawling] = useState(false);
    const [msg, setMsg] = useState(null);
    const [showResetModal, setShowResetModal] = useState(false);

    const load = () => api.pendingDocs().then(setDocs).catch((e) => setErr(e.message));
    useEffect(() => { load(); }, []);

    async function review(id, status) {
        await api.reviewDoc(id, status);
        load();
    }

    async function handleCrawl(e) {
        e.preventDefault();
        if (!crawlUrl.trim()) return;
        setCrawling(true);
        setErr(null);
        setMsg(null);
        try {
            const res = await api.crawlDocs([crawlUrl.trim()]);
            if (res.inserted > 0) {
                setMsg(`Đã cào thành công ${res.inserted} tài liệu mới!`);
                setCrawlUrl('');
                load();
            } else if (res.skipped > 0) {
                setMsg('Đường link này đã tồn tại trong hệ thống.');
            } else if (res.errors?.length > 0) {
                setErr(`Lỗi cào dữ liệu: ${res.errors[0].error}`);
            }
        } catch (e) {
            setErr(`Không thể cào dữ liệu: ${e.message}`);
        } finally {
            setCrawling(false);
        }
    }

    async function handlePresetCrawl(source) {
        setCrawling(true);
        setErr(null);
        setMsg(null);
        try {
            const res = await api.crawlPresetDocs(source, 10);
            if (res.inserted > 0) {
                setMsg(`Đã cào tự động thành công ${res.inserted} tài liệu mới từ ${source.toUpperCase()}!`);
                load();
            } else if (res.skipped > 0) {
                setMsg(`Các bài viết từ nguồn ${source.toUpperCase()} đã tồn tại trong danh sách.`);
            } else if (res.errors?.length > 0) {
                setErr(`Lỗi cào dữ liệu: ${res.errors[0].error}`);
            }
        } catch (e) {
            setErr(`Không thể cào tự động: ${e.message}`);
        } finally {
            setCrawling(false);
        }
    }

    async function confirmResetDocs() {
        setShowResetModal(false);
        setErr(null);
        setMsg(null);
        try {
            const res = await api.resetDocs();
            setMsg(res.message);
            load();
        } catch (e) {
            setErr(`Không thể reset: ${e.message}`);
        }
    }

    return (
        <div className="space-y-6 relative">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Duyệt tài liệu y–dược</h1>
                    <p className="text-sm text-slate-500">
                        Tài liệu được duyệt sẽ đưa vào kho tri thức (RAG). Từ chối nếu nội dung sai lệch.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => setShowResetModal(true)}
                    className="flex items-center gap-1.5 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700 hover:bg-rose-100 transition shadow-sm"
                >
                    <RotateCcw size={14} />
                    Reset danh sách để Demo
                </button>
            </div>

            {/* Nút cào tự động từ nguồn uy tín chọn sẵn */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
                <label className="block text-sm font-medium text-slate-700">⚡ Cào tự động theo nguồn y tế uy tín:</label>
                <div className="flex flex-wrap gap-2">
                    <button
                        type="button"
                        disabled={crawling}
                        onClick={() => handlePresetCrawl('moh')}
                        className="rounded-lg bg-emerald-50 border border-emerald-300 px-3 py-2 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                    >
                        🏥 Cào 5 bài từ Bộ Y tế (moh.gov.vn)
                    </button>
                    <button
                        type="button"
                        disabled={crawling}
                        onClick={() => handlePresetCrawl('who')}
                        className="rounded-lg bg-blue-50 border border-blue-300 px-3 py-2 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                    >
                        🌐 Cào 5 bài từ WHO (who.int)
                    </button>
                    <button
                        type="button"
                        disabled={crawling}
                        onClick={() => handlePresetCrawl('all')}
                        className="rounded-lg bg-purple-50 border border-purple-300 px-3 py-2 text-xs font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-50"
                    >
                        🚀 Cào tất cả nguồn uy tín (10 bài)
                    </button>
                </div>
            </div>

            {/* Form cào bài viết mới từ URL thủ công */}
            <form onSubmit={handleCrawl} className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
                <label className="block text-sm font-medium text-slate-700">Cào thủ công từ URL bất kỳ:</label>
                <div className="flex gap-2">
                    <input
                        type="url"
                        required
                        placeholder="Nhập đường link bài viết (vd: https://moh.gov.vn/...)"
                        value={crawlUrl}
                        onChange={(e) => setCrawlUrl(e.target.value)}
                        className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500"
                    />
                    <button
                        type="submit"
                        disabled={crawling}
                        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                        {crawling ? 'Đang cào…' : 'Cào bài viết'}
                    </button>
                </div>
                {msg && <p className="text-xs text-emerald-600 font-medium">{msg}</p>}
            </form>

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

            {/* Custom Modal Confirmation */}
            {showResetModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl space-y-4">
                        <div className="flex items-center gap-3 text-rose-600">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-rose-100">
                                <AlertTriangle size={20} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900">Xác nhận Reset Dữ liệu Demo</h3>
                        </div>

                        <p className="text-sm leading-relaxed text-slate-600">
                            Hành động này sẽ xóa toàn bộ bài viết và các đoạn vector đã lưu trong cơ sở dữ liệu để bạn sẵn sàng demo cào & duyệt lại từ đầu.
                        </p>

                        <div className="flex justify-end gap-3 pt-2">
                            <button
                                type="button"
                                onClick={() => setShowResetModal(false)}
                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
                            >
                                Hủy bỏ
                            </button>
                            <button
                                type="button"
                                onClick={confirmResetDocs}
                                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 shadow-sm"
                            >
                                Xác nhận Reset
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}