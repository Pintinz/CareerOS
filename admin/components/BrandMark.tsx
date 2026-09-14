import Image from "next/image";

// Official CareerOS artwork, cut from the brand board by mobile/tool/generate_brand_assets.py.
const SYMBOL_ASPECT = 522 / 457;
const WORDMARK_ASPECT = 795 / 136;

/** CareerOS symbol (C + rising ribbon arrow + spark), `size` px tall. */
export function BrandMark({ size = 32, onDark = false, decorative = false }: { size?: number; onDark?: boolean; decorative?: boolean }) {
  return (
    <Image
      src={onDark ? "/brand/careeros-symbol-on-dark.png" : "/brand/careeros-symbol.png"}
      alt={decorative ? "" : "CareerOS"}
      width={Math.round(size * SYMBOL_ASPECT)}
      height={size}
      unoptimized
      priority
    />
  );
}

/** Primary horizontal logo, proportioned like the brand board, with an optional suffix ("Admin"). */
export function BrandLockup({ onDark = false, suffix, size = 40 }: { onDark?: boolean; suffix?: string; size?: number }) {
  const wordmarkHeight = Math.round(size * 0.41);
  return (
    <span className="inline-flex items-start" aria-label={suffix ? `CareerOS ${suffix}` : "CareerOS"} role="img">
      <BrandMark size={size} onDark={onDark} decorative />
      <span className="inline-flex items-center" style={{ marginTop: size * 0.37, marginLeft: -size * 0.046 }}>
        <Image
          src={onDark ? "/brand/careeros-wordmark-on-dark.png" : "/brand/careeros-wordmark.png"}
          alt=""
          width={Math.round(wordmarkHeight * WORDMARK_ASPECT)}
          height={wordmarkHeight}
          unoptimized
          priority
        />
        {suffix && (
          <span className={`ml-2 text-sm font-semibold leading-none ${onDark ? "text-white/60" : "text-muted"}`}>{suffix}</span>
        )}
      </span>
    </span>
  );
}
