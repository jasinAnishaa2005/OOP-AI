import { Text, type TextProps } from 'react-native';

import { colors, typography, type TypographyVariant } from '@/theme';

type Props = TextProps & {
  variant?: TypographyVariant;
  color?: string;
  align?: 'left' | 'center' | 'right';
};

export function AppText({ variant = 'body', color = colors.textPrimary, align, style, ...rest }: Props) {
  return <Text style={[typography[variant], { color, textAlign: align }, style]} {...rest} />;
}
