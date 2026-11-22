import { useId } from 'react';
import Svg, { Defs, Ellipse, G, Line, Path, Pattern, Rect, Text as SvgText } from 'react-native-svg';

import { colors, fontFamilies, palette } from '@/theme';

const ink = palette.espresso;

/** Coffee cup with a </> mark resting on two OOP books over a gingham placemat. */
export function BrandIllustration({ width = 220 }: { width?: number }) {
  const patternId = `mat-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  return (
    <Svg width={width} height={(width * 170) / 240} viewBox="0 0 240 170">
      <Defs>
        <Pattern id={patternId} patternUnits="userSpaceOnUse" width={12} height={12}>
          <Rect width={12} height={12} fill={colors.check.base} />
          <Rect width={6} height={12} fill={colors.check.stripe} />
          <Rect width={12} height={6} fill={colors.check.stripe} />
          <Rect width={6} height={6} fill={colors.check.cross} />
        </Pattern>
      </Defs>
      <Ellipse cx={120} cy={146} rx={108} ry={22} fill={`url(#${patternId})`} opacity={0.75} />

      {/* Bottom book */}
      <Path d="M30 122 L176 116 L214 126 L68 133 Z" fill={palette.mocha} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Path d="M30 122 L68 133 L68 160 L32 150 Q24 136 30 122 Z" fill={palette.mocha} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Path d="M68 133 L214 126 L214 152 L68 160 Z" fill={palette.cream} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Path d="M80 141 L204 135 M80 148 L196 143 M80 154 L204 148" stroke={palette.latte} strokeWidth={1.5} strokeLinecap="round" />
      <Path d="M38 130 Q34 140 39 148 M60 136 Q56 146 61 155" stroke={ink} strokeWidth={1.8} fill="none" strokeLinecap="round" />

      {/* Top book */}
      <Path d="M40 92 L170 84 L204 95 L74 104 Z" fill={palette.cocoa} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Path d="M40 92 L74 104 L74 130 L42 120 Q34 106 40 92 Z" fill={palette.cocoa} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Path d="M74 104 L204 95 L204 120 L74 130 Z" fill={palette.cream} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Path d="M86 111 L194 104 M86 118 L188 112 M86 124 L194 118" stroke={palette.latte} strokeWidth={1.5} strokeLinecap="round" />
      <SvgText x={46} y={117} fontSize={11} fontWeight="700" fontFamily={fontFamilies.bold} fill={palette.cream} transform="rotate(14 46 117)">
        OOP
      </SvgText>

      {/* Cup */}
      <Path d="M152 54 C172 50 174 80 150 78" stroke={ink} strokeWidth={5} fill="none" strokeLinecap="round" />
      <Path d="M152 54 C172 50 174 80 150 78" stroke={palette.cream} strokeWidth={2} fill="none" strokeLinecap="round" />
      <Path d="M86 46 H156 V66 C156 84 142 94 121 94 C100 94 86 84 86 66 Z" fill={palette.cream} stroke={ink} strokeWidth={2.5} strokeLinejoin="round" />
      <Ellipse cx={121} cy={46} rx={35} ry={7} fill={palette.cream} stroke={ink} strokeWidth={2.5} />
      <Ellipse cx={121} cy={47} rx={29} ry={4.5} fill={palette.deepCoffee} />
      <SvgText x={121} y={76} fontSize={18} fontWeight="700" fontFamily={fontFamilies.bold} fill={ink} textAnchor="middle">
        {'</>'}
      </SvgText>

      {/* Steam */}
      <G stroke={palette.mocha} strokeWidth={3} fill="none" strokeLinecap="round">
        <Path d="M108 34 C102 27 114 22 108 12" />
        <Path d="M121 32 C115 23 128 18 121 6" />
        <Path d="M134 34 C128 27 140 22 134 13" />
      </G>
      <Sparks x={170} y={14} />
    </Svg>
  );
}

function Sparks({ x, y, color = palette.espresso }: { x: number; y: number; color?: string }) {
  return (
    <G stroke={color} strokeWidth={2.5} strokeLinecap="round">
      <Line x1={x} y1={y + 4} x2={x + 2} y2={y + 16} />
      <Line x1={x + 10} y1={y + 22} x2={x + 20} y2={y + 12} />
      <Line x1={x + 14} y1={y + 32} x2={x + 26} y2={y + 30} />
    </G>
  );
}

/** Three short "shine" strokes used as corner decoration. */
export function Sparkle({ size = 32, flip = false, color = palette.espresso }: { size?: number; flip?: boolean; color?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 32 36" style={flip ? { transform: [{ scaleX: -1 }] } : undefined}>
      <Sparks x={2} y={0} color={color} />
    </Svg>
  );
}

/** Small leafy sprig that frames section pills. */
export function Sprig({ size = 26, flip = false }: { size?: number; flip?: boolean }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 26 26" style={flip ? { transform: [{ scaleX: -1 }] } : undefined}>
      <G stroke={palette.espresso} strokeWidth={1.8} strokeLinecap="round" fill={palette.mocha}>
        <Path d="M4 24 C10 18 14 12 22 4" fill="none" />
        <Path d="M9 18 C5 17 3 13 4 11 C7 12 9 15 9 18 Z" />
        <Path d="M13 13 C9 12 8 8 9 6 C12 7 13 10 13 13 Z" />
        <Path d="M12 18 C15 20 19 19 20 17 C17 15 14 16 12 18 Z" />
        <Path d="M16 11 C19 13 23 12 24 10 C21 8 18 9 16 11 Z" />
      </G>
    </Svg>
  );
}

/** Two stacked books tucked into the paper corner. */
export function BookStack({ width = 64 }: { width?: number }) {
  return (
    <Svg width={width} height={(width * 46) / 64} viewBox="0 0 64 46">
      <G stroke={ink} strokeWidth={1.8} strokeLinejoin="round">
        <Path d="M4 26 L46 22 L60 27 L18 31 Z" fill={palette.cocoa} />
        <Path d="M4 26 L18 31 L18 44 L5 40 Q1 33 4 26 Z" fill={palette.cocoa} />
        <Path d="M18 31 L60 27 L60 39 L18 44 Z" fill={palette.cream} />
        <Path d="M6 8 L44 4 L56 9 L18 13 Z" fill={palette.mocha} />
        <Path d="M6 8 L18 13 L18 26 L7 22 Q3 15 6 8 Z" fill={palette.mocha} />
        <Path d="M18 13 L56 9 L56 21 L18 26 Z" fill={palette.cream} />
      </G>
      <Path d="M23 17 L52 14 M23 21 L50 18 M23 35 L56 32 M23 39 L54 36" stroke={palette.latte} strokeWidth={1.2} strokeLinecap="round" />
    </Svg>
  );
}
