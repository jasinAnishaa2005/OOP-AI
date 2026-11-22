import { StyleSheet, View, type ViewProps } from 'react-native';

import { colors, layout, radii, shadows, spacing } from '@/theme';

type Props = ViewProps & { stitched?: boolean };

/** Rounded off-white reading surface with a visible border and optional stitched inset. */
export function PaperContainer({ stitched = true, style, children, ...rest }: Props) {
  return (
    <View style={[styles.outer, style]} {...rest}>
      <View style={[styles.inner, stitched && styles.stitched]}>{children}</View>
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
    borderWidth: 2,
    borderColor: colors.border,
    padding: spacing.sm,
    ...shadows.soft,
  },
  inner: {
    borderRadius: radii.lg - spacing.sm / 2,
    padding: layout.containerPadding - spacing.sm,
    paddingVertical: layout.containerPadding,
  },
  stitched: {
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.stitch,
  },
});
