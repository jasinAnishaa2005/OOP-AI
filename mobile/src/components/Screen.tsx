import type { PropsWithChildren } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { usePaperFrame } from '@/theme';

import { CheckBackground } from './CheckBackground';
import { PaperContainer } from './PaperContainer';

/** Full-screen gingham background with the content centered inside a paper container. */
export function Screen({ children }: PropsWithChildren) {
  const frame = usePaperFrame();
  return (
    <CheckBackground cellSize={frame.checkCell}>
      <SafeAreaView style={styles.flex}>
        <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView
            contentContainerStyle={[styles.scroll, { paddingHorizontal: frame.margin, paddingVertical: frame.margin }]}
            keyboardShouldPersistTaps="handled">
            <PaperContainer frame={frame}>{children}</PaperContainer>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </CheckBackground>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center' },
});
