import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import { LogoMark } from '../components/Logo.jsx';

// Phiên bản chính sách - phải khớp CONSENT_VERSION ở backend/app/services/consent.py.
// Đổi nội dung (thêm mục đích xử lý, thêm bên nhận dữ liệu...) → tăng phiên bản.
export const POLICY_VERSION = '1.0';
export const POLICY_DATE = '17/11/2026';

const SECTIONS = [
  {
    title: '1. NutriSmart là gì và ai xử lý dữ liệu của bạn',
    body: [
      'NutriSmart là sản phẩm đồ án tốt nghiệp của Nhóm E15, hỗ trợ theo dõi dinh dưỡng và gợi ý thực đơn. NutriSmart không phải dịch vụ y tế và không thay thế chẩn đoán hay tư vấn của bác sĩ.',
      'Nhóm E15 là bên quyết định mục đích và cách thức xử lý dữ liệu cá nhân của bạn trong ứng dụng.',
    ],
  },
  {
    title: '2. Dữ liệu chúng tôi thu thập',
    list: [
      'Tài khoản: họ tên, email, mật khẩu (chỉ lưu dạng mã hóa một chiều, không ai đọc được).',
      'Hồ sơ sức khỏe: giới tính, ngày sinh, chiều cao, cân nặng, mức vận động, mục tiêu, bệnh nền, dị ứng. Đây là dữ liệu cá nhân nhạy cảm theo Nghị định 13/2023/NĐ-CP.',
      'Dữ liệu bạn tạo khi dùng app: nhật ký bữa ăn, vận động, cân nặng, check-in lộ trình, tin nhắn với trợ lý AI, ảnh món ăn bạn tải lên, số bước chân đồng bộ từ ứng dụng di động (nếu dùng).',
    ],
  },
  {
    title: '3. Chúng tôi dùng dữ liệu để làm gì',
    list: [
      'Tính mục tiêu calo hằng ngày và chỉ số BMI.',
      'Sinh, theo dõi và điều chỉnh lộ trình dinh dưỡng theo chu kỳ.',
      'Trả lời câu hỏi của bạn bằng trợ lý AI, dựa trên tài liệu đã được chuyên gia duyệt.',
      'Cảnh báo an toàn: món có chất bạn dị ứng, món không phù hợp bệnh nền, khẩu phần quá thấp hoặc quá cao.',
      'Ước lượng dinh dưỡng từ ảnh món ăn.',
    ],
    after: 'Chúng tôi không bán dữ liệu, không dùng cho quảng cáo và không chia sẻ cho bên thứ ba nào ngoài nhà cung cấp AI nêu ở mục 4 (chỉ khi bạn đồng ý).',
  },
  {
    title: '4. AI nội bộ và AI đám mây',
    list: [
      'AI nội bộ: mô hình chạy trên máy chủ của NutriSmart, dữ liệu không rời khỏi máy chủ. Câu trả lời chậm hơn.',
      'AI đám mây (Google Gemini) - CHỈ khi bạn đồng ý: trước khi gửi, hệ thống tự xóa họ tên, email, số điện thoại và đổi tuổi chính xác thành khoảng tuổi (ví dụ 25-34). Bệnh nền, dị ứng, chiều cao, cân nặng vẫn được gửi vì AI cần chúng để tư vấn đúng.',
      'Phân tích ảnh món ăn luôn cần AI đám mây: ảnh được gửi tới Google Gemini, không kèm hồ sơ sức khỏe. Nếu bạn chọn chỉ dùng AI nội bộ, tính năng này tạm khóa; bạn vẫn ghi bữa ăn thủ công được.',
      'Mỗi lần dữ liệu được gửi ra AI đám mây đều được ghi vào nhật ký kiểm toán (thời điểm, mục đích, loại dữ liệu đã ẩn).',
      'Lưu ý từ Google: với gói miễn phí của Gemini API, Google có thể dùng nội dung gửi lên để cải thiện sản phẩm của họ; với gói trả phí thì không. Vì vậy hệ thống luôn ẩn danh trước khi gửi.',
    ],
  },
  {
    title: '5. Lưu trữ và bảo vệ',
    list: [
      'Dữ liệu lưu trong cơ sở dữ liệu PostgreSQL trên máy chủ của nhóm; chỉ tài khoản quản trị và chuyên gia được phân quyền mới truy cập được phần cần cho công việc.',
      'Dữ liệu được giữ đến khi tài khoản bị xóa.',
    ],
  },
  {
    title: '6. Quyền của bạn',
    list: [
      'Xem và sửa hồ sơ, bệnh nền, dị ứng bất cứ lúc nào trong trang Hồ sơ.',
      'Rút lại đồng ý gửi dữ liệu tới AI đám mây: bật "Chỉ xử lý bằng AI nội bộ" trong Hồ sơ. Việc rút lại có hiệu lực ngay và không ảnh hưởng tới dữ liệu đã xử lý trước đó.',
      'Yêu cầu xóa tài khoản và toàn bộ dữ liệu: liên hệ quản trị viên NutriSmart.',
      'Mỗi lần bạn đồng ý hoặc rút lại đều được lưu kèm thời điểm và phiên bản chính sách.',
    ],
  },
];

export default function Privacy() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-paper px-4 py-8 sm:py-12">
      <article className="mx-auto max-w-3xl rounded-md bg-paper-2 p-6 shadow-card sm:p-10">
        <button type="button" onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
          className="mb-6 inline-flex items-center gap-2 rounded-sm text-sm font-medium text-ink-2 hover:text-accent-strong focus-visible:outline focus-visible:outline-2 focus-visible:outline-focus">
          <ArrowLeft size={16} aria-hidden="true" />Quay lại
        </button>
        <header className="mb-8 flex items-start gap-4">
          <LogoMark size={44} />
          <div>
            <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Chính sách quyền riêng tư</h1>
            <p className="mt-1 text-sm text-muted">Phiên bản {POLICY_VERSION} - áp dụng từ {POLICY_DATE}</p>
          </div>
        </header>

        <div className="mb-8 flex gap-3 rounded-sm bg-accent-soft p-4 text-sm text-ink-2">
          <ShieldCheck size={20} className="mt-0.5 shrink-0 text-accent-strong" aria-hidden="true" />
          <p>Tóm tắt: dữ liệu sức khỏe chỉ dùng để tư vấn dinh dưỡng cho chính bạn. Dữ liệu chỉ được gửi ra AI đám mây
            (Google Gemini) khi bạn đồng ý, và luôn được ẩn danh trước. Bạn đổi lựa chọn được bất cứ lúc nào trong Hồ sơ.</p>
        </div>

        <div className="space-y-7">
          {SECTIONS.map((s) => (
            <section key={s.title}>
              <h2 className="mb-2 font-display text-lg font-bold text-ink">{s.title}</h2>
              {s.body?.map((p) => <p key={p} className="mb-2 text-base leading-relaxed text-ink-2">{p}</p>)}
              {s.list && (
                <ul className="list-disc space-y-1.5 pl-5 text-base leading-relaxed text-ink-2">
                  {s.list.map((li) => <li key={li}>{li}</li>)}
                </ul>
              )}
              {s.after && <p className="mt-2 text-base leading-relaxed text-ink-2">{s.after}</p>}
            </section>
          ))}
        </div>

        <p className="mt-10 border-t border-rule-2 pt-5 text-sm text-muted">
          Căn cứ: Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân.{' '}
          <Link to="/register" className="font-medium text-accent-strong underline underline-offset-2">Về trang đăng ký</Link>
        </p>
      </article>
    </div>
  );
}
