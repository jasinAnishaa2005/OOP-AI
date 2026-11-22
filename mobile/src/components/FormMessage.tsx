import { StyleSheet, View } from 'react-native';

import { colors, radii, spacing } from '@/theme';

import { AppText } from './AppText';

type Props = { message?: string | null; tone?: 'error' | 'info' };

export function FormMessage({ message, tone = 'error' }: Props) {
  if (!message) return null;
  const isError = tone === 'error';
  return (
    <View
      accessibilityRole="alert"
      style={[styles.box, { borderColor: isError ? colors.error : colors.border }]}>
      <AppText variant="caption" color={isError ? colors.error : colors.textSecondary}>
        {message}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    borderWidth: 1.5,
    borderRadius: radii.md,
    backgroundColor: colors.surfaceMuted,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
});
