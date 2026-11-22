import { Platform } from 'react-native';

/** Brand palette — "Coffee & Paper". Change values here to re-skin the whole app. */
export const palette = {
  deepCoffee: '#4E2E20',
  espresso: '#604536',
  mocha: '#86634D',
  cocoa: '#AA8A76',
  lightMocha: '#CEB5A3',
  latte: '#D4BAA6',
  sand: '#E9D8C5',
  paperBeige: '#E9DACB',
  linen: '#F2E1D0',
  offWhite: '#F3E6D8',
  cream: '#F7EEE4',
  greyBrown: '#716357',
  warmGrey: '#8F7F71',
  warmGreyDeep: '#5E5347',
  rust: '#8C4A36',
} as const;

export const colors = {
  background: palette.paperBeige,
  surface: palette.offWhite,
  surfaceMuted: palette.paperBeige,
  border: palette.mocha,
  borderStrong: palette.espresso,
  stitch: palette.latte,
  textPrimary: palette.deepCoffee,
  textSecondary: palette.espresso,
  textMuted: palette.greyBrown,
  textOnDark: palette.cream,
  primaryButton: palette.warmGrey,
  primaryButtonEdge: palette.warmGreyDeep,
  primaryButtonText: palette.cream,
  secondaryButton: palette.sand,
  secondaryButtonText: palette.deepCoffee,
  inputBackground: palette.paperBeige,
  inputBorder: palette.mocha,
  inputBorderFocused: palette.deepCoffee,
  placeholder: palette.greyBrown,
  icon: palette.greyBrown,
  pill: palette.sand,
  questionPanel: palette.deepCoffee,
  questionText: palette.offWhite,
  answerCard: palette.latte,
  answerCardAlt: palette.paperBeige,
  error: palette.rust,
  shadow: palette.deepCoffee,
  check: {
    base: palette.linen,
    stripe: palette.lightMocha,
    cross: palette.cocoa,
  },
} as const;

export const radii = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 28,
  pill: 999,
} as const;

export const spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  xxxl: 48,
} as const;

/**
 * Comic Sans MS is the brand font. It is not shipped on Android/iOS, so native builds use the
 * bundled look-alike Comic Neue; web prefers the system Comic Sans MS when present.
 */
const webStack = (weight: string) => `"Comic Sans MS", "Comic Neue", ${weight}, "Chalkboard SE", sans-serif`;

export const fontFamilies = {
  regular: Platform.select({ web: webStack('ComicNeue_400Regular'), default: 'ComicNeue_400Regular' }),
  bold: Platform.select({ web: webStack('ComicNeue_700Bold'), default: 'ComicNeue_700Bold' }),
  mono: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'ui-monospace, Menlo, Consolas, monospace' }),
} as const;

export const typography = {
  display: { fontFamily: fontFamilies.bold, fontSize: 44, lineHeight: 52 },
  h1: { fontFamily: fontFamilies.bold, fontSize: 26, lineHeight: 34 },
  h2: { fontFamily: fontFamilies.bold, fontSize: 20, lineHeight: 28 },
  body: { fontFamily: fontFamilies.regular, fontSize: 16, lineHeight: 24 },
  bodyBold: { fontFamily: fontFamilies.bold, fontSize: 16, lineHeight: 24 },
  label: { fontFamily: fontFamilies.bold, fontSize: 14, lineHeight: 20 },
  caption: { fontFamily: fontFamilies.regular, fontSize: 13, lineHeight: 18 },
  tagline: { fontFamily: fontFamilies.bold, fontSize: 16, lineHeight: 22, letterSpacing: 1.5 },
  button: { fontFamily: fontFamilies.bold, fontSize: 19, lineHeight: 26 },
  code: { fontFamily: fontFamilies.mono, fontSize: 14, lineHeight: 20 },
} as const;

export const shadows = {
  soft: {
    shadowColor: colors.shadow,
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
    elevation: 3,
  },
} as const;

export const layout = {
  screenMargin: spacing.lg,
  containerPadding: spacing.xl,
  maxContentWidth: 460,
  touchTarget: 54,
  checkCellSize: 26,
} as const;
