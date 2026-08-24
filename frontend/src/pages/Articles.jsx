import { useEffect, useState } from 'react';
import { ExternalLink, Search, X } from 'lucide-react';
import { api } from '../lib/api.js';
import { Alert, Btn, Card, Field, Select } from '../components/ui.jsx';

const PAGE_SIZE = 12;
const EMPTY_FILTERS = { q: '', category_id: '' };

function formatApprovedDate(value) {
  if (!value) return null;
  return new Date(value).toLocaleDateString('vi-VN');
}

function SkeletonCard() {
  return (
    <Card className="animate-pulse space-y-3 p-5">
      <div className="h-5 w-24 rounded bg-paper-3" />
      <div className="h-5 w-4/5 rounded bg-paper-3" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded bg-paper-3" />
        <div className="h-3 w-full rounded bg-paper-3" />
        <div className="h-3 w-2/3 rounded bg-paper-3" />
      </div>
      <div className="h-4 w-1/2 rounded bg-paper-3" />
    </Card>
  );
}

function ArticleCard({ article }) {
  const approved = formatApprovedDate(article.approved_at);
  return (
    <Card className="flex flex-col gap-3 p-5 transition-all duration-short ease-out hover:-translate-y-0.5 hover:shadow-card">
      {article.category && (
        <span className="w-max rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent-strong">
          {article.category.name}
        </span>
      )}
      <h3 className="font-display text-base font-bold leading-snug text-ink">{article.title}</h3>
      {article.excerpt && <p className="text-sm leading-relaxed text-ink-2">{article.excerpt}</p>}
      <div className="flex flex-wrap items-center gap-x-2 text-xs text-muted">
        <span className="font-medium text-ink-2">{article.source_name || 'Không rõ nguồn'}</span>
        {approved && <><span>·</span><span>Duyệt ngày {approved}</span></>}
      </div>
      <div className="mt-auto pt-1">
        {article.source_url ? (
          <a
            href={article.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex min-h-9 items-center gap-1.5 rounded-sm bg-paper-2 px-3 py-1.5 text-xs font-semibold text-accent-strong shadow-hairline transition-[background-color] duration-short ease-out hover:bg-accent-soft focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <ExternalLink size={14} />
            Đọc bài gốc
          </a>
        ) : (
          <span className="text-xs italic text-muted">Chưa có liên kết nguồn</span>
        )}
      </div>
    </Card>
  );
}

export default function Articles() {
  const [qInput, setQInput] = useState('');
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [firstLoad, setFirstLoad] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => { api.articleCategories().then(setCategories).catch(() => setCategories([])); }, []);

  async function load(targetPage, appliedFilters = filters) {
    setLoading(true);
    setError(null);
    try {
      const data = await api.articles({ ...appliedFilters, page: targetPage, page_size: PAGE_SIZE });
      setResult(data);
      setPage(data.page);
    } catch (e) {
      setError(e.message || 'Không tải được kho bài viết.');
    } finally {
      setLoading(false);
      setFirstLoad(false);
    }
  }

  useEffect(() => { load(1, EMPTY_FILTERS); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function submitSearch(e) {
    e.preventDefault();
    const next = { ...filters, q: qInput.trim() };
    setFilters(next);
    load(1, next);
  }

  function changeCategory(categoryId) {
    const next = { ...filters, category_id: categoryId };
    setFilters(next);
    load(1, next);
  }

  function clearFilters() {
    setQInput('');
    setFilters(EMPTY_FILTERS);
    load(1, EMPTY_FILTERS);
  }

  const pageCount = Math.max(1, Math.ceil(result.total / result.page_size));
  const hasActiveFilters = Boolean(filters.q || filters.category_id);

  return (
    <div className="space-y-5">
      <header>
        <h1 className="font-display text-2xl font-bold text-ink">Kho bài viết dinh dưỡng</h1>
        <p className="mt-1 text-sm text-ink-2">
          Kiến thức dinh dưỡng đã được chuyên gia kiểm duyệt và phê duyệt. Bấm “Đọc bài gốc” để xem nguồn đầy đủ.
        </p>
      </header>

      {/* Hàng công cụ: tìm kiếm (Enter/nút) + lọc danh mục + xóa lọc */}
      <form onSubmit={submitSearch} className="flex flex-wrap items-center gap-3">
        <Field
          type="search"
          placeholder="Tìm theo tiêu đề hoặc nguồn…"
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          disabled={loading}
          className="w-full flex-1 sm:w-auto sm:min-w-64"
          aria-label="Tìm kiếm bài viết"
        />
        <Select
          value={filters.category_id}
          onChange={(e) => changeCategory(e.target.value)}
          disabled={loading}
          className="w-full sm:w-60"
          aria-label="Lọc theo danh mục"
        >
          <option value="">Tất cả danh mục</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name} ({c.article_count})</option>
          ))}
        </Select>
        <Btn type="submit" variant="primary" disabled={loading}>
          <Search size={15} />
          {loading ? 'Đang tìm…' : 'Tìm kiếm'}
        </Btn>
        {hasActiveFilters && (
          <Btn type="button" variant="ghost" onClick={clearFilters} disabled={loading}>
            <X size={15} />
            Xóa bộ lọc
          </Btn>
        )}
      </form>

      {error && (
        <div className="space-y-2">
          <Alert tone="danger">{error}</Alert>
          <Btn variant="subtle" onClick={() => load(page)}>Thử lại</Btn>
        </div>
      )}

      {!error && !firstLoad && (
        <p className="text-sm text-muted">{result.total} bài viết phù hợp · Trang {page}/{pageCount}</p>
      )}

      {/* Lưới card: 1 cột mobile, 2 cột tablet, 3 cột desktop */}
      {firstLoad && loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : !error && result.items.length === 0 && !loading ? (
        <Card className="space-y-3 p-10 text-center">
          <p className="text-base text-muted">
            {hasActiveFilters ? 'Không tìm thấy bài viết phù hợp với bộ lọc hiện tại.' : 'Chưa có bài viết nào được phê duyệt.'}
          </p>
          {hasActiveFilters && (
            <Btn variant="subtle" onClick={clearFilters}><X size={15} />Xóa bộ lọc</Btn>
          )}
        </Card>
      ) : (
        <div className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-3 ${loading ? 'opacity-60' : ''}`}>
          {result.items.map((article) => <ArticleCard key={article.id} article={article} />)}
        </div>
      )}

      {/* Phân trang theo pattern AdminAudit */}
      {!error && !firstLoad && result.total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
          <span>{result.total} bài viết · Trang {page}/{pageCount}</span>
          <div className="flex gap-2">
            <Btn size="sm" onClick={() => load(page - 1)} disabled={loading || page <= 1}>Trang trước</Btn>
            <Btn size="sm" onClick={() => load(page + 1)} disabled={loading || page >= pageCount}>Trang sau</Btn>
          </div>
        </div>
      )}
    </div>
  );
}

