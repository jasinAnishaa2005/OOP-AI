import { StyleSheet, View } from 'react-native';

import { colors, radii, spacing } from '@/theme';

import { AppText } from './AppText';
import { BrandIllustration, Sparkle, Sprig } from './Illustrations';

type Props = { subtitle?: string; compact?: boolean };

/** Illustration, OOP-AI wordmark, tagline and a dashed section pill. */
export function BrandHeader({ subtitle, compact = false }: Props) {
  return (
    <View style={styles.root}>
      <BrandIllustration width={compact ? 150 : 210} />
      <View style={styles.titleRow}>
        <Sparkle size={26} flip />
        <AppText variant="display" align="center" accessibilityRole="header" style={styles.title}>
          OOP-AI
        </AppText>
        <Sparkle size={26} />
      </View>
      <AppText variant="tagline" color={colors.textMuted} align="center">
        LEARN · PRACTICE · EXCEL
      </AppText>
      {subtitle ? (
        <View style={styles.pillRow}>
          <View style={styles.sprig}>
            <Sprig size={22} />
          </View>
          <View style={styles.pill}>
            <AppText variant="h2" align="center">
              {subtitle}
            </AppText>
          </View>
          <View style={styles.sprig}>
            <Sprig size={22} flip />
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { alignItems: 'center', marginBottom: spacing.xl },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.xs },
  title: { paddingHorizontal: spacing.xs },
  pillRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginTop: spacing.xl },
  sprig: { flexShrink: 0 },
  pill: {
    flexShrink: 1,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radii.lg,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.border,
    backgroundColor: colors.pill,
  },
});
