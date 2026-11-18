import { useCallback, useEffect, useState } from 'react';
import { Check, ClipboardCheck, Database, RotateCcw, X } from 'lucide-react';
import { api } from '../lib/api.js';
import { Alert, Btn, Field, Modal } from '../components/ui.jsx';

const round = (value) => Math.round(Number(value ?? 0));

function mergedRows(item) {
  const rows = new Map();
  const key = (c) => `${c.name}|${c.fct_code ?? ''}`;
  item.predicted_components.forEach((c) => rows.set(key(c), { ...c, ai: c.grams, user: 0, grams: 0 }));
  item.final_components.forEach((c) => {
    const old = rows.get(key(c));
    rows.set(key(c), { ...(old ?? c), ai: old?.ai ?? 0, user: c.grams, grams: c.grams });
  });
  return [...rows.values()];
}

function CorrectionCard({ item, onDone, onError }) {
  const [rows, setRows] = useState(() => mergedRows(item));
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmReject, setConfirmReject] = useState(false);

  const kept = rows.filter((r) => Number(r.grams) > 0);
  const kcal = round(kept.reduce((sum, r) => sum + (r.per_100g.energy_kcal * Number(r.grams)) / 100, 0));
  const gramsValid = rows.every((r) => Number(r.grams) >= 0 && Number(r.grams) <= 3000);

  async function submit(action) {
    setBusy(true);
    try {
      await api.reviewVisionFeedback(item.id, {
        action,
        note: note.trim() || null,
        components: action === 'APPROVE'
          ? kept.map((r) => ({ name: r.name, grams: Number(r.grams), fct_code: r.fct_code ?? null }))
          : null,
      });
      onDone(action === 'APPROVE' ? 'Đã duyệt ca sửa vào kho few-shot.' : 'Đã từ chối ca sửa.');
    } catch (e) {
      onError(typeof e.detail === 'string' ? e.detail : 'Không lưu được kết quả duyệt, thử lại sau.');
      setBusy(false);
    }
  }

  return (
    <article className="rounded-md bg-paper-2 p-4 shadow-hairline sm:p-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-lg font-bold text-ink">{item.food_name}</h2>
          <p className="text-xs text-muted">{new Date(item.created_at).toLocaleString('vi-VN')}</p>
        </div>
        <dl className="flex gap-4 text-right text-xs text-ink-2">
          <div><dt>AI dự đoán</dt><dd className="text-base font-bold text-ink">{round(item.predicted_kcal)} kcal</dd></div>
          <div><dt>Người dùng chốt</dt><dd className="text-base font-bold text-ink">{round(item.final_kcal)} kcal</dd></div>
          <div><dt>Chuyên gia</dt><dd className="text-base font-bold text-accent-strong">{kcal} kcal</dd></div>
        </dl>
      </header>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[32rem] text-sm">
          <thead>
            <tr className="border-b border-rule-2 text-left text-xs text-muted">
              <th scope="col" className="py-2 pr-3 font-medium">Thành phần</th>
              <th scope="col" className="w-20 py-2 pr-3 text-right font-medium">AI (g)</th>
              <th scope="col" className="w-24 py-2 pr-3 text-right font-medium">Người dùng (g)</th>
              <th scope="col" className="w-28 py-2 text-right font-medium">Chuyên gia (g)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.name}-${row.fct_code ?? 'ai'}`} className="border-b border-rule-2/60">
                <td className="py-2 pr-3 text-ink">{row.name}</td>
                <td className="py-2 pr-3 text-right text-ink-2 [font-variant-numeric:tabular-nums]">{round(row.ai)}</td>
                <td className="py-2 pr-3 text-right font-semibold text-ink [font-variant-numeric:tabular-nums]">{round(row.user)}</td>
                <td className="py-2 text-right">
                  <Field type="number" min="0" max="3000" value={row.grams} aria-label={`Số gram chuyên gia chốt cho ${row.name}`}
                    onChange={(e) => setRows(rows.map((r, i) => (i === index ? { ...r, grams: e.target.value } : r)))}
                    className="w-24 text-right" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <label className="mt-4 block text-sm font-medium text-ink-2">
        Ghi chú của chuyên gia
        <Field value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} className="mt-1 w-full"
          placeholder="Lý do chỉnh hoặc từ chối (không bắt buộc)" />
      </label>

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Btn type="button" variant="ghost" disabled={busy} onClick={() => setConfirmReject(true)}><X size={16} />Từ chối</Btn>
        <Btn type="button" variant="primary" disabled={busy || kept.length === 0 || !gramsValid} onClick={() => submit('APPROVE')}>
          <Check size={16} />Duyệt vào kho
        </Btn>
      </div>

      <Modal open={confirmReject} onClose={() => setConfirmReject(false)} tone="danger" icon={<X size={18} />} title="Từ chối ca sửa này?"
        footer={<><Btn variant="ghost" onClick={() => setConfirmReject(false)}>Quay lại</Btn>
          <Btn variant="primary" disabled={busy} onClick={() => { setConfirmReject(false); submit('REJECT'); }}>Từ chối</Btn></>}>
        <p className="text-sm text-ink-2">Ca này sẽ không được dùng làm ví dụ cho AI.</p>
      </Modal>
    </article>
  );
}

function StoreRow({ example, onToggle }) {
  return (
    <li className="flex flex-wrap items-center gap-3 rounded-md bg-paper-2 p-4 shadow-hairline">
      <div className="min-w-0 flex-1 basis-64">
        <p className="font-semibold text-ink">{example.food_name}</p>
        <p className="mt-1 text-sm text-ink-2">{example.components.map((c) => `${c.name} ${round(c.grams)} g`).join(', ')}</p>
      </div>
      <span className="text-sm font-bold text-ink [font-variant-numeric:tabular-nums]">{round(example.total_kcal)} kcal</span>
      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${example.is_active ? 'bg-accent-soft text-accent-strong' : 'bg-paper-3 text-ink-2'}`}>
        {example.is_active ? 'Đang dùng' : 'Đã tắt'}
      </span>
      <Btn type="button" size="sm" variant="ghost" onClick={() => onToggle(example)}>{example.is_active ? 'Tắt' : 'Bật lại'}</Btn>
    </li>
  );
}

export default function ExpertCorrections() {
  const [tab, setTab] = useState('queue');
  const [queue, setQueue] = useState([]);
  const [store, setStore] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([api.visionFeedbackQueue(), api.fewShotExamples()])
      .then(([pending, examples]) => { setQueue(pending); setStore(examples); setErr(null); })
      .catch((e) => setErr(typeof e.detail === 'string' ? e.detail : 'Không tải được dữ liệu duyệt.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function toggle(example) {
    try {
      const updated = await api.updateFewShot(example.id, { is_active: !example.is_active });
      setStore((rows) => rows.map((r) => (r.id === updated.id ? updated : r)));
    } catch (e) {
      setErr(typeof e.detail === 'string' ? e.detail : 'Không cập nhật được ví dụ.');
    }
  }

  const tabs = [
    { id: 'queue', label: `Chờ duyệt (${queue.length})`, icon: ClipboardCheck },
    { id: 'store', label: `Kho few-shot (${store.length})`, icon: Database },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink">Duyệt ca sửa khẩu phần</h1>
          <p className="mt-1 text-sm text-ink-2">Chỉ ca được duyệt mới trở thành ví dụ cho AI ở các lần quét món tương tự.</p>
        </div>
        <Btn type="button" variant="ghost" onClick={load} disabled={loading}><RotateCcw size={16} />Tải lại</Btn>
      </header>

      <div className="flex gap-1 border-b border-rule-2" role="tablist" aria-label="Khu vực duyệt ca sửa">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`flex min-h-11 items-center gap-2 border-b-2 px-3 text-sm font-semibold ${tab === id ? 'border-accent-strong text-accent-strong' : 'border-transparent text-ink-2 hover:text-ink'}`}>
            <Icon size={16} aria-hidden="true" />{label}
          </button>
        ))}
      </div>

      {err && <Alert tone="danger">{err}</Alert>}
      {msg && <Alert tone="success">{msg}</Alert>}
      {loading && <p className="text-sm text-muted">Đang tải dữ liệu...</p>}

      {!loading && tab === 'queue' && (queue.length === 0
        ? <p className="rounded-md bg-paper-2 p-6 text-center text-sm text-ink-2 shadow-hairline">Chưa có ca sửa nào chờ duyệt.</p>
        : <div className="space-y-4">{queue.map((item) => (
          <CorrectionCard key={item.id} item={item} onError={setErr}
            onDone={(text) => { setMsg(text); setErr(null); load(); }} />
        ))}</div>)}

      {!loading && tab === 'store' && (store.length === 0
        ? <p className="rounded-md bg-paper-2 p-6 text-center text-sm text-ink-2 shadow-hairline">Kho few-shot chưa có ví dụ nào.</p>
        : <ul className="space-y-3">{store.map((example) => <StoreRow key={example.id} example={example} onToggle={toggle} />)}</ul>)}
    </div>
  );
}
