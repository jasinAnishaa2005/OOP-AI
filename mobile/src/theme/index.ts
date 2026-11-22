import { colors, fontFamilies, layout, palette, radii, shadows, spacing, typography } from './tokens';

export const theme = { palette, colors, radii, spacing, typography, fontFamilies, shadows, layout } as const;
export type Theme = typeof theme;
export type TypographyVariant = keyof typeof typography;
export { colors, fontFamilies, layout, palette, radii, shadows, spacing, typography };
