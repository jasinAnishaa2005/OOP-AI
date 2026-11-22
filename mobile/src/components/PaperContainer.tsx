import { StyleSheet, View, type ViewProps } from 'react-native';

import { colors, layout, spacing, usePaperFrame, type PaperFrame } from '@/theme';

import { BookStack, Sparkle } from './Illustrations';

type Props = ViewProps & { stitched?: boolean; decorated?: boolean; frame?: PaperFrame };

/** Rounded off-white paper with a coffee outline, a dashed gingham ribbon and corner doodles. */
export function PaperContainer({ stitched = true, decorated = true, frame, style, children, ...rest }: Props) {
  const fallback = usePaperFrame();
  const f = frame ?? fallback;
  return (
    <View style={[styles.outer, { width: f.cardWidth, borderRadius: f.radius, padding: f.inset }, style]} {...rest}>
      <View
        style={[
          styles.inner,
          { borderRadius: Math.max(f.radius - f.inset, 6) },
          stitched && [styles.stitched, { borderWidth: f.ribbon }],
        ]}>
        {children}
      </View>
      {decorated && (
        <>
          <View style={[styles.sparkle, { top: f.inset + spacing.md, right: f.inset + spacing.md }]} pointerEvents="none">
            <Sparkle size={30} />
          </View>
          <View style={styles.books} pointerEvents="none">
            <BookStack width={52} />
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  outer: {
    maxWidth: layout.maxContentWidth,
    alignSelf: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.textPrimary,
    shadowColor: colors.shadow,
    shadowOpacity: 0.28,
    shadowRadius: 7,
    shadowOffset: { width: 0, height: 2 },
    elevation: 5,
  },
  inner: {
    paddingHorizontal: layout.containerPadding - spacing.sm,
    paddingTop: layout.containerPadding,
    paddingBottom: spacing.xxxl,
  },
  stitched: {
    borderStyle: 'dashed',
    borderColor: colors.stitch,
  },
  sparkle: { position: 'absolute' },
  books: { position: 'absolute', left: spacing.xs, bottom: spacing.xs },
});
