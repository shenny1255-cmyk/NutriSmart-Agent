import { useState } from 'react';
import { AlertTriangle, Plus, X } from 'lucide-react';
import { Btn, Field, Modal, Select } from './ui.jsx';
import { customHealthTermError } from '../lib/validation.js';

export default function CustomHealthTerms({ kind, values, existingNames, onChange }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [touched, setTouched] = useState(false);
  const [severity, setSeverity] = useState('');
  const normalized = input.trim().replace(/\s+/g, ' ');
  const validationError = input ? customHealthTermError(input) : '';
  const valueNames = values.map((value) => typeof value === 'string' ? value : value.name);
  const duplicate = normalized && [...valueNames, ...existingNames]
    .some((name) => name.trim().toLocaleLowerCase('vi') === normalized.toLocaleLowerCase('vi'));
  const error = validationError || (duplicate ? 'Mục này đã có trong hồ sơ.' : '')
    || (values.length >= 10 ? 'Chỉ được tự khai báo tối đa 10 mục.' : '');
  const isCondition = kind === 'condition';
  const label = isCondition ? 'bệnh nền' : 'dị ứng';
  const severityLabels = { UNKNOWN: 'Chưa xác định', MILD: 'Nhẹ', MODERATE: 'Trung bình', SEVERE: 'Nghiêm trọng' };

  function close() {
    setOpen(false);
    setInput('');
    setTouched(false);
    setSeverity('');
  }

  function add() {
    setTouched(true);
    if (!normalized || error || (!isCondition && !severity)) return;
    onChange([...values, isCondition ? normalized : { name: normalized, severity }]);
    close();
  }

  return (
    <div className="mt-1">
      {values.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2">
          {values.map((value, index) => {
            const name = typeof value === 'string' ? value : value.name;
            const level = typeof value === 'string' ? 'UNKNOWN' : value.severity;
            return (
            <span key={`${name}-${index}`} title="Thông tin do bạn cung cấp, chưa được hệ thống xác minh."
              className="inline-flex min-h-10 items-center gap-2 rounded-full bg-warning-soft px-3.5 py-1 text-sm font-medium text-ink-2">
              {name}<span className="rounded-full bg-white/70 px-1.5 py-0.5 text-xs font-medium text-warning-strong">Tự khai báo</span>
              {!isCondition && <span className="text-xs text-warning-strong">{severityLabels[level] || severityLabels.UNKNOWN}</span>}
              <button type="button" onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))}
                className="-my-1 -mr-2 flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-white/60 hover:text-danger"
                aria-label={`Xóa ${name}`}><X size={15} /></button>
            </span>
          );})}
        </div>
      )}
      <Btn type="button" size="sm" variant="ghost" className="px-1 text-base text-ink-2 hover:text-accent-strong" onClick={() => setOpen(true)} disabled={values.length >= 10}>
        <Plus size={14} />Không có trong danh sách? Tự khai báo
      </Btn>

      <Modal open={open} onClose={close} icon={<Plus size={18} />} title={`Thêm ${label} tự khai báo`}
        footer={<><Btn variant="ghost" onClick={close}>Hủy</Btn><Btn variant="primary" onClick={add} disabled={!normalized || !!error || (!isCondition && !severity)}>Thêm</Btn></>}>
        <div className="space-y-3">
          <div className="flex gap-2 rounded-sm bg-warning-soft p-3 text-sm text-ink-2">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warning-strong" />
            <p>{isCondition
              ? 'Chỉ nhập tình trạng đã được chuyên gia y tế chẩn đoán. Nội dung này được đánh dấu là tự khai báo.'
              : 'Chỉ nhập thực phẩm hoặc tác nhân từng gây phản ứng dị ứng. Nội dung này được đánh dấu là tự khai báo.'}</p>
          </div>
          <label className="block text-sm font-medium text-ink-2">
            Tên {label}
            <Field autoFocus maxLength={80} value={input} onChange={(e) => { setInput(e.target.value); setTouched(true); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
              aria-invalid={touched && !!error}
              placeholder={isCondition ? 'VD: Hen phế quản' : 'VD: Trứng'}
              className={`mt-1 w-full ${touched && error ? 'outline outline-2 outline-danger' : ''}`} />
          </label>
          {touched && error
            ? <p className="text-xs font-medium text-danger">{error}</p>
            : <p className="text-xs text-muted">Từ 2–80 ký tự, không chứa emoji hoặc ký tự đặc biệt.</p>}
          {!isCondition && (
            <label className="block text-sm font-medium text-ink-2">
              Mức độ phản ứng
              <Select value={severity} onChange={(e) => setSeverity(e.target.value)} className="mt-1 w-full">
                <option value="">— Chọn mức độ —</option>
                <option value="MILD">Nhẹ</option>
                <option value="MODERATE">Trung bình</option>
                <option value="SEVERE">Nghiêm trọng</option>
                <option value="UNKNOWN">Chưa xác định</option>
              </Select>
            </label>
          )}
        </div>
      </Modal>
    </div>
  );
}
