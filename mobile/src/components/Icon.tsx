import Svg, { Circle, Line, Path, Rect } from 'react-native-svg';

import { colors } from '@/theme';

export type IconName = 'user' | 'mail' | 'id' | 'lock' | 'key' | 'eye' | 'eyeOff' | 'arrowRight' | 'check';

type Props = { name: IconName; size?: number; color?: string; strokeWidth?: number };

/** Hand-drawn style line icons in the coffee palette. */
export function Icon({ name, size = 24, color = colors.icon, strokeWidth = 1.8 }: Props) {
  const stroke = { stroke: color, strokeWidth, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {name === 'user' && (
        <>
          <Circle cx={12} cy={8} r={4} {...stroke} />
          <Path d="M4.5 20.5c0-4 3.4-6.5 7.5-6.5s7.5 2.5 7.5 6.5z" {...stroke} />
        </>
      )}
      {name === 'mail' && (
        <>
          <Rect x={3} y={5.5} width={18} height={13} rx={3} {...stroke} />
          <Path d="M4 7l8 6 8-6" {...stroke} />
        </>
      )}
      {name === 'id' && (
        <>
          <Rect x={2.5} y={5} width={19} height={14} rx={3} {...stroke} />
          <Circle cx={8.5} cy={11} r={2.2} {...stroke} />
          <Path d="M5.5 16.2c.6-1.6 1.7-2.4 3-2.4s2.4.8 3 2.4M14.5 10h4M14.5 13.5h3" {...stroke} />
        </>
      )}
      {name === 'lock' && (
        <>
          <Rect x={5} y={10.5} width={14} height={10} rx={3} {...stroke} />
          <Path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" {...stroke} />
        </>
      )}
      {name === 'key' && (
        <>
          <Circle cx={8} cy={14} r={4} {...stroke} />
          <Path d="M11 11l8-8M16 6l2.5 2.5M14 8l2 2" {...stroke} />
        </>
      )}
      {(name === 'eye' || name === 'eyeOff') && (
        <>
          <Path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" {...stroke} />
          <Circle cx={12} cy={12} r={3} {...stroke} />
          {name === 'eyeOff' && <Line x1={4} y1={4} x2={20} y2={20} {...stroke} />}
        </>
      )}
      {name === 'arrowRight' && <Path d="M4 12h15M13 6l6 6-6 6" {...stroke} />}
      {name === 'check' && <Path d="M5 12.5l4.5 4.5L19 7.5" {...stroke} />}
    </Svg>
  );
}
