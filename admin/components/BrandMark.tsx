/** CareerOS pathway mark — same geometry as the mobile CareerOSMark and the brand SVG masters. */
export function BrandMark({ size = 32, onDark = false }: { size?: number; onDark?: boolean }) {
  const gradientId = onDark ? "careeros-path-dark" : "careeros-path-light";
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="CareerOS">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor={onDark ? "#249BFF" : "#1677FF"} />
          <stop offset="1" stopColor="#13BDEB" />
        </linearGradient>
      </defs>
      <path
        d="M49.5 17.5 A22 22 0 1 0 53 41"
        fill="none"
        stroke={onDark ? "#FFFFFF" : "#071A38"}
        strokeWidth={8.5}
        strokeLinecap="round"
      />
      <path d="M17 44 C 27 44, 34 38, 44.5 27.5" fill="none" stroke={`url(#${gradientId})`} strokeWidth={6.5} strokeLinecap="round" />
      <path
        d="M57 15 L 51.6 32.4 L 39.6 20.4 Z"
        fill={`url(#${gradientId})`}
        stroke={`url(#${gradientId})`}
        strokeWidth={2}
        strokeLinejoin="round"
      />
      <path d="M58 4 L59.4 7.6 L63 9 L59.4 10.4 L58 14 L56.6 10.4 L53 9 L56.6 7.6 Z" fill="#13BDEB" />
    </svg>
  );
}

/** "Career" + "OS" wordmark lockup. */
export function BrandLockup({ onDark = false, suffix }: { onDark?: boolean; suffix?: string }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <BrandMark size={30} onDark={onDark} />
      <span className="text-lg font-extrabold tracking-tight">
        <span className={onDark ? "text-white" : "text-navy"}>Career</span>
        <span className={onDark ? "text-brand-light" : "text-brand"}>OS</span>
        {suffix && <span className={`ml-1.5 font-semibold ${onDark ? "text-white/60" : "text-muted"}`}>{suffix}</span>}
      </span>
    </span>
  );
}
