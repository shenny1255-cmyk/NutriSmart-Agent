// Khung dùng chung cho Login/Register — nền trang trí SVG tự dựng (Tier B hand-built)
// chủ đề dinh dưỡng: lá + hạt hữu cơ, tint mint nhạt, không dùng ảnh stock.
// Mọi màu qua Tailwind fill-*/text-* → token, không inline OKLCH.

export default function AuthLayout({ children }) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-x-clip bg-paper p-4 py-10">
      {/* Nền trang trí — ẩn với screen reader, không bắt sự kiện chuột */}
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 h-full w-full"
        preserveAspectRatio="xMidYMid slice"
        viewBox="0 0 1200 800"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Lá lớn — góc trên trái, xoay nhẹ tạo bất đối xứng */}
        <g className="fill-accent-soft" transform="translate(-60 -80) rotate(-18)">
          <path d="M170 240 C 170 120, 260 40, 380 40 C 380 160, 290 240, 170 240 Z" />
          <path d="M175 235 C 235 175, 300 110, 372 48" className="fill-none stroke-accent/20" strokeWidth="3" strokeLinecap="round" />
        </g>

        {/* Lá nhỏ — góc dưới phải */}
        <g className="fill-accent-soft" transform="translate(1050 640) rotate(150)">
          <path d="M0 160 C 0 70, 70 0, 160 0 C 160 90, 90 160, 0 160 Z" />
          <path d="M4 156 C 50 110, 100 60, 154 6" className="fill-none stroke-accent/20" strokeWidth="2.5" strokeLinecap="round" />
        </g>

        {/* Cành hạt — cạnh phải trên, nét mảnh */}
        <g className="stroke-accent/25 fill-none" strokeWidth="2.5" strokeLinecap="round" transform="translate(1010 90) rotate(24)">
          <path d="M0 140 C 20 90, 30 45, 32 0" />
          <ellipse cx="10" cy="96" rx="9" ry="14" transform="rotate(-32 10 96)" className="fill-accent/15 stroke-none" />
          <ellipse cx="22" cy="56" rx="8" ry="13" transform="rotate(-20 22 56)" className="fill-accent/15 stroke-none" />
          <ellipse cx="30" cy="18" rx="7" ry="11" transform="rotate(-10 30 18)" className="fill-accent/15 stroke-none" />
        </g>

        {/* Vài hạt rời — dưới trái, nhịp lẻ */}
        <g className="fill-accent/10">
          <circle cx="150" cy="620" r="10" />
          <circle cx="196" cy="672" r="6" />
          <circle cx="120" cy="690" r="7" />
        </g>
      </svg>

      {/* Nội dung form nổi trên nền */}
      <div className="relative z-base w-full">{children}</div>
    </div>
  );
}
