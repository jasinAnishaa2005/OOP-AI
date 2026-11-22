import { StyleSheet, View } from 'react-native';

import { colors, spacing } from '@/theme';

import { AppText } from './AppText';

/** Text wordmark used until the final OOP-AI logo asset is provided. */
export function BrandHeader({ subtitle }: { subtitle?: string }) {
  return (
    <View style={styles.root}>
      <AppText variant="display" align="center">
        OOP-AI
      </AppText>
      <AppText variant="tagline" color={colors.textMuted} align="center" style={styles.tagline}>
        LEARN • PRACTICE • EXCEL
      </AppText>
      {subtitle ? (
        <AppText variant="h2" align="center" style={styles.subtitle}>
          {subtitle}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { alignItems: 'center', marginBottom: spacing.xl },
  tagline: { marginTop: spacing.xs },
  subtitle: { marginTop: spacing.xl },
});
