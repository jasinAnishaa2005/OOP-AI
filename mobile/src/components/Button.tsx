import { ActivityIndicator, Pressable, StyleSheet, type PressableProps } from 'react-native';

import { colors, layout, radii, shadows, spacing } from '@/theme';

import { AppText } from './AppText';

type Props = Omit<PressableProps, 'children'> & {
  title: string;
  variant?: 'primary' | 'secondary' | 'link';
  loading?: boolean;
};

export function Button({ title, variant = 'primary', loading = false, disabled, style, ...rest }: Props) {
  const isDisabled = disabled || loading;
  const textColor =
    variant === 'primary'
      ? colors.primaryButtonText
      : variant === 'secondary'
        ? colors.secondaryButtonText
        : colors.textSecondary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      disabled={isDisabled}
      style={(state) => [
        styles.base,
        styles[variant],
        state.pressed && styles.pressed,
        isDisabled && styles.disabled,
        typeof style === 'function' ? style(state) : style,
      ]}
      {...rest}>
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <AppText variant={variant === 'link' ? 'label' : 'bodyBold'} color={textColor}>
          {title}
        </AppText>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.md,
  },
  primary: {
    minHeight: layout.touchTarget,
    paddingHorizontal: spacing.xl,
    backgroundColor: colors.primaryButton,
    borderWidth: 1.5,
    borderColor: colors.borderStrong,
    ...shadows.soft,
  },
  secondary: {
    minHeight: layout.touchTarget,
    paddingHorizontal: spacing.xl,
    backgroundColor: colors.secondaryButton,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  link: {
    minHeight: 40,
    paddingHorizontal: spacing.sm,
  },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  disabled: { opacity: 0.55 },
});
