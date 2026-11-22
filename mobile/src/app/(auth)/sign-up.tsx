import { Link } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText, BrandHeader, Button, FormMessage, Screen, TextField } from '@/components';
import { useAuthStore } from '@/store/auth';
import { colors, spacing } from '@/theme';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Errors = Partial<Record<'fullName' | 'email' | 'password' | 'confirm', string>>;

export default function SignUpScreen() {
  const signUp = useAuthStore((s) => s.signUp);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [studentId, setStudentId] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const validate = (): Errors => {
    const next: Errors = {};
    if (fullName.trim().length < 2) next.fullName = 'Enter your full name.';
    if (!EMAIL_RE.test(email.trim())) next.email = 'Enter a valid email address.';
    if (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password))
      next.password = 'At least 8 characters with a letter and a number.';
    if (confirm !== password) next.confirm = 'Passwords do not match.';
    return next;
  };

  const onSubmit = async () => {
    const next = validate();
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length) return;
    setSubmitting(true);
    try {
      await signUp({
        full_name: fullName.trim(),
        email: email.trim(),
        student_id: studentId.trim() || null,
        password,
      });
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Sign up failed.');
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <BrandHeader compact subtitle="Create Your Account" />
      <FormMessage message={formError} />
      <TextField label="Full name" icon="user" value={fullName} onChangeText={setFullName} autoComplete="name" error={errors.fullName} />
      <TextField
        label="Email"
        icon="mail"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        autoComplete="email"
        error={errors.email}
      />
      <TextField
        label="Student ID (optional)"
        icon="id"
        value={studentId}
        onChangeText={setStudentId}
        autoCapitalize="characters"
        hint="Lets you sign in with your student ID."
      />
      <TextField
        label="Password"
        icon="lock"
        password
        value={password}
        onChangeText={setPassword}
        autoComplete="new-password"
        textContentType="newPassword"
        error={errors.password}
      />
      <TextField label="Confirm password" icon="lock" password value={confirm} onChangeText={setConfirm} error={errors.confirm} />
      <Button title="Sign Up" icon="arrowRight" onPress={onSubmit} loading={submitting} />
      <View style={styles.footer}>
        <AppText variant="body" color={colors.textPrimary}>
          Already have an account?
        </AppText>
        <Link href="/sign-in" asChild>
          <Button variant="link" title="Sign In" />
        </Link>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: spacing.xs, marginTop: spacing.lg },
});
