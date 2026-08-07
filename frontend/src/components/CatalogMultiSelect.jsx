import { useMemo, useState } from 'react';
import { Check, Pencil, Plus, Search, X } from 'lucide-react';
import { Btn, Field, Modal } from './ui.jsx';

function normalizeSearch(value) {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('vi').trim();
}

export default function CatalogMultiSelect({ kind, items, selected, onChange }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState(new Set());
  const isCondition = kind === 'condition';
  const label = isCondition ? 'bệnh nền' : 'dị ứng';
  const selectedItems = items.filter((item) => selected.includes(item.id));
  const visibleItems = selectedItems.slice(0, 4);
  const hiddenCount = Math.max(0, selectedItems.length - visibleItems.length);

  const filteredItems = useMemo(() => {
    const normalizedQuery = normalizeSearch(query);
    return [...items]
      .filter((item) => !normalizedQuery || normalizeSearch(item.name).includes(normalizedQuery))
      .sort((a, b) => Number(draft.has(b.id)) - Number(draft.has(a.id)) || a.name.localeCompare(b.name, 'vi'));
  }, [draft, items, query]);

  function showPicker() {
    setDraft(new Set(selected));
    setQuery('');
    setOpen(true);
  }

  function toggle(id) {
    setDraft((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function apply() {
    onChange([...draft]);
    setOpen(false);
  }

  return (
    <div className="space-y-2">
      {selectedItems.length === 0 ? (
        <p className="rounded-sm bg-paper-3 px-3 py-2.5 text-base text-ink-2">Chưa ghi nhận {label}.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {visibleItems.map((item) => (
            <span key={item.id} className="inline-flex min-h-10 items-center gap-1 rounded-full bg-accent-soft px-3.5 py-2 text-sm font-medium text-accent-strong">
              {item.name}
              <button type="button" onClick={() => onChange(selected.filter((id) => id !== item.id))}
                className="-my-1 -mr-2 flex h-9 w-9 items-center justify-center rounded-full hover:bg-white/60 hover:text-danger"
                aria-label={`Bỏ chọn ${item.name}`}><X size={14} /></button>
            </span>
          ))}
          {hiddenCount > 0 && (
            <button type="button" onClick={showPicker}
              className="min-h-10 rounded-full bg-paper-3 px-3.5 py-2 text-sm font-semibold text-accent-strong shadow-hairline">
              +{hiddenCount} mục khác
            </button>
          )}
        </div>
      )}

      <Btn type="button" size="sm" variant="subtle" className="text-base" onClick={showPicker}>
        {selectedItems.length > 0 ? <Pencil size={14} /> : <Plus size={14} />}
        {selectedItems.length > 0 ? `Chỉnh sửa lựa chọn (${selectedItems.length})` : `Chọn ${label}`}
      </Btn>

      <Modal open={open} onClose={() => setOpen(false)} icon={<Search size={18} />}
        title={`Chọn ${label}`}
        footer={<>
          <Btn variant="ghost" onClick={() => setDraft(new Set())} disabled={draft.size === 0}>Bỏ chọn tất cả</Btn>
          <Btn variant="ghost" onClick={() => setOpen(false)}>Hủy</Btn>
          <Btn variant="primary" onClick={apply}>Áp dụng ({draft.size})</Btn>
        </>}>
        <div className="space-y-3">
          <Field autoFocus value={query} onChange={(event) => setQuery(event.target.value)}
            placeholder={`Tìm ${label}…`} className="w-full" />
          <p className="text-xs text-muted">Các mục đã chọn được đưa lên đầu danh sách.</p>
          <div className="max-h-72 space-y-1 overflow-y-auto pr-1">
            {filteredItems.length === 0 && (
              <p className="rounded-sm bg-paper-3 p-3 text-sm text-muted">Không tìm thấy. Bạn có thể đóng cửa sổ và dùng mục “Tự khai báo”.</p>
            )}
            {filteredItems.map((item) => {
              const checked = draft.has(item.id);
              return (
                <button key={item.id} type="button" onClick={() => toggle(item.id)}
                  className={`flex min-h-11 w-full items-center gap-3 rounded-sm px-3 py-2 text-left text-sm transition-colors ${checked ? 'bg-accent-soft text-accent-strong' : 'hover:bg-paper-3'}`}>
                  <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${checked ? 'border-accent-strong bg-accent-strong text-white' : 'border-rule'}`}>
                    {checked && <Check size={13} strokeWidth={3} />}
                  </span>
                  <span className="font-medium">{item.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </Modal>
    </div>
  );
}
