import { StyleSheet, View } from 'react-native';

import { colors, radii, spacing } from '@/theme';

import { AppText } from './AppText';

/** Thin rule with a dashed "or" pill in the middle. */
export function OrDivider({ label = 'or' }: { label?: string }) {
  return (
    <View style={styles.row}>
      <View style={styles.line} />
      <View style={styles.pill}>
        <AppText variant="bodyBold">{label}</AppText>
      </View>
      <View style={styles.line} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', marginVertical: spacing.lg, paddingHorizontal: spacing.xl },
  line: { flex: 1, height: 1, backgroundColor: colors.border, opacity: 0.6 },
  pill: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xxs,
    borderRadius: radii.lg,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.border,
    backgroundColor: colors.pill,
  },
});
