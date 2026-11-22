import { Link } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText, BrandHeader, Button, Checkbox, FormMessage, OrDivider, Screen, Sparkle, TextField } from '@/components';
import type { TextFieldHandle } from '@/components/TextField';
import { useAuthStore } from '@/store/auth';
import { colors, spacing, typography } from '@/theme';

export default function SignInScreen() {
  const signIn = useAuthStore((s) => s.signIn);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const passwordRef = useRef<TextFieldHandle>(null);

  const onSubmit = async () => {
    if (!identifier.trim() || !password) {
      setError('Enter your student ID or email and your password.');
      return;
    }
    setError(null);
    setInfo(null);
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
      <BrandHeader subtitle="Sign In to Continue" />
      <FormMessage message={error} />
      <FormMessage message={info} tone="info" />
      <TextField
        label="Student ID or Email"
        icon="user"
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
        icon="lock"
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
          <Button variant="link" title="Forgot Password?" />
        </Link>
      </View>
      <Button title="Sign In" icon="arrowRight" onPress={onSubmit} loading={submitting} />
      <OrDivider />
      <Button
        variant="gingham"
        title="Sign In with Google"
        leading={<AppText style={styles.google}>G</AppText>}
        onPress={() => {
          setError(null);
          setInfo('Google sign-in is not available yet. Please use your student ID or email.');
        }}
      />
      <View style={styles.footer}>
        <AppText variant="body" color={colors.textPrimary}>
          Don&apos;t have an account?
        </AppText>
        <Link href="/sign-up" asChild>
          <Button variant="link" title="Sign Up" />
        </Link>
        <View style={styles.footerSpark}>
          <Sparkle size={18} />
        </View>
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
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.xs, marginTop: spacing.lg },
  footerSpark: { marginTop: -spacing.lg },
  google: { ...typography.h1, fontSize: 28, color: colors.textPrimary },
});
