import { useEffect, useState } from 'react';
import { RotateCcw, AlertTriangle, Building2, Globe, Zap, Link2, Check, X, Upload } from 'lucide-react';
import { api } from '../lib/api.js';
import { Btn, Field, Select, Alert, Card, Modal } from '../components/ui.jsx';

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
        <div className="relative space-y-6">
            <header className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h1 className="font-display text-2xl font-bold tracking-tight">Duyệt tài liệu y–dược</h1>
                    <p className="text-sm text-muted">
                        Tài liệu được duyệt sẽ đưa vào kho tri thức (RAG). Từ chối nếu nội dung sai lệch.
                    </p>
                </div>
                <Btn variant="danger-subtle" size="sm" onClick={() => setShowResetModal(true)}>
                    <RotateCcw size={13} />
                    Reset danh sách để Demo
                </Btn>
            </header>

            {/* Cào tự động từ nguồn chọn sẵn */}
            <Card className="space-y-3 p-4">
                <p className="flex items-center gap-1.5 text-sm font-medium text-ink-2">
                    <Zap size={15} className="text-accent-strong" />
                    Cào tự động theo nguồn y tế uy tín
                </p>
                <div className="flex flex-wrap gap-2">
                    <Btn variant="subtle" size="sm" disabled={crawling} onClick={() => handlePresetCrawl('moh')}>
                        <Building2 size={13} />
                        6 bài từ Sức khỏe & Đời sống (Bộ Y tế)
                    </Btn>
                    <Btn variant="subtle" size="sm" disabled={crawling} onClick={() => handlePresetCrawl('vinmec')}>
                        <Globe size={13} />
                        4 bài từ Vinmec
                    </Btn>
                    <Btn variant="primary" size="sm" disabled={crawling} onClick={() => handlePresetCrawl('all')}>
                        <Zap size={13} />
                        Cào tất cả nguồn uy tín (10 bài)
                    </Btn>
                </div>
            </Card>

            {/* Cào thủ công từ URL */}
            <Card className="space-y-2 p-4">
                <label htmlFor="crawl-url" className="flex items-center gap-1.5 text-sm font-medium text-ink-2">
                    <Link2 size={15} className="text-accent-strong" />
                    Cào thủ công từ URL bất kỳ
                </label>
                <form onSubmit={handleCrawl} className="flex flex-wrap gap-2">
                    <Field
                        id="crawl-url"
                        type="url"
                        required
                        placeholder="Nhập đường link bài viết (vd: https://moh.gov.vn/...)"
                        value={crawlUrl}
                        onChange={(e) => setCrawlUrl(e.target.value)}
                        className="w-full flex-1 sm:w-auto"
                    />
                    <Btn type="submit" variant="primary" disabled={crawling}>
                        {crawling ? 'Đang cào…' : 'Cào bài viết'}
                    </Btn>
                </form>
                {msg && <Alert tone="success">{msg}</Alert>}
            </Card>

            {/* Tải tài liệu lên từ máy */}
            <UploadTaiLieu
                onDone={(m) => { setMsg(m); setErr(null); load(); }}
                onError={(m) => { setErr(m); setMsg(null); }}
            />

            {err && <Alert tone="warning">{err}</Alert>}
            {docs.length === 0 && !err && (
                <Card className="p-8 text-center text-sm text-muted">
                    Không có tài liệu nào đang chờ duyệt.
                </Card>
            )}

            {/* Danh sách chờ duyệt */}
            <div className="space-y-3">
                {docs.map((d) => (
                    <Card
                        key={d.id}
                        className="flex flex-wrap items-center justify-between gap-3 p-4 transition-[transform,box-shadow] duration-short ease-out hover:-translate-y-0.5 hover:shadow-card"
                    >
                        <div className="min-w-0">
                            <p className="font-medium text-ink [overflow-wrap:anywhere]">{d.title}</p>
                            <p className="mt-0.5 text-xs text-muted">
                                {d.source_name || 'Không rõ nguồn'}
                                {d.source_url && (
                                    <>
                                        {' · '}
                                        <a
                                            href={d.source_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="rounded-sm text-accent-strong underline decoration-accent/40 underline-offset-2 transition-colors duration-micro ease-out hover:decoration-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
                                        >
                                            nguồn
                                        </a>
                                    </>
                                )}
                            </p>
                        </div>
                        <div className="flex shrink-0 gap-2">
                            <Btn variant="primary" size="sm" onClick={() => review(d.id, 'APPROVED')}>
                                <Check size={13} />
                                Duyệt
                            </Btn>
                            <Btn variant="danger-subtle" size="sm" onClick={() => review(d.id, 'REJECTED')}>
                                <X size={13} />
                                Từ chối
                            </Btn>
                        </div>
                    </Card>
                ))}
            </div>

            <Modal
                open={showResetModal}
                onClose={() => setShowResetModal(false)}
                icon={<AlertTriangle size={20} />}
                tone="danger"
                title="Xác nhận Reset Dữ liệu Demo"
                footer={
                    <>
                        <Btn variant="ghost" onClick={() => setShowResetModal(false)}>
                            Hủy bỏ
                        </Btn>
                        <Btn variant="danger" onClick={confirmResetDocs}>
                            Xác nhận Reset
                        </Btn>
                    </>
                }
            >
                Hành động này sẽ xóa toàn bộ bài viết và các đoạn vector đã lưu trong cơ sở dữ liệu để bạn sẵn sàng demo cào & duyệt lại từ đầu.
            </Modal>
        </div>
    );
}

function UploadTaiLieu({ onDone, onError }) {
    const [title, setTitle] = useState('');
    const [categoryId, setCategoryId] = useState('');
    const [rawText, setRawText] = useState('');
    const [file, setFile] = useState(null);
    const [cats, setCats] = useState([]);
    const [dangTai, setDangTai] = useState(false);

    useEffect(() => { api.docCategories().then(setCats).catch(() => setCats([])); }, []);

    async function submit(e) {
        e.preventDefault();
        setDangTai(true);
        try {
            const doc = await api.uploadDoc({
                title: title.trim(),
                category_id: categoryId || undefined,
                raw_text: rawText.trim() || undefined,
                file: file || undefined,
            });
            setTitle(''); setRawText(''); setFile(null); setCategoryId('');
            e.target.reset();
            onDone(`Đã tải lên "${doc.title}". Tài liệu đang chờ duyệt.`);
        } catch (err) {
            onError(`Không tải lên được: ${err.message}`);
        } finally {
            setDangTai(false);
        }
    }

    return (
        <Card className="space-y-3 p-4">
            <p className="flex items-center gap-1.5 text-sm font-medium text-ink-2">
                <Upload size={15} className="text-accent-strong" />
                Tải tài liệu lên từ máy
            </p>
            <form onSubmit={submit} className="space-y-3">
                <div className="flex flex-wrap gap-2">
                    <Field
                        required
                        placeholder="Tiêu đề tài liệu"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        className="w-full flex-1 sm:w-auto"
                    />
                    <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="w-full sm:w-52">
                        <option value="">— Chưa phân loại —</option>
                        {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </Select>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <input
                        type="file"
                        accept=".txt,.md,.pdf"
                        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                        className="min-h-11 flex-1 rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink-2 shadow-hairline file:mr-3 file:rounded-sm file:border-0 file:bg-accent-soft file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent-strong hover:file:bg-accent-soft/70"
                    />
                    <span className="text-xs text-muted">.txt · .md · .pdf (tối đa 10 MB)</span>
                </div>

                <textarea
                    rows={3}
                    placeholder="…hoặc dán thẳng nội dung tài liệu vào đây"
                    value={rawText}
                    onChange={(e) => setRawText(e.target.value)}
                    className="w-full rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline placeholder:text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
                />

                <div className="flex flex-wrap items-center gap-2">
                    <Btn type="submit" variant="primary" disabled={dangTai || !title.trim() || (!file && !rawText.trim())}>
                        <Upload size={15} />
                        {dangTai ? 'Đang tải lên…' : 'Tải lên'}
                    </Btn>
                    <span className="text-xs text-muted">
                        Tài liệu vào trạng thái chờ duyệt; bấm Duyệt mới đưa vào kho tri thức.
                    </span>
                </div>
            </form>
        </Card>
    );
}