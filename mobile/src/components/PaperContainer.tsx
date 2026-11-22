import { StyleSheet, View, type ViewProps } from 'react-native';

import { colors, layout, radii, shadows, spacing } from '@/theme';

import { BookStack, Sparkle } from './Illustrations';

type Props = ViewProps & { stitched?: boolean; decorated?: boolean };

/** Rounded off-white paper with a coffee outline, a dashed gingham ribbon and corner doodles. */
export function PaperContainer({ stitched = true, decorated = true, style, children, ...rest }: Props) {
  return (
    <View style={[styles.outer, style]} {...rest}>
      <View style={[styles.inner, stitched && styles.stitched]}>{children}</View>
      {decorated && (
        <>
          <View style={styles.sparkle} pointerEvents="none">
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
    width: '100%',
    maxWidth: layout.maxContentWidth,
    alignSelf: 'center',
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    borderWidth: 1.5,
    borderColor: colors.border,
    padding: spacing.sm,
    ...shadows.soft,
  },
  inner: {
    borderRadius: radii.lg - spacing.sm / 2,
    paddingHorizontal: layout.containerPadding - spacing.xs,
    paddingTop: layout.containerPadding,
    paddingBottom: spacing.xxxl,
  },
  stitched: {
    borderWidth: 5,
    borderStyle: 'dashed',
    borderColor: colors.stitch,
  },
  sparkle: { position: 'absolute', top: spacing.lg, right: spacing.lg },
  books: { position: 'absolute', left: spacing.xs, bottom: spacing.xs },
});
