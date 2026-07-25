import { useEffect, useRef, useState } from 'react';
import { Send, Bot, User, BookOpenText, ChevronDown, ExternalLink } from 'lucide-react';
import { api } from '../lib/api.js';

export default function Chat() {
  const [messages, setMessages] = useState([]);   // { role, content, citations? }
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  // Tải lịch sử trò chuyện khi mở trang
  useEffect(() => {
    api.chatHistory()
      .then((rows) => setMessages(rows.map((m) => ({
        role: m.role,
        content: m.content,
        citations: m.citations,   // nếu backend trả kèm nguồn trích dẫn
      }))))
      .catch(() => { });   // chưa có lịch sử / backend chưa chạy → để trống
  }, []);

  // Tự cuộn xuống tin nhắn mới nhất
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  async function send(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setError(null);
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);   // hiện ngay
    setSending(true);

    try {
      const { reply, citations } = await api.chat(text);
      setMessages((m) => [...m, { role: 'assistant', content: reply, citations }]);
    } catch {
      setError('Trợ lý AI chưa phản hồi được. Kiểm tra Ollama đang chạy rồi thử lại.');
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-6.5rem)] max-w-3xl flex-col md:h-[calc(100vh-4rem)]">
      <header className="mb-4">
        <h1 className="font-display text-2xl font-bold tracking-tight">Trợ lý AI</h1>
        <p className="text-sm text-muted">
          Tư vấn dinh dưỡng cá nhân hóa dựa trên hồ sơ và lộ trình của bạn.
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-md bg-paper-2 p-4 shadow-hairline md:p-5">
        {messages.length === 0 && !sending && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <span className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
              <Bot size={26} />
            </span>
            <p className="text-sm font-medium text-ink-2">Hãy hỏi tôi bất cứ điều gì về ăn uống của bạn.</p>
            <p className="mt-1 text-xs text-muted">Ví dụ: “Tối nay tôi nên ăn gì?”</p>
          </div>
        )}

        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} content={m.content} citations={m.citations} />
        ))}

        {sending && (
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent-strong">
              <Bot size={16} />
            </span>
            <span className="flex items-center gap-1 rounded-md bg-paper-3 px-4 py-3" aria-label="Đang soạn câu trả lời">
              <Dot delay="0ms" /><Dot delay="150ms" /><Dot delay="300ms" />
            </span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {error && (
        <p className="mt-2 rounded-sm bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <form onSubmit={send} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Nhập câu hỏi của bạn…"
          disabled={sending}
          className={[
            'min-h-11 min-w-0 flex-1 rounded-sm bg-paper-2 px-4 py-2 text-sm text-ink shadow-hairline',
            'placeholder:text-muted transition-[box-shadow,background-color] duration-short ease-out',
            'hover:bg-paper-3 focus:bg-paper-2',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus',
            'disabled:cursor-not-allowed disabled:opacity-60',
          ].join(' ')}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className={[
            'flex min-h-11 items-center gap-2 rounded-sm bg-accent-strong px-4 py-2 text-sm font-medium text-accent-ink shadow-whisper',
            'transition-[background-color,transform,box-shadow,opacity] duration-short ease-out',
            'hover:-translate-y-px hover:shadow-card active:translate-y-0 active:shadow-whisper',
            'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
            'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-whisper',
          ].join(' ')}
        >
          <Send size={16} />
          <span className="hidden sm:inline">Gửi</span>
        </button>
      </form>
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
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-paper-3 text-ink-2' : 'bg-accent-soft text-accent-strong',
        ].join(' ')}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={`min-w-0 max-w-[85%] sm:max-w-[80%] ${isUser ? 'items-end' : ''}`}>
        <div
          className={[
            'whitespace-pre-wrap rounded-md px-4 py-2.5 text-sm leading-relaxed [overflow-wrap:anywhere]',
            isUser
              ? 'rounded-br-sm bg-accent-strong text-accent-ink'
              : 'rounded-bl-sm bg-paper-3 text-ink',
          ].join(' ')}
        >
          {content}
        </div>
        {!isUser && citations?.length > 0 && <Citations items={citations} />}
      </div>
    </div>
  );
}

// Nguồn trích dẫn y khoa — thu gọn/mở rộng, animate grid-rows (không animate height)
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
              <li key={i} className="mt-1 rounded-sm bg-paper-2 p-3 shadow-hairline">
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