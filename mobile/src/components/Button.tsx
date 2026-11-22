import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, View, type PressableProps } from 'react-native';

import { colors, layout, radii, shadows, spacing } from '@/theme';

import { AppText } from './AppText';
import { CheckBackground } from './CheckBackground';
import { Icon, type IconName } from './Icon';

type Variant = 'primary' | 'secondary' | 'gingham' | 'link';

type Props = Omit<PressableProps, 'children'> & {
  title: string;
  variant?: Variant;
  loading?: boolean;
  /** Icon drawn after the title (e.g. a forward arrow). */
  icon?: IconName;
  /** Custom node drawn before the title (e.g. a provider logo). */
  leading?: ReactNode;
};

export function Button({ title, variant = 'primary', loading = false, icon, leading, disabled, style, ...rest }: Props) {
  const isDisabled = disabled || loading;
  const textColor =
    variant === 'primary'
      ? colors.primaryButtonText
      : variant === 'link'
        ? colors.textPrimary
        : colors.secondaryButtonText;
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
      {variant === 'gingham' && (
        <CheckBackground
          style={styles.ginghamFill}
          cellSize={18}
          base={colors.surface}
          stripe={colors.pill}
          cross={colors.stitch}
        />
      )}
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <View style={styles.content}>
          {leading}
          <AppText
            variant={variant === 'link' ? 'label' : 'button'}
            color={textColor}
            style={variant === 'link' && styles.linkText}>
            {title}
          </AppText>
          {icon && <Icon name={icon} size={24} color={textColor} strokeWidth={2.2} />}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.lg,
    overflow: 'hidden',
  },
  content: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  primary: {
    minHeight: layout.touchTarget,
    paddingHorizontal: spacing.xl,
    backgroundColor: colors.primaryButton,
    borderBottomWidth: 4,
    borderColor: colors.primaryButtonEdge,
    ...shadows.soft,
  },
  secondary: {
    minHeight: layout.touchTarget,
    paddingHorizontal: spacing.xl,
    backgroundColor: colors.secondaryButton,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  gingham: {
    minHeight: layout.touchTarget,
    paddingHorizontal: spacing.xl,
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  ginghamFill: { ...StyleSheet.absoluteFill, opacity: 0.85 },
  link: {
    minHeight: 40,
    paddingHorizontal: spacing.xs,
    overflow: 'visible',
  },
  linkText: { textDecorationLine: 'underline' },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  disabled: { opacity: 0.55 },
});
