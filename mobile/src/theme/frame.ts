import { useWindowDimensions } from 'react-native';

import { layout } from './tokens';

/**
 * Proportions measured from the approved sign-in reference (1024px wide):
 * paper card 906px wide with 60px corner radius, 59px gingham margin, 53.4px check period,
 * 24px paper inset before the stitched ribbon, and a ~10px ribbon.
 */
const REF = { card: 906, radius: 60, check: 53.4, inset: 24, ribbon: 10, screen: 1024 } as const;

export type PaperFrame = {
  cardWidth: number;
  margin: number;
  radius: number;
  checkCell: number;
  inset: number;
  ribbon: number;
};

export function usePaperFrame(): PaperFrame {
  const { width } = useWindowDimensions();
  const cardWidth = Math.min(width * (REF.card / REF.screen), layout.maxContentWidth);
  const scale = (v: number) => Math.round((v / REF.card) * cardWidth);
  return {
    cardWidth,
    margin: Math.max((width - cardWidth) / 2, 12),
    radius: scale(REF.radius),
    checkCell: Math.round((REF.check / REF.card) * cardWidth * 10) / 10,
    inset: scale(REF.inset),
    ribbon: Math.max(scale(REF.ribbon), 3),
  };
}
