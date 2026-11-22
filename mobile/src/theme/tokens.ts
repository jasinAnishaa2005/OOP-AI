import { Platform } from 'react-native';

/** Brand palette — "Coffee & Paper". Change values here to re-skin the whole app. */
export const palette = {
  deepCoffee: '#493326',
  espresso: '#604536',
  mocha: '#806653',
  lightMocha: '#B8A58F',
  latte: '#C5B6A3',
  warmGrey: '#A9A69F',
  checkGrey: '#D1CEC6',
  paperBeige: '#E9E4D9',
  offWhite: '#F0ECE3',
  rust: '#8C4A36',
} as const;

export const colors = {
  background: palette.paperBeige,
  surface: palette.offWhite,
  surfaceMuted: palette.paperBeige,
  border: palette.lightMocha,
  borderStrong: palette.mocha,
  stitch: palette.mocha,
  textPrimary: palette.deepCoffee,
  textSecondary: palette.espresso,
  textMuted: palette.mocha,
  textOnDark: palette.offWhite,
  primaryButton: palette.warmGrey,
  primaryButtonText: palette.deepCoffee,
  secondaryButton: palette.paperBeige,
  secondaryButtonText: palette.espresso,
  inputBackground: palette.paperBeige,
  inputBorder: palette.latte,
  inputBorderFocused: palette.mocha,
  placeholder: palette.warmGrey,
  questionPanel: palette.deepCoffee,
  questionText: palette.offWhite,
  answerCard: palette.latte,
  answerCardAlt: palette.paperBeige,
  error: palette.rust,
  shadow: palette.deepCoffee,
  check: {
    base: palette.offWhite,
    stripe: palette.lightMocha,
    stripeAlt: palette.checkGrey,
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
  display: { fontFamily: fontFamilies.bold, fontSize: 34, lineHeight: 42, letterSpacing: 1 },
  h1: { fontFamily: fontFamilies.bold, fontSize: 26, lineHeight: 34 },
  h2: { fontFamily: fontFamilies.bold, fontSize: 20, lineHeight: 28 },
  body: { fontFamily: fontFamilies.regular, fontSize: 16, lineHeight: 24 },
  bodyBold: { fontFamily: fontFamilies.bold, fontSize: 16, lineHeight: 24 },
  label: { fontFamily: fontFamilies.bold, fontSize: 14, lineHeight: 20 },
  caption: { fontFamily: fontFamilies.regular, fontSize: 13, lineHeight: 18 },
  tagline: { fontFamily: fontFamilies.bold, fontSize: 13, lineHeight: 18, letterSpacing: 3 },
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
  screenMargin: spacing.xl,
  containerPadding: spacing.xl,
  maxContentWidth: 480,
  touchTarget: 52,
  checkCellSize: 28,
} as const;
