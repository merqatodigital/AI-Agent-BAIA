import * as React from "react";

/**
 * KAPWA / MerQato logomark — the four-arm "shared self" cross.
 * Rendered as inline SVG using `currentColor` so it inherits text color
 * (e.g. charcoal on light, warmwhite on dark).
 */
export function Logo({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      role="img"
      aria-label="MerQato logo"
      className={className}
      fill="currentColor"
    >
      <g transform="translate(24 24)">
        <ellipse cx="0" cy="-11" rx="5" ry="11" />
        <ellipse cx="0" cy="-11" rx="5" ry="11" transform="rotate(90)" />
        <ellipse cx="0" cy="-11" rx="5" ry="11" transform="rotate(180)" />
        <ellipse cx="0" cy="-11" rx="5" ry="11" transform="rotate(270)" />
        <circle cx="0" cy="0" r="6.5" />
      </g>
    </svg>
  );
}

/** Full lockup: logomark + MERQATO wordmark + tagline. */
export function Wordmark({
  size = 40,
  showTagline = true,
  className,
}: {
  size?: number;
  showTagline?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex items-center gap-3 ${className ?? ""}`}>
      <Logo size={size} className="text-accent" />
      <div className="leading-none">
        <div className="font-serif text-2xl font-semibold tracking-tight text-ink">
          MERQATO
        </div>
        {showTagline && (
          <div className="eyebrow mt-1 text-[0.62rem]">AI Resort Website</div>
        )}
      </div>
    </div>
  );
}
