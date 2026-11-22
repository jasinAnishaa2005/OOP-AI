import { useId } from 'react';
import { StyleSheet, View, type ViewProps } from 'react-native';
import Svg, { Defs, Pattern, Rect } from 'react-native-svg';

import { colors, layout } from '@/theme';

type Props = ViewProps & {
  cellSize?: number;
  base?: string;
  stripe?: string;
  cross?: string;
  opacity?: number;
};

/** Signature gingham: light base, mid-tone stripes and a darker square where the stripes cross. */
export function CheckBackground({
  cellSize = layout.checkCellSize,
  base = colors.check.base,
  stripe = colors.check.stripe,
  cross = colors.check.cross,
  opacity = 1,
  style,
  children,
  ...rest
}: Props) {
  const half = cellSize / 2;
  // Unique per instance: web stacks keep earlier screens mounted, and duplicate SVG ids break the fill.
  const patternId = `gingham-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  return (
    <View style={[styles.root, { backgroundColor: base }, style]} {...rest}>
      <Svg style={StyleSheet.absoluteFill} width="100%" height="100%" pointerEvents="none" opacity={opacity}>
        <Defs>
          <Pattern id={patternId} patternUnits="userSpaceOnUse" width={cellSize} height={cellSize}>
            <Rect x={0} y={0} width={cellSize} height={cellSize} fill={base} />
            <Rect x={0} y={0} width={half} height={cellSize} fill={stripe} />
            <Rect x={0} y={0} width={cellSize} height={half} fill={stripe} />
            <Rect x={0} y={0} width={half} height={half} fill={cross} />
          </Pattern>
        </Defs>
        <Rect x={0} y={0} width="100%" height="100%" fill={`url(#${patternId})`} />
      </Svg>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, overflow: 'hidden' },
});
