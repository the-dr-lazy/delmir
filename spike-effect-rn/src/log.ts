// SPIKE (delmir#43): every result goes to logcat as one `SPIKE {json}` line (tag ReactNativeJS).
export const log = (event: string, data: Record<string, unknown> = {}) =>
  console.log(`SPIKE ${JSON.stringify({ event, t: Date.now(), ...data })}`);
