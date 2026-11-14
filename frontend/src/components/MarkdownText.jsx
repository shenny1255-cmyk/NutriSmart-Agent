// Hiển thị câu trả lời của trợ lý AI dạng markdown gọn (đậm, nghiêng, danh sách, tiêu đề, đoạn).
// Dựng phần tử React trực tiếp - KHÔNG dùng dangerouslySetInnerHTML nên không lo chèn HTML.
// Chịu được văn bản đang stream dở: dấu ** chưa đóng sẽ bị ẩn thay vì hiện ra.

const INLINE = /(\*\*[^*\n]+?\*\*|__[^_\n]+?__|`[^`\n]+`|\*[^*\s\n][^*\n]*?\*)/g;

function cleanText(text) {
  // Dấu gạch ngang dài → gạch thường; ** lẻ (chưa đóng khi đang stream) → bỏ
  return text.replace(/[—–]/g, '-').replace(/\*\*/g, '').replace(/(^|\s)\*(\s|$)/g, '$1$2');
}

function renderInline(text, keyBase) {
  const out = [];
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push(cleanText(text.slice(last, m.index)));
    const tok = m[0];
    const key = `${keyBase}-${i++}`;
    if (tok.startsWith('**') || tok.startsWith('__')) {
      out.push(<strong key={key} className="font-semibold text-ink">{cleanText(tok.slice(2, -2))}</strong>);
    } else if (tok.startsWith('`')) {
      out.push(<code key={key} className="rounded bg-paper-3 px-1 py-0.5 text-[0.85em]">{tok.slice(1, -1)}</code>);
    } else {
      out.push(<em key={key}>{cleanText(tok.slice(1, -1))}</em>);
    }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(cleanText(text.slice(last)));
  return out;
}

const BULLET = /^(\s*)[-*+•]\s+(.*)$/;
const NUMBER = /^(\s*)(\d+)[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;

// Gom các dòng thành khối: đoạn văn, danh sách, tiêu đề
function toBlocks(text) {
  const blocks = [];
  let para = [];
  let list = null;
  const flushPara = () => { if (para.length) { blocks.push({ type: 'p', lines: para }); para = []; } };
  const flushList = () => { if (list) { blocks.push(list); list = null; } };

  for (const raw of text.replace(/\r/g, '').split('\n')) {
    const line = raw.replace(/\s+$/, '');
    let m;
    if (!line.trim()) { flushPara(); flushList(); continue; }
    if ((m = line.match(HEADING))) { flushPara(); flushList(); blocks.push({ type: 'h', text: m[1] }); continue; }
    if ((m = line.match(BULLET)) || (m = line.match(NUMBER))) {
      const ordered = m.length === 4;
      const indent = m[1].length >= 2 ? 1 : 0;
      const body = ordered ? m[3] : m[2];
      flushPara();
      if (!list || list.ordered !== ordered) { flushList(); list = { type: 'list', ordered, items: [] }; }
      list.items.push({ text: body, indent, num: ordered ? m[2] : null });
      continue;
    }
    if (list && /^\s{2,}/.test(raw)) {           // dòng nối tiếp của mục danh sách
      list.items[list.items.length - 1].text += ` ${line.trim()}`;
      continue;
    }
    flushList();
    para.push(line.trim());
  }
  flushPara();
  flushList();
  return blocks;
}

export default function MarkdownText({ text }) {
  if (!text) return null;
  const blocks = toBlocks(text);
  return (
    <div className="space-y-2.5">
      {blocks.map((b, bi) => {
        if (b.type === 'h') {
          return <p key={bi} className="font-display font-semibold text-ink">{renderInline(b.text, `h${bi}`)}</p>;
        }
        if (b.type === 'list') {
          const Tag = b.ordered ? 'ol' : 'ul';
          return (
            <Tag key={bi} className="space-y-1.5">
              {b.items.map((it, ii) => (
                <li key={ii} className={`flex gap-2 ${it.indent ? 'pl-5' : ''}`}>
                  <span className="shrink-0 select-none font-semibold text-accent-strong" aria-hidden="true">
                    {b.ordered ? `${it.num}.` : '•'}
                  </span>
                  <span className="min-w-0">{renderInline(it.text, `l${bi}-${ii}`)}</span>
                </li>
              ))}
            </Tag>
          );
        }
        return (
          <p key={bi}>
            {b.lines.map((ln, li) => (
              <span key={li}>
                {li > 0 && <br />}
                {renderInline(ln, `p${bi}-${li}`)}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
