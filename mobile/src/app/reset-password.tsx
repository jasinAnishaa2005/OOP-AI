import { Link, router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { authApi } from '@/api/auth';
import { BrandHeader, Button, FormMessage, Screen, TextField } from '@/components';
import { useAuthStore } from '@/store/auth';
import { spacing } from '@/theme';

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ token?: string }>();
  const [token, setToken] = useState(typeof params.token === 'string' ? params.token : '');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async () => {
    if (!token.trim()) return setError('Paste the reset code from your email.');
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password))
      return setError('Password needs at least 8 characters with a letter and a number.');
    if (password !== confirm) return setError('Passwords do not match.');
    setError(null);
    setSubmitting(true);
    try {
      const res = await authApi.resetPassword(token.trim(), password);
      // The server revoked every session; drop the local one too.
      if (useAuthStore.getState().status === 'signedIn') await useAuthStore.getState().signOut();
      setDone(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reset failed.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <BrandHeader compact subtitle="Reset Password" />
      <FormMessage message={error} />
      <FormMessage message={done} tone="info" />
      {done ? (
        <Button title="Go to Sign In" icon="arrowRight" onPress={() => router.replace('/sign-in')} />
      ) : (
        <>
          <TextField label="Reset code" icon="key" value={token} onChangeText={setToken} autoCapitalize="none" autoCorrect={false} />
          <TextField label="New password" icon="lock" password value={password} onChangeText={setPassword} autoComplete="new-password" />
          <TextField label="Confirm password" icon="lock" password value={confirm} onChangeText={setConfirm} />
          <Button title="Update Password" icon="arrowRight" onPress={onSubmit} loading={submitting} />
          <View style={styles.links}>
            <Link href="/sign-in" asChild>
              <Button variant="link" title="Back to Sign In" />
            </Link>
          </View>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  links: { alignItems: 'center', marginTop: spacing.lg },
});
