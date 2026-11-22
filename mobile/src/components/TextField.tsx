import { useState, type ComponentRef, type Ref } from 'react';
import { Pressable, StyleSheet, TextInput, View, type TextInputProps } from 'react-native';

import { colors, layout, radii, spacing, typography } from '@/theme';

import { AppText } from './AppText';

export type TextFieldHandle = ComponentRef<typeof TextInput>;

type Props = TextInputProps & {
  ref?: Ref<TextFieldHandle>;
  label: string;
  error?: string | null;
  hint?: string;
  password?: boolean;
};

export function TextField({ ref, label, error, hint, password = false, style, onFocus, onBlur, ...rest }: Props) {
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(true);
  return (
    <View style={styles.wrapper}>
      <AppText variant="label" color={colors.textSecondary} style={styles.label}>
        {label}
      </AppText>
      <View
        style={[
          styles.inputRow,
          focused && { borderColor: colors.inputBorderFocused },
          !!error && { borderColor: colors.error },
        ]}>
        <TextInput
          ref={ref}
          accessibilityLabel={label}
          placeholderTextColor={colors.placeholder}
          secureTextEntry={password && hidden}
          autoCapitalize={password ? 'none' : rest.autoCapitalize}
          autoCorrect={password ? false : rest.autoCorrect}
          style={[styles.input, style]}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          {...rest}
        />
        {password && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={hidden ? 'Show password' : 'Hide password'}
            onPress={() => setHidden((v) => !v)}
            hitSlop={8}
            style={styles.toggle}>
            <AppText variant="label" color={colors.textMuted}>
              {hidden ? 'Show' : 'Hide'}
            </AppText>
          </Pressable>
        )}
      </View>
      {error ? (
        <AppText variant="caption" color={colors.error} style={styles.help}>
          {error}
        </AppText>
      ) : hint ? (
        <AppText variant="caption" color={colors.textMuted} style={styles.help}>
          {hint}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { marginBottom: spacing.lg },
  label: { marginBottom: spacing.xs },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: layout.touchTarget,
    borderRadius: radii.lg,
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    backgroundColor: colors.inputBackground,
  },
  input: {
    flex: 1,
    ...typography.body,
    color: colors.textPrimary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    // The rounded row border already shows focus; drop the browser's default outline.
    outlineWidth: 0,
  },
  toggle: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  help: { marginTop: spacing.xs },
});
