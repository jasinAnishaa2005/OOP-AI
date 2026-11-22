import { Link } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText, BrandHeader, Button, Checkbox, FormMessage, Screen, TextField } from '@/components';
import type { TextFieldHandle } from '@/components/TextField';
import { useAuthStore } from '@/store/auth';
import { colors, spacing } from '@/theme';

export default function SignInScreen() {
  const signIn = useAuthStore((s) => s.signIn);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const passwordRef = useRef<TextFieldHandle>(null);

  const onSubmit = async () => {
    if (!identifier.trim() || !password) {
      setError('Enter your student ID or email and your password.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await signIn(identifier, password, rememberMe);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Sign in failed.');
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <BrandHeader subtitle="Welcome back" />
      <FormMessage message={error} />
      <TextField
        label="Student ID or Email"
        value={identifier}
        onChangeText={setIdentifier}
        autoCapitalize="none"
        autoComplete="username"
        textContentType="username"
        returnKeyType="next"
        onSubmitEditing={() => passwordRef.current?.focus()}
      />
      <TextField
        ref={passwordRef}
        label="Password"
        password
        value={password}
        onChangeText={setPassword}
        autoComplete="current-password"
        textContentType="password"
        returnKeyType="go"
        onSubmitEditing={onSubmit}
      />
      <View style={styles.row}>
        <Checkbox label="Remember me" checked={rememberMe} onChange={setRememberMe} />
        <Link href="/forgot-password" asChild>
          <Button variant="link" title="Forgot password?" />
        </Link>
      </View>
      <Button title="Sign In" onPress={onSubmit} loading={submitting} />
      <View style={styles.footer}>
        <AppText variant="caption" color={colors.textMuted}>
          New to OOP-AI?
        </AppText>
        <Link href="/sign-up" asChild>
          <Button variant="link" title="Create an account" />
        </Link>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.lg,
    flexWrap: 'wrap',
  },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: spacing.lg },
});
