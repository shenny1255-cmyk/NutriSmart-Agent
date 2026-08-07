import { useEffect, useState } from 'react';
import { Eye, Filter, Search, X } from 'lucide-react';
import { api } from '../lib/api.js';
import { MAX_BIRTH_DATE as TODAY } from '../lib/date.js';
import { Alert, Btn, EmptyRow, Field, Modal, Select, TableShell, Td, THead, Tr } from '../components/ui.jsx';

const ACTIONS = {
  CREATE: { label: 'Tạo mới', cls: 'bg-accent-soft text-accent-strong' },
  UPDATE: { label: 'Cập nhật', cls: 'bg-info-soft text-info' },
  DELETE: { label: 'Xóa', cls: 'bg-danger-soft text-danger' },
  APPROVE: { label: 'Phê duyệt', cls: 'bg-warning-soft text-warning-strong' },
};

const ENTITIES = {
  users: 'Tài khoản',
  doc_categories: 'Danh mục',
  documents: 'Tài liệu',
  chat_messages: 'Tin nhắn',
};

const MIN_AUDIT_DATE = '2020-01-01';
const EMPTY_FILTERS = { q: '', action: '', entity: '', date_from: '', date_to: '' };
const FIELD_LABELS = {
  email: 'Email', full_name: 'Họ và tên', role: 'Vai trò', name: 'Tên',
  slug: 'Đường dẫn', parent_id: 'Danh mục cha',
};

function validDate(value) {
  return value === '' || (/^\d{4}-\d{2}-\d{2}$/.test(value) && value >= MIN_AUDIT_DATE && value <= TODAY);
}

function calendarOnlyKeyDown(event) {
  if (event.key !== 'Tab') event.preventDefault();
}

function filtersHaveValidDates(filters) {
  return validDate(filters.date_from) && validDate(filters.date_to)
    && (!filters.date_from || !filters.date_to || filters.date_from <= filters.date_to);
}

function formatAuditTime(value) {
  const date = new Date(value);
  return `${date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })} · ${date.toLocaleDateString('vi-VN')}`;
}

function DataBlock({ title, data }) {
  const entries = Object.entries(data || {});
  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold text-ink">{title}</h3>
      {entries.length === 0 ? <p className="text-sm text-muted">Không có dữ liệu.</p> : (
        <dl className="divide-y divide-rule-2 rounded-sm bg-paper-3 px-3 text-sm">
          {entries.map(([key, value]) => (
            <div key={key} className="grid grid-cols-[minmax(100px,1fr)_2fr] gap-3 py-2">
              <dt className="font-medium text-ink-2">{FIELD_LABELS[key] || key}</dt>
              <dd className="break-words text-ink">{value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}

export default function AdminAudit() {
  const [result, setResult] = useState({ items: [], total: 0, page: 1, page_size: 20 });
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);
  const datesValid = filtersHaveValidDates(filters);
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  async function load(targetPage = page, selectedFilters = filters) {
    if (!filtersHaveValidDates(selectedFilters)) {
      setError(`Khoảng ngày không hợp lệ. Hãy chọn từ ${MIN_AUDIT_DATE} đến ${TODAY}, và Từ ngày không được sau Đến ngày.`);
      return;
    }
    setLoading(true);
    try {
      setResult(await api.auditLogs({ ...selectedFilters, page: targetPage, page_size: 20 }));
      setPage(targetPage);
      setError(null);
    } catch (e) {
      setError(e.message || 'Không tải được nhật ký hệ thống.');
    } finally {
      setLoading(false);
    }
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    load(1, EMPTY_FILTERS);
  }

  useEffect(() => { load(1); }, []);
  const pageCount = Math.max(1, Math.ceil(result.total / result.page_size));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight">Nhật ký hệ thống</h1>
        <p className="mt-1 text-sm text-muted">Theo dõi các thao tác quản trị quan trọng. Mật khẩu và token không được hiển thị.</p>
      </div>

      <div className="grid gap-3 rounded-md bg-paper-2 p-4 shadow-hairline sm:grid-cols-2 xl:grid-cols-12">
        <Field value={filters.q} onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          onKeyDown={(e) => e.key === 'Enter' && load(1)} placeholder="Tên, email hoặc ID…" className="xl:col-span-3" />
        <Select className="xl:col-span-2" value={filters.action} onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}>
          <option value="">Mọi hành động</option>
          {Object.entries(ACTIONS).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}
        </Select>
        <Select className="xl:col-span-2" value={filters.entity} onChange={(e) => setFilters((f) => ({ ...f, entity: e.target.value }))}>
          <option value="">Mọi đối tượng</option>
          {Object.entries(ENTITIES).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select>
        <label className="text-xs font-medium text-ink-2 xl:col-span-2">
          Từ ngày
          <Field type="date" min={MIN_AUDIT_DATE} max={TODAY} value={filters.date_from}
            onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
            onKeyDown={calendarOnlyKeyDown} onPaste={(e) => e.preventDefault()}
            aria-invalid={!validDate(filters.date_from) || (filters.date_from && filters.date_to && filters.date_from > filters.date_to)}
            className={`mt-1 w-full ${!validDate(filters.date_from) || (filters.date_from && filters.date_to && filters.date_from > filters.date_to) ? 'outline outline-2 outline-danger' : ''}`} />
        </label>
        <label className="text-xs font-medium text-ink-2 xl:col-span-2">
          Đến ngày
          <Field type="date" min={MIN_AUDIT_DATE} max={TODAY} value={filters.date_to}
            onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
            onKeyDown={calendarOnlyKeyDown} onPaste={(e) => e.preventDefault()}
            aria-invalid={!validDate(filters.date_to) || (filters.date_from && filters.date_to && filters.date_from > filters.date_to)}
            className={`mt-1 w-full ${!validDate(filters.date_to) || (filters.date_from && filters.date_to && filters.date_from > filters.date_to) ? 'outline outline-2 outline-danger' : ''}`} />
        </label>
        <div className="flex flex-wrap items-center justify-end gap-2 sm:col-span-2 xl:col-span-12">
          {activeFilterCount > 0 && <span className="mr-auto text-xs text-muted">Đang chọn {activeFilterCount} bộ lọc</span>}
          <Btn onClick={clearFilters} disabled={loading || activeFilterCount === 0}><X size={15} />Xóa bộ lọc</Btn>
          <Btn variant="primary" onClick={() => load(1)} disabled={loading || !datesValid}>
            {filters.q ? <Search size={15} /> : <Filter size={15} />}{loading ? 'Đang lọc…' : 'Áp dụng bộ lọc'}
          </Btn>
        </div>
      </div>

      {error && <Alert tone="danger">{error}</Alert>}

      <TableShell>
        <THead cols={['Thời gian', 'Người thực hiện', 'Hành động', 'Đối tượng', 'Mô tả', '']} />
        <tbody>
          {!loading && result.items.length === 0 && <EmptyRow colSpan={6}>Chưa có bản ghi phù hợp.</EmptyRow>}
          {result.items.map((log) => {
            const action = ACTIONS[log.action] || { label: log.action, cls: 'bg-paper-3 text-ink-2' };
            return (
              <Tr key={log.id}>
                <Td className="whitespace-nowrap text-ink-2">{formatAuditTime(log.created_at)}</Td>
                <Td>
                  <p className="font-medium text-ink">{log.actor_name || 'Hệ thống'}</p>
                  {log.actor_email && <p className="text-xs text-muted">{log.actor_email}</p>}
                </Td>
                <Td className="whitespace-nowrap"><span className={`inline-flex whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${action.cls}`}>{action.label}</span></Td>
                <Td>
                  <p className="font-medium text-ink-2">{ENTITIES[log.entity] || log.entity}</p>
                  <p className="max-w-48 truncate text-xs text-muted" title={log.target_label}>{log.target_label || '—'}</p>
                </Td>
                <Td className="max-w-md text-ink-2">{log.description}</Td>
                <Td className="text-right">
                  <Btn size="sm" variant="subtle" className="min-w-max whitespace-nowrap" onClick={() => setDetail(log)}><Eye size={14} />Chi tiết</Btn>
                </Td>
              </Tr>
            );
          })}
        </tbody>
      </TableShell>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <span>{result.total} bản ghi · Trang {page}/{pageCount}</span>
        <div className="flex gap-2">
          <Btn size="sm" onClick={() => load(page - 1)} disabled={loading || page <= 1}>Trang trước</Btn>
          <Btn size="sm" onClick={() => load(page + 1)} disabled={loading || page >= pageCount}>Trang sau</Btn>
        </div>
      </div>

      <Modal open={!!detail} onClose={() => setDetail(null)} icon={<Eye size={18} />} title="Chi tiết thao tác"
        footer={<Btn variant="primary" onClick={() => setDetail(null)}>Đóng</Btn>}>
        {detail && <div className="space-y-5">
          <dl className="grid gap-2 rounded-sm bg-paper-3 p-3 text-sm sm:grid-cols-2">
            <div><dt className="text-muted">Người thực hiện</dt><dd className="font-medium">{detail.actor_name || 'Hệ thống'} {detail.actor_email ? `(${detail.actor_email})` : ''}</dd></div>
            <div><dt className="text-muted">Thời gian</dt><dd>{new Date(detail.created_at).toLocaleString('vi-VN')}</dd></div>
            <div><dt className="text-muted">Đối tượng</dt><dd>{ENTITIES[detail.entity] || detail.entity} · {detail.target_label || '—'}</dd></div>
            <div><dt className="text-muted">ID kỹ thuật</dt><dd className="break-all font-mono text-xs">{detail.entity_id || '—'}</dd></div>
            <div><dt className="text-muted">Địa chỉ IP</dt><dd>{detail.ip_address || 'Chưa ghi nhận'}</dd></div>
          </dl>
          <DataBlock title="Dữ liệu trước thay đổi" data={detail.before_data} />
          <DataBlock title="Dữ liệu sau thay đổi" data={detail.after_data} />
        </div>}
      </Modal>
    </div>
  );
}
