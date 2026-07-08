// MerQato / KAPWA design language — extracted palette, typography and tokens.
// Used by both the Tailwind theme (globals.css) and server/client code that
// needs hex values (charts, inline styles, PDFs, emails).

export const palette = {
  sandstone: "#D7C4A5",
  limestone: "#EBDCC7",
  desertSand: "#CBB0BA",
  charcoal: "#2D2828",
  basalt: "#1B1A18",
  bronze: "#8A6A43",
  forest: "#435347",
  warmWhite: "#F7F2EA",
} as const;

export type PaletteKey = keyof typeof palette;

export const fonts = {
  serif: '"Cormorant Garamond", Georgia, serif',
  sans: '"Montserrat", Arial, sans-serif',
} as const;

// Semantic tokens mapped to CSS variables defined in globals.css.
export const brand = {
  bg: palette.warmWhite,
  surface: palette.limestone,
  text: palette.charcoal,
  muted: palette.bronze,
  accent: palette.forest,
  border: palette.sandstone,
  danger: "#9B4A3A",
} as const;

export const brandWordmark = "MERQATO";
export const brandTagline = "AI RESORT WEBSITE";
