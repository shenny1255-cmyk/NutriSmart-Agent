import { useEffect, useState } from 'react';
import {
  RotateCcw, AlertTriangle, Check, X, Upload, Eye, Layers,
  CheckSquare, Square, Trash2, Plus
} from 'lucide-react';
import { api } from '../lib/api.js';
import { Btn, Field, Select, Alert, Card, Modal } from '../components/ui.jsx';

export default function ExpertReview() {
  const [docs, setDocs] = useState([]);
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);
  const [activeTab, setActiveTab] = useState('preset'); // 'preset' | 'url' | 'upload' | 'sources'

  // Batch selection state
  const [selectedIds, setSelectedIds] = useState([]);
  const [batchActioning, setBatchActioning] = useState(false);

  // Crawling state
  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawling, setCrawling] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);

  // Document preview modal state
  const [previewData, setPreviewData] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Dynamic crawl sources state
  const [crawlSources, setCrawlSources] = useState([]);
  const [newSourceName, setNewSourceName] = useState('');
  const [newSourceKey, setNewSourceKey] = useState('');
  const [newSourceDomain, setNewSourceDomain] = useState('');
  const [newSourceUrl, setNewSourceUrl] = useState('');

  const loadDocs = () => {
    api.pendingDocs().then(data => {
      setDocs(data);
      setSelectedIds([]);
    }).catch((e) => setErr(e.message));
  };

  const loadSources = () => {
    api.listCrawlSources().then(setCrawlSources).catch(() => setCrawlSources([]));
  };

  useEffect(() => {
    loadDocs();
    loadSources();
  }, []);

  async function reviewSingle(id, status) {
    try {
      await api.reviewDoc(id, status);
      if (previewData && previewData.id === id) {
        setPreviewData(null);
      }
      loadDocs();
    } catch (e) {
      setErr(`Không thể xử lý: ${e.message}`);
    }
  }

  async function handleBatchReview(status) {
    if (selectedIds.length === 0) return;
    setBatchActioning(true);
    setErr(null);
    setMsg(null);
    try {
      await Promise.all(selectedIds.map(id => api.reviewDoc(id, status)));
      setMsg(`Đã ${status === 'APPROVED' ? 'duyệt' : 'từ chối'} thành công ${selectedIds.length} tài liệu!`);
      loadDocs();
    } catch (e) {
      setErr(`Lỗi thao tác hàng loạt: ${e.message}`);
    } finally {
      setBatchActioning(false);
    }
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === docs.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(docs.map(d => d.id));
    }
  };

  const toggleSelectOne = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  async function handlePreview(id) {
    setLoadingPreview(true);
    try {
      const res = await api.previewDoc(id);
      setPreviewData(res);
    } catch (e) {
      setErr(`Không thể tải xem trước: ${e.message}`);
    } finally {
      setLoadingPreview(false);
    }
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
        loadDocs();
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
        loadDocs();
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

  async function handleCreateSource(e) {
    e.preventDefault();
    if (!newSourceName || !newSourceKey || !newSourceDomain) return;
    setErr(null);
    setMsg(null);
    try {
      const urls = newSourceUrl.trim() ? [newSourceUrl.trim()] : [];
      await api.createCrawlSource({
        name: newSourceName.trim(),
        source_key: newSourceKey.trim().toLowerCase(),
        domain: newSourceDomain.trim(),
        base_urls: urls,
      });
      setMsg(`Đã thêm nguồn cào mới "${newSourceName}"!`);
      setNewSourceName(''); setNewSourceKey(''); setNewSourceDomain(''); setNewSourceUrl('');
      loadSources();
    } catch (e) {
      setErr(`Không thể thêm nguồn: ${e.message}`);
    }
  }

  async function handleDeleteSource(id) {
    try {
      await api.deleteCrawlSource(id);
      loadSources();
    } catch (e) {
      setErr(`Không thể xóa nguồn: ${e.message}`);
    }
  }

  async function confirmResetDocs() {
    setShowResetModal(false);
    setErr(null);
    setMsg(null);
    try {
      const res = await api.resetDocs();
      setMsg(res.message);
      loadDocs();
    } catch (e) {
      setErr(`Không thể reset: ${e.message}`);
    }
  }

  return (
    <div className="relative space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink sm:text-3xl">Duyệt tài liệu y–dược & Cào tri thức</h1>
          <p className="mt-1 text-base text-ink-2">
            Thu thập bài viết y tế uy tín, bóc tách văn bản, xem trước Semantic Chunks và duyệt vào kho RAG.
          </p>
        </div>
        <Btn variant="danger-subtle" size="md" onClick={() => setShowResetModal(true)} className="text-sm font-medium">
          <RotateCcw size={15} />
          Reset danh sách để Demo
        </Btn>
      </header>

      {/* Tabs navigation - Khung 4 Tab phân chia rõ ràng bằng đường gạch dọc | và không dùng Icon */}
      <Card className="p-2 shadow-sm">
        <div className="flex flex-wrap items-center gap-2 border-b border-paper-3 pb-2 text-base font-semibold">
          <button
            onClick={() => { setActiveTab('preset'); setErr(null); setMsg(null); }}
            className={`px-4 py-2 text-sm font-semibold transition-all ${
              activeTab === 'preset'
                ? 'rounded-md bg-accent-strong text-white shadow-sm'
                : 'text-ink-2 hover:bg-paper-2 hover:text-ink'
            }`}
          >
            Cào tự động nguồn uy tín
          </button>
          
          <span className="text-paper-3 select-none font-light">|</span>

          <button
            onClick={() => { setActiveTab('url'); setErr(null); setMsg(null); }}
            className={`px-4 py-2 text-sm font-semibold transition-all ${
              activeTab === 'url'
                ? 'rounded-md bg-accent-strong text-white shadow-sm'
                : 'text-ink-2 hover:bg-paper-2 hover:text-ink'
            }`}
          >
            Cào thủ công URL
          </button>

          <span className="text-paper-3 select-none font-light">|</span>

          <button
            onClick={() => { setActiveTab('upload'); setErr(null); setMsg(null); }}
            className={`px-4 py-2 text-sm font-semibold transition-all ${
              activeTab === 'upload'
                ? 'rounded-md bg-accent-strong text-white shadow-sm'
                : 'text-ink-2 hover:bg-paper-2 hover:text-ink'
            }`}
          >
            Tải file từ máy
          </button>

          <span className="text-paper-3 select-none font-light">|</span>

          <button
            onClick={() => { setActiveTab('sources'); setErr(null); setMsg(null); }}
            className={`px-4 py-2 text-sm font-semibold transition-all ${
              activeTab === 'sources'
                ? 'rounded-md bg-accent-strong text-white shadow-sm'
                : 'text-ink-2 hover:bg-paper-2 hover:text-ink'
            }`}
          >
            Quản lý nguồn động ({crawlSources.length})
          </button>
        </div>

        {/* Nội dung bên trong Tab với cỡ chữ to, rõ ràng */}
        <div className="p-4">
          {activeTab === 'preset' && (
            <div className="space-y-4">
              <p className="text-sm font-medium text-ink-2">
                Kích hoạt cào bài viết tự động từ các nguồn báo y tế đã kiểm định (Sức khỏe & Đời sống, Vinmec...).
              </p>
              <div className="flex flex-wrap gap-3">
                <Btn variant="subtle" size="md" disabled={crawling} onClick={() => handlePresetCrawl('moh')} className="text-sm font-medium">
                  Sức khỏe & Đời sống (Bộ Y tế)
                </Btn>
                <Btn variant="subtle" size="md" disabled={crawling} onClick={() => handlePresetCrawl('vinmec')} className="text-sm font-medium">
                  Vinmec
                </Btn>
                <Btn variant="primary" size="md" disabled={crawling} onClick={() => handlePresetCrawl('all')} className="text-sm font-semibold">
                  {crawling ? 'Đang cào dữ liệu...' : 'Cào tất cả nguồn uy tín (10 bài)'}
                </Btn>
              </div>
            </div>
          )}

          {activeTab === 'url' && (
            <form onSubmit={handleCrawl} className="space-y-4">
              <p className="text-sm font-medium text-ink-2">
                Nhập đường dẫn bài viết hướng dẫn dinh dưỡng/y tế để bóc tách văn bản chuẩn.
              </p>
              <div className="flex flex-wrap gap-3">
                <Field
                  id="crawl-url"
                  type="url"
                  required
                  placeholder="Dán đường link bài viết (vd: https://suckhoedoisong.vn/...)"
                  value={crawlUrl}
                  onChange={(e) => setCrawlUrl(e.target.value)}
                  className="w-full flex-1 sm:w-auto text-sm"
                />
                <Btn type="submit" variant="primary" disabled={crawling} size="md" className="text-sm font-semibold">
                  {crawling ? 'Đang cào…' : 'Cào bài viết'}
                </Btn>
              </div>
            </form>
          )}

          {activeTab === 'upload' && (
            <UploadTaiLieu
              onDone={(m) => { setMsg(m); setErr(null); loadDocs(); }}
              onError={(m) => { setErr(m); setMsg(null); }}
            />
          )}

          {activeTab === 'sources' && (
            <div className="space-y-4">
              <form onSubmit={handleCreateSource} className="space-y-3 rounded bg-paper-2 p-4">
                <p className="text-sm font-bold text-ink">Thêm nguồn cào dữ liệu mới:</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <Field placeholder="Tên nguồn (vd: Báo Y Tế)" value={newSourceName} onChange={e => setNewSourceName(e.target.value)} required className="text-sm" />
                  <Field placeholder="Mã nguồn (vd: moh_new)" value={newSourceKey} onChange={e => setNewSourceKey(e.target.value)} required className="text-sm" />
                  <Field placeholder="Domain (vd: suckhoedoisong.vn)" value={newSourceDomain} onChange={e => setNewSourceDomain(e.target.value)} required className="text-sm" />
                </div>
                <Field placeholder="URL bài viết đầu tiên (tùy chọn)" value={newSourceUrl} onChange={e => setNewSourceUrl(e.target.value)} className="w-full text-sm" />
                <Btn type="submit" variant="primary" size="md" className="text-sm font-semibold">
                  <Plus size={15} />
                  Lưu nguồn mới
                </Btn>
              </form>

              <div className="space-y-2">
                <p className="text-sm font-bold text-ink">Danh sách nguồn đang hoạt động:</p>
                {crawlSources.length === 0 ? (
                  <p className="text-sm text-muted">Chưa có nguồn cào động nào.</p>
                ) : (
                  crawlSources.map(s => (
                    <div key={s.id} className="flex items-center justify-between rounded bg-paper p-3 text-sm shadow-hairline">
                      <div>
                        <span className="font-semibold text-ink">{s.name}</span>
                        <span className="ml-2 text-ink-2">({s.domain} · key: {s.source_key})</span>
                      </div>
                      <button onClick={() => handleDeleteSource(s.id)} className="text-danger hover:underline">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Contextual feedback message */}
          {msg && <div className="mt-4"><Alert tone="success">{msg}</Alert></div>}
          {err && <div className="mt-4"><Alert tone="warning">{err}</Alert></div>}
        </div>
      </Card>

      {/* Action Bar for Pending Documents & Batch Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-md bg-paper-2 p-4 shadow-hairline">
        <div className="flex items-center gap-4">
          <button
            onClick={toggleSelectAll}
            className="flex items-center gap-2 text-sm font-semibold text-ink hover:text-accent-strong"
          >
            {selectedIds.length > 0 && selectedIds.length === docs.length ? (
              <CheckSquare size={20} className="text-accent-strong" />
            ) : (
              <Square size={20} className="text-ink-2" />
            )}
            {selectedIds.length === docs.length && docs.length > 0 ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
          </button>
          <span className="text-sm font-medium text-ink-2">
            Đang chờ duyệt: <strong className="text-ink text-base">{docs.length}</strong> bài
            {selectedIds.length > 0 && ` (Đã chọn ${selectedIds.length})`}
          </span>
        </div>

        {selectedIds.length > 0 && (
          <div className="flex items-center gap-3">
            <Btn
              variant="primary"
              size="md"
              disabled={batchActioning}
              onClick={() => handleBatchReview('APPROVED')}
              className="text-sm font-semibold"
            >
              <Check size={16} />
              Duyệt chọn ({selectedIds.length})
            </Btn>
            <Btn
              variant="danger-subtle"
              size="md"
              disabled={batchActioning}
              onClick={() => handleBatchReview('REJECTED')}
              className="text-sm font-semibold"
            >
              <X size={16} />
              Từ chối chọn ({selectedIds.length})
            </Btn>
          </div>
        )}
      </div>

      {docs.length === 0 && (
        <Card className="p-10 text-center text-base text-muted">
          Không có tài liệu nào đang chờ duyệt. Hãy bấm nút cào ở trên để tải bài viết mới.
        </Card>
      )}

      {/* Danh sách bài chờ duyệt - Chữ to rõ ràng */}
      <div className="space-y-4">
        {docs.map((d) => {
          const isSelected = selectedIds.includes(d.id);
          const textLen = d.raw_text ? d.raw_text.length : 0;
          const estChunks = Math.ceil(textLen / 800) || 1;

          return (
            <Card
              key={d.id}
              className={`flex flex-wrap items-center justify-between gap-4 p-5 transition-all duration-short ease-out hover:-translate-y-0.5 hover:shadow-card ${
                isSelected ? 'border-accent-strong/50 bg-accent-soft/10' : ''
              }`}
            >
              <div className="flex min-w-0 items-start gap-4">
                <button
                  type="button"
                  onClick={() => toggleSelectOne(d.id)}
                  className="mt-1 shrink-0 text-ink-2 hover:text-ink"
                >
                  {isSelected ? (
                    <CheckSquare size={22} className="text-accent-strong" />
                  ) : (
                    <Square size={22} />
                  )}
                </button>
                <div className="min-w-0">
                  <p
                    className="cursor-pointer text-base font-bold text-ink hover:text-accent-strong [overflow-wrap:anywhere]"
                    onClick={() => handlePreview(d.id)}
                  >
                    {d.title}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-ink-2">
                    <span className="font-semibold text-ink">{d.source_name || 'Nguồn web'}</span>
                    {d.source_url && (
                      <>
                        <span>·</span>
                        <a
                          href={d.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-sm font-medium text-accent-strong underline decoration-accent/40 underline-offset-2 hover:decoration-accent"
                        >
                          xem nguồn gốc
                        </a>
                      </>
                    )}
                    <span>·</span>
                    <span className="rounded bg-paper-3 px-2 py-0.5 font-mono text-xs font-semibold text-ink">
                      {(textLen / 1000).toFixed(1)}k ký tự
                    </span>
                    <span className="rounded bg-accent-soft/60 px-2 py-0.5 font-mono text-xs font-semibold text-accent-strong">
                      ~{estChunks} chunks RAG
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2.5">
                <Btn variant="subtle" size="md" onClick={() => handlePreview(d.id)} disabled={loadingPreview} className="text-sm font-medium">
                  <Eye size={15} />
                  Xem trước & Chunks
                </Btn>
                <Btn variant="primary" size="md" onClick={() => reviewSingle(d.id, 'APPROVED')} className="text-sm font-semibold">
                  <Check size={15} />
                  Duyệt
                </Btn>
                <Btn variant="danger-subtle" size="md" onClick={() => reviewSingle(d.id, 'REJECTED')} className="text-sm font-semibold">
                  <X size={15} />
                  Từ chối
                </Btn>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Modal Xem trước Văn bản bóc tách & Chunks RAG */}
      {previewData && (
        <Modal
          open={Boolean(previewData)}
          onClose={() => setPreviewData(null)}
          icon={<Layers size={22} />}
          title={`Xem trước: ${previewData.title}`}
          footer={
            <div className="flex w-full justify-between gap-3">
              <Btn variant="ghost" size="md" onClick={() => setPreviewData(null)} className="text-sm font-medium">
                Đóng
              </Btn>
              <div className="flex gap-3">
                <Btn variant="danger-subtle" size="md" onClick={() => reviewSingle(previewData.id, 'REJECTED')} className="text-sm font-semibold">
                  <X size={15} />
                  Từ chối
                </Btn>
                <Btn variant="primary" size="md" onClick={() => reviewSingle(previewData.id, 'APPROVED')} className="text-sm font-semibold">
                  <Check size={15} />
                  Duyệt vào RAG Index
                </Btn>
              </div>
            </div>
          }
        >
          <div className="max-h-[60vh] space-y-5 overflow-y-auto pr-1 text-base text-ink">
            <div>
              <span className="font-bold text-ink">Nguồn: </span>
              <span className="text-ink-2">{previewData.source_name || 'Không rõ'} ({previewData.source_url})</span>
            </div>

            <div>
              <h4 className="mb-2 font-bold text-ink">Văn bản bóc tách thô (Raw Text):</h4>
              <div className="max-h-48 overflow-y-auto rounded bg-paper-2 p-4 font-mono text-sm text-ink-2 shadow-inner">
                {previewData.raw_text}
              </div>
            </div>

            <div>
              <h4 className="mb-3 font-bold text-ink">
                Phân đoạn Ngữ nghĩa RAG ({previewData.estimated_chunks?.length || 0} chunks):
              </h4>
              <div className="space-y-3">
                {previewData.estimated_chunks?.map((chunk, idx) => (
                  <div key={idx} className="rounded border border-accent-soft bg-paper p-4 text-sm shadow-hairline">
                    <div className="mb-2 flex justify-between font-bold text-accent-strong">
                      <span>Chunk #{chunk.chunk_index + 1}</span>
                      <span>{chunk.token_count} từ (tokens)</span>
                    </div>
                    <p className="whitespace-pre-wrap text-ink-2">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Modal Reset */}
      <Modal
        open={showResetModal}
        onClose={() => setShowResetModal(false)}
        icon={<AlertTriangle size={22} />}
        tone="danger"
        title="Xác nhận Reset Dữ liệu Demo"
        footer={
          <>
            <Btn variant="ghost" size="md" onClick={() => setShowResetModal(false)} className="text-sm font-medium">
              Hủy bỏ
            </Btn>
            <Btn variant="danger" size="md" onClick={confirmResetDocs} className="text-sm font-semibold">
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
    <form onSubmit={submit} className="space-y-4">
      <p className="text-sm font-medium text-ink-2">Tải tệp văn bản (.txt, .md, .pdf) hoặc dán thẳng nội dung bài viết.</p>
      <div className="flex flex-wrap gap-3">
        <Field
          required
          placeholder="Tiêu đề tài liệu"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full flex-1 sm:w-auto text-sm"
        />
        <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="w-full sm:w-60 text-sm">
          <option value="">— Chưa phân loại —</option>
          {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".txt,.md,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="min-h-10 flex-1 rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink-2 shadow-hairline file:mr-3 file:rounded-sm file:border-0 file:bg-accent-soft file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-accent-strong"
        />
      </div>

      <textarea
        rows={3}
        placeholder="…hoặc dán thẳng nội dung tài liệu vào đây"
        value={rawText}
        onChange={(e) => setRawText(e.target.value)}
        className="w-full rounded-sm bg-paper-2 px-3 py-2 text-sm text-ink shadow-hairline placeholder:text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
      />

      <Btn type="submit" variant="primary" size="md" disabled={dangTai || !title.trim() || (!file && !rawText.trim())} className="text-sm font-semibold">
        <Upload size={15} />
        {dangTai ? 'Đang tải lên…' : 'Tải lên tài liệu'}
      </Btn>
    </form>
  );
}