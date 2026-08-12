import { useEffect, useRef, useState } from 'react';
import { Send, Bot, User, BookOpenText, ChevronDown, ExternalLink, Trash2, Sparkles } from 'lucide-react';
import { api } from '../lib/api.js';
import { Modal, Btn } from '../components/ui.jsx';

const QUICK_PROMPTS = [
  'Gợi ý thực đơn giảm cân hôm nay cho tôi',
  'Chế độ ăn phù hợp cho người cao huyết áp',
  'Thịt bò và sữa có tốt cho người tăng huyết áp không?',
  'Mẹo uống đủ 2 lít nước mỗi ngày',
];

export default function Chat() {
  const [messages, setMessages] = useState([]);   // { role, content, citations? }
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [confirmClearOpen, setConfirmClearOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const endRef = useRef(null);

  // Tải lịch sử trò chuyện khi mở trang
  useEffect(() => {
    api.chatHistory()
      .then((rows) => setMessages(rows.map((m) => ({
        role: m.role,
        content: m.content,
        citations: m.citations,
      }))))
      .catch(() => { });
  }, []);

  // Tự cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  async function sendPrompt(text) {
    const promptText = (text || input).trim();
    if (!promptText || sending) return;

    setError(null);
    setInput('');

    setMessages((m) => [
      ...m,
      { role: 'user', content: promptText },
      { role: 'assistant', content: '', citations: [] },
    ]);
    setSending(true);

    await api.streamChat(promptText, {
      onToken: (token) => {
        setMessages((m) => {
          const next = [...m];
          const last = next[next.length - 1];
          if (last && last.role === 'assistant') {
            next[next.length - 1] = {
              ...last,
              content: last.content + token,
            };
          }
          return next;
        });
      },
      onDone: (citations) => {
        setMessages((m) => {
          const next = [...m];
          const last = next[next.length - 1];
          if (last && last.role === 'assistant') {
            next[next.length - 1] = {
              ...last,
              citations,
            };
          }
          return next;
        });
        setSending(false);
      },
      onError: (err) => {
        setError(err || 'Trợ lý AI chưa phản hồi được.');
        setSending(false);
      },
    });
  }

  function send(e) {
    e?.preventDefault();
    sendPrompt(input);
  }

  async function confirmClearHistory() {
    setClearing(true);
    try {
      await api.clearChatHistory();
      setMessages([]);
      setConfirmClearOpen(false);
    } catch {
      setError('Không thể xóa lịch sử trò chuyện.');
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-7.5rem)] max-w-3xl flex-col md:h-[calc(100vh-5rem)]">
      <header className="mb-3 flex shrink-0 items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Trợ lý AI</h1>
          <p className="text-sm text-muted">
            Tư vấn dinh dưỡng cá nhân hóa dựa trên hồ sơ và lộ trình của bạn.
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={() => setConfirmClearOpen(true)}
            className="flex items-center gap-1.5 rounded-xl border border-danger-soft bg-white/80 px-3.5 py-1.5 text-xs font-semibold text-danger hover:bg-danger-soft transition-colors shadow-whisper"
            title="Xóa lịch sử chat"
          >
            <Trash2 size={14} />
            Xóa lịch sử
          </button>
        )}
      </header>

      {/* Khung chứa tin nhắn với Viền Gradient Glassmorphic Sang trọng (Luxurious Aura Ring) */}
      <div className="relative flex-1 min-h-0 rounded-3xl p-[1.5px] bg-gradient-to-b from-accent-strong/40 via-emerald-500/20 to-accent-soft/40 shadow-[0_20px_50px_rgba(16,185,129,0.1),0_4px_20px_rgba(0,0,0,0.05)]">
        <div className="flex h-full flex-col space-y-4 overflow-y-auto rounded-[22.5px] bg-white/95 p-5 pt-6 backdrop-blur-xl md:p-6 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-black/15 hover:[&::-webkit-scrollbar-thumb]:bg-black/30">
          {messages.length === 0 && !sending && (
            <div className="flex h-full flex-col items-center justify-center p-4 text-center">
              <span className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-soft to-emerald-100 text-accent-strong shadow-whisper border border-accent/20">
                <Bot size={32} />
              </span>
              <h2 className="font-display text-lg font-bold text-ink">Xin chào! Tôi có thể giúp gì cho dinh dưỡng của bạn?</h2>
              <p className="mt-1 max-w-md text-xs text-muted">
                Bấm chọn nhanh câu hỏi gợi ý bên dưới hoặc tự nhập thắc mắc của bạn để bắt đầu.
              </p>

              {/* Quick Suggestion Chips nổi bật sắc nét */}
              <div className="mt-6 flex flex-wrap justify-center gap-2.5 max-w-xl">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => sendPrompt(prompt)}
                    className="flex items-center gap-2 rounded-xl border border-accent/30 bg-white/90 px-4 py-2.5 text-xs font-semibold text-accent-strong shadow-whisper transition-all duration-short hover:scale-[1.02] hover:bg-accent-soft/80 hover:border-accent-strong hover:shadow-card active:scale-100"
                  >
                    <Sparkles size={14} className="shrink-0 text-accent-strong" />
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => {
            const isWaitingFirstToken = sending && i === messages.length - 1 && m.role === 'assistant' && !m.content;
            if (isWaitingFirstToken) {
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent-strong border border-accent/20">
                    <Bot size={16} />
                  </span>
                  <span className="flex items-center gap-1 rounded-2xl bg-paper-2 px-4 py-3 shadow-whisper border border-black/5" aria-label="Đang soạn câu trả lời">
                    <Dot delay="0ms" /><Dot delay="150ms" /><Dot delay="300ms" />
                  </span>
                </div>
              );
            }
            if (m.role === 'assistant' && !m.content) return null;
            return <Bubble key={i} role={m.role} content={m.content} citations={m.citations} />;
          })}

          <div ref={endRef} />
        </div>
      </div>

      {error && (
        <p className="mt-2 rounded-lg bg-danger-soft px-3.5 py-2 text-xs font-medium text-danger">{error}</p>
      )}

      {/* Input controls hợp nhất với Viền Gradient Sang trọng */}
      <form onSubmit={send} className="mt-3.5 flex items-center gap-2 rounded-2xl p-[1.5px] bg-gradient-to-r from-accent-strong/40 via-emerald-400/25 to-accent-strong/40 shadow-card shrink-0">
        <div className="flex w-full items-center gap-2 rounded-[14px] bg-white/95 p-1.5 pl-4 backdrop-blur-md">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Nhập câu hỏi của bạn…"
            disabled={sending}
            className="min-w-0 flex-1 bg-transparent py-2 text-sm text-ink outline-none placeholder:text-muted disabled:cursor-not-allowed disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className={[
              'flex h-10 items-center gap-2 rounded-xl bg-gradient-to-r from-accent-strong to-emerald-600 px-5 text-sm font-semibold text-white shadow-whisper',
              'transition-all duration-short ease-out',
              'hover:shadow-card hover:scale-[1.02] active:scale-[0.98]',
              'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:shadow-whisper disabled:hover:scale-100',
            ].join(' ')}
          >
            <Send size={15} />
            <span className="hidden sm:inline">{sending ? 'Đang gửi…' : 'Gửi'}</span>
          </button>
        </div>
      </form>

      {/* Modal xác nhận xóa lịch sử trò chuyện */}
      <Modal
        open={confirmClearOpen}
        onClose={() => !clearing && setConfirmClearOpen(false)}
        icon={<Trash2 size={20} />}
        tone="danger"
        title="Xóa lịch sử trò chuyện"
        footer={
          <>
            <Btn variant="ghost" onClick={() => setConfirmClearOpen(false)} disabled={clearing}>
              Hủy bỏ
            </Btn>
            <Btn variant="danger" onClick={confirmClearHistory} disabled={clearing}>
              {clearing ? 'Đang xóa…' : 'Xóa tất cả'}
            </Btn>
          </>
        }
      >
        <p className="text-ink-2">
          Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện này không? Hành động này không thể hoàn tác.
        </p>
      </Modal>
    </div>
  );
}

function Dot({ delay }) {
  return (
    <span
      className="h-1.5 w-1.5 rounded-full bg-muted animate-bounce motion-reduce:animate-none"
      style={{ animationDelay: delay, animationDuration: '900ms' }}
    />
  );
}

function Bubble({ role, content, citations }) {
  const isUser = role === 'user';
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={[
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-whisper',
          isUser ? 'bg-gradient-to-r from-accent-strong to-emerald-600 text-white' : 'bg-accent-soft text-accent-strong border border-accent/20',
        ].join(' ')}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`min-w-0 max-w-[85%] sm:max-w-[80%] ${isUser ? 'items-end' : ''}`}>
        <div
          className={[
            'whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed [overflow-wrap:anywhere] shadow-whisper',
            isUser
              ? 'rounded-tr-xs bg-gradient-to-r from-accent-strong to-emerald-600 text-white font-medium'
              : 'rounded-tl-xs bg-paper-2 text-ink border border-black/5',
          ].join(' ')}
        >
          {content}
        </div>
        {!isUser && citations?.length > 0 && <Citations items={citations} />}
      </div>
    </div>
  );
}

function Citations({ items }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className={[
          'flex min-h-9 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium',
          'transition-colors duration-short ease-out',
          'text-muted hover:bg-accent-soft hover:text-accent-strong active:bg-accent-soft',
          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          open && 'bg-accent-soft text-accent-strong',
        ].filter(Boolean).join(' ')}
      >
        <BookOpenText size={13} />
        {items.length} tài liệu tham khảo
        <ChevronDown
          size={13}
          className={`transition-transform duration-short ease-in-out ${open ? 'rotate-180' : ''}`}
        />
      </button>

      <div
        className="grid transition-[grid-template-rows] duration-short ease-out"
        style={{ gridTemplateRows: open ? '1fr' : '0fr' }}
      >
        <ul className="min-h-0 space-y-1 overflow-hidden">
          {items.map((c, i) => {
            const title = c.title ?? c.source ?? c.name ?? (typeof c === 'string' ? c : `Tài liệu ${i + 1}`);
            const url = c.url ?? c.link;
            const snippet = c.snippet ?? c.excerpt;
            return (
              <li key={i} className="mt-1 rounded-xl bg-white p-3 shadow-whisper border border-black/5">
                <div className="flex items-start justify-between gap-2">
                  <p className="min-w-0 text-xs font-semibold text-ink [overflow-wrap:anywhere]">
                    <span className="mr-1.5 text-accent-strong [font-variant-numeric:tabular-nums]">[{i + 1}]</span>
                    {title}
                  </p>
                  {url && (
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`Mở nguồn: ${title}`}
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm text-muted transition-colors duration-short ease-out hover:bg-accent-soft hover:text-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus"
                    >
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
                {snippet && <p className="mt-1 text-xs leading-relaxed text-muted">{snippet}</p>}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}