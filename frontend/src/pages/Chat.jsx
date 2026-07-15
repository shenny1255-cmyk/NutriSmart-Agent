import { useEffect, useRef, useState } from 'react';
import { Send, Bot, User } from 'lucide-react';
import { api } from '../lib/api.js';

export default function Chat() {
  const [messages, setMessages] = useState([]);   // { role, content }
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  // Tải lịch sử trò chuyện khi mở trang
  useEffect(() => {
    api.chatHistory()
      .then((rows) => setMessages(rows.map((m) => ({ role: m.role, content: m.content }))))
      .catch(() => {});   // chưa có lịch sử / backend chưa chạy → để trống
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
      const { reply } = await api.chat(text);
      setMessages((m) => [...m, { role: 'assistant', content: reply }]);
    } catch {
      setError('Trợ lý AI chưa phản hồi được. Kiểm tra Ollama đang chạy rồi thử lại.');
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-3xl flex-col">
      <header className="mb-4">
        <h1 className="text-2xl font-bold">Trợ lý AI</h1>
        <p className="text-sm text-slate-500">
          Tư vấn dinh dưỡng cá nhân hóa dựa trên hồ sơ và lộ trình của bạn.
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-slate-200 bg-white p-5">
        {messages.length === 0 && !sending && (
          <div className="flex h-full flex-col items-center justify-center text-center text-slate-400">
            <Bot size={40} className="mb-2 text-emerald-500" />
            <p className="text-sm">Hãy hỏi tôi bất cứ điều gì về ăn uống của bạn.</p>
            <p className="mt-1 text-xs">Ví dụ: “Tối nay tôi nên ăn gì?”</p>
          </div>
        )}

        {messages.map((m, i) => (
          <Bubble key={i} role={m.role} content={m.content} />
        ))}

        {sending && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Bot size={18} className="text-emerald-500" />
            <span className="animate-pulse">Đang soạn câu trả lời…</span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {error && <p className="mt-2 text-sm text-amber-600">{error}</p>}

      <form onSubmit={send} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Nhập câu hỏi của bạn…"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm outline-none focus:border-emerald-500"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send size={16} />
          Gửi
        </button>
      </form>
    </div>
  );
}

function Bubble({ role, content }) {
  const isUser = role === 'user';
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? 'bg-slate-200 text-slate-600' : 'bg-emerald-100 text-emerald-700'
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div
        className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
          isUser
            ? 'bg-emerald-600 text-white'
            : 'bg-slate-100 text-slate-800'
        }`}
      >
        {content}
      </div>
    </div>
  );
}
