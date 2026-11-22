import { useId } from 'react';
import { StyleSheet, View, type ViewProps } from 'react-native';
import Svg, { Defs, Pattern, Rect } from 'react-native-svg';

import { colors, layout } from '@/theme';

type Props = ViewProps & {
  cellSize?: number;
  base?: string;
  stripe?: string;
  stripeOpacity?: number;
};

/** Signature gingham: two translucent stripe sets crossing over a paper base. */
export function CheckBackground({
  cellSize = layout.checkCellSize,
  base = colors.check.base,
  stripe = colors.check.stripe,
  stripeOpacity = 0.45,
  style,
  children,
  ...rest
}: Props) {
  const half = cellSize / 2;
  // Unique per instance: web stacks keep earlier screens mounted, and duplicate SVG ids break the fill.
  const patternId = `gingham-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  return (
    <View style={[styles.root, { backgroundColor: base }, style]} {...rest}>
      <Svg style={StyleSheet.absoluteFill} width="100%" height="100%" pointerEvents="none">
        <Defs>
          <Pattern id={patternId} patternUnits="userSpaceOnUse" width={cellSize} height={cellSize}>
            <Rect x={0} y={0} width={cellSize} height={cellSize} fill={base} />
            <Rect x={0} y={0} width={half} height={cellSize} fill={stripe} fillOpacity={stripeOpacity} />
            <Rect x={0} y={0} width={cellSize} height={half} fill={stripe} fillOpacity={stripeOpacity} />
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
