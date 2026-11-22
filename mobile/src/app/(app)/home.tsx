import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText, BrandHeader, Button, Screen } from '@/components';
import { useAuthStore } from '@/store/auth';
import { colors, spacing } from '@/theme';

/** Signed-in landing screen. The full dashboard follows the upcoming dashboard design. */
export default function HomeScreen() {
  const user = useAuthStore((s) => s.user);
  const signOut = useAuthStore((s) => s.signOut);
  const [signingOut, setSigningOut] = useState(false);

  return (
    <Screen>
      <BrandHeader compact />
      <AppText variant="h1" align="center">
        Hello, {user?.full_name.split(' ')[0]}
      </AppText>
      <View style={styles.details}>
        <AppText variant="caption" color={colors.textMuted} align="center">
          {user?.email}
          {user?.student_id ? ` • ${user.student_id}` : ''}
        </AppText>
      </View>
      <Button
        variant="secondary"
        title="Sign Out"
        loading={signingOut}
        onPress={async () => {
          setSigningOut(true);
          await signOut();
        }}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  details: { marginTop: spacing.sm, marginBottom: spacing.xl },
});
