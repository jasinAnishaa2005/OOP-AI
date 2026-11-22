import { Link } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { authApi } from '@/api/auth';
import { AppText, BrandHeader, Button, FormMessage, Screen, TextField } from '@/components';
import { colors, spacing } from '@/theme';

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async () => {
    if (!email.trim()) {
      setError('Enter the email you registered with.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const res = await authApi.forgotPassword(email.trim());
      setInfo(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <BrandHeader subtitle="Forgot password" />
      <AppText variant="body" color={colors.textSecondary} align="center" style={styles.intro}>
        Enter your email and we will send you a link and a reset code.
      </AppText>
      <FormMessage message={error} />
      <FormMessage message={info} tone="info" />
      <TextField
        label="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
      />
      <Button title="Send reset link" onPress={onSubmit} loading={submitting} />
      <View style={styles.links}>
        <Link href="/reset-password" asChild>
          <Button variant="link" title="I have a reset code" />
        </Link>
        <Link href="/sign-in" asChild>
          <Button variant="link" title="Back to sign in" />
        </Link>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  intro: { marginBottom: spacing.lg },
  links: { alignItems: 'center', marginTop: spacing.lg },
});
