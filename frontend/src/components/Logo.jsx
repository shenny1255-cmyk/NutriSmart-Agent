// Logo mark NutriSmart Agent — bubble chat (AI agent) + lá (dinh dưỡng).
// SVG tự dựng, màu qua Tailwind class → token. Cùng hình học với public/favicon.svg.

export function LogoMark({ size = 40, className = '' }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      aria-hidden="true"
      className={`shrink-0 ${className}`}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        className="fill-accent-strong"
        d="M20 5 H44 C52.837 5 60 12.163 60 21 V33 C60 41.837 52.837 49 44 49 H27 L15 59.5 V48.2 C8.6 46.1 4 40.1 4 33 V21 C4 12.163 11.163 5 20 5 Z"
      />
      <path
        className="fill-paper-2"
        d="M22 39 C22 26.5 31 17.5 43.5 17.5 C43.5 30 34.5 39 22 39 Z"
      />
      <path
        className="fill-none stroke-accent-soft"
        strokeWidth="2"
        strokeLinecap="round"
        d="M23.5 37.5 C29.5 31.5 36 25 42 19"
      />
    </svg>
  );
}

export function Logo({ size = 40, subtitle, className = '' }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <LogoMark size={size} />
      <div>
        <p className="font-display text-lg font-bold leading-tight tracking-tight text-ink">
          Nutri<span className="text-accent-strong">Smart</span>
        </p>
        {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
      </div>
    </div>
  );
}
