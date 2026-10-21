// SPIKE (delmir#43): what the Hermes build in the APK provides.
import { Platform } from 'react-native';
import { log } from './log';

export const probe = (variant: string) => {
  const g = globalThis as any;
  const props = g.HermesInternal?.getRuntimeProperties?.() ?? {};
  log('probe', {
    variant,
    dev: __DEV__,
    typeof: {
      TextDecoder: typeof g.TextDecoder,
      TextEncoder: typeof g.TextEncoder,
      FinalizationRegistry: typeof g.FinalizationRegistry,
      WeakRef: typeof g.WeakRef,
      'crypto.getRandomValues': typeof g.crypto?.getRandomValues,
      'crypto.randomUUID': typeof g.crypto?.randomUUID,
      'Symbol.dispose': typeof (Symbol as any).dispose,
      'Symbol.asyncDispose': typeof (Symbol as any).asyncDispose,
      structuredClone: typeof g.structuredClone,
      AbortController: typeof g.AbortController,
      queueMicrotask: typeof g.queueMicrotask,
    },
    textDecoderWorks: (() => { try { return new g.TextDecoder().decode(new Uint8Array([0x68, 0x69])) === 'hi'; } catch (e) { return String(e); } })(),
    hermes: props,
    android: Platform.constants,
  });
};
