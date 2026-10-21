// SPIKE (delmir#43): two screens on React Navigation 7 static native-stack, state in @effect/atom-react.
import React, { useEffect, useRef } from 'react';
import { Animated, Button, FlatList, Linking, Pressable, Text, View } from 'react-native';
import { createStaticNavigation, useNavigation } from '@react-navigation/native';
import { createNativeStackNavigator, type NativeStackScreenProps } from '@react-navigation/native-stack';
import * as Effect from 'effect/Effect';
import * as Atom from 'effect/reactivity/Atom';
import * as AsyncResult from 'effect/reactivity/AsyncResult';
import { RegistryProvider, useAtomRefresh, useAtomSet, useAtomValue } from '@effect/atom-react';
import { RegistryLayer, bench, checks, cipherProbe, getCase, listCases, migrationsCheck, runnerName, seed } from './Registry';
import { log } from './log';

const runtime = Atom.runtime(RegistryLayer);
const casesAtom = runtime.atom(listCases);
const caseAtom = Atom.family((id: string) => runtime.atom(getCase(id)));

const command = runtime.fn((url: string) => {
  const u = new URL(url);
  const op = u.hostname;
  const n = (k: string, d: number) => Number(u.searchParams.get(k) ?? d);
  log('command', { url, runner: runnerName() });
  const run =
    op === 'seed' ? seed(n('n', 1000))
    : op === 'bench' ? bench(u.searchParams.get('mode') === 'async' ? 'async' : 'sync', n('runs', 20))
    : op === 'checks' ? checks
    : op === 'cipher' ? cipherProbe
    : op === 'migrations' ? migrationsCheck
    : Effect.void;
  return run.pipe(
    Effect.tapCause(cause => Effect.sync(() => log('command-failed', { url, cause: String(cause) }))),
    Effect.tap(() => Effect.sync(() => log('command-done', { url }))),
  );
});

let firstScreenLogged = false;

function Spinner() {
  // JS-driven (not native-driver) animation, so a blocked JS thread shows up as janky frames in gfxinfo.
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.loop(Animated.timing(v, { toValue: 1, duration: 1000, useNativeDriver: false })).start();
  }, [v]);
  const width = v.interpolate({ inputRange: [0, 1], outputRange: [10, 300] });
  return <Animated.View style={{ height: 6, width, backgroundColor: 'teal' }} />;
}

function CaseList() {
  const nav = useNavigation<any>();
  const cases = useAtomValue(casesAtom);
  const refresh = useAtomRefresh(casesAtom);
  const runCommand = useAtomSet(command, { mode: 'promise' });
  useEffect(() => {
    const go = (url: string | null | undefined) => { if (url) runCommand(url).then(refresh, refresh); };
    Linking.getInitialURL().then(go);
    const sub = Linking.addEventListener('url', e => go(e.url));
    return () => sub.remove();
  }, [runCommand, refresh]);
  useEffect(() => {
    if (AsyncResult.isSuccess(cases)) log('first-data', { count: cases.value.length });
  }, [cases]);
  return (
    <View
      style={{ flex: 1 }}
      onLayout={() => { if (!firstScreenLogged) { firstScreenLogged = true; log('first-screen', { variant: 'effect' }); } }}>
      <Spinner />
      <Button title="Seed 1,000 cases (debug)" onPress={() => runCommand('delmirspike://seed?n=1000').then(refresh)} />
      {AsyncResult.match(cases, {
        onInitial: () => <Text>Opening registry…</Text>,
        onFailure: f => <Text>Failed: {String(f.cause)}</Text>,
        onSuccess: ({ value }) => (
          <FlatList
            data={value}
            keyExtractor={c => c.id}
            renderItem={({ item }) => (
              <Pressable onPress={() => nav.navigate('Case', { id: item.id })} style={{ padding: 12 }}>
                <Text>{item.label} · P(OMI) {item.pOmi?.toFixed(2) ?? 'declined'}</Text>
              </Pressable>
            )}
          />
        ),
      })}
    </View>
  );
}

function CaseScreen({ route }: NativeStackScreenProps<{ Case: { id: string } }, 'Case'>) {
  const c = useAtomValue(caseAtom(route.params.id));
  return AsyncResult.match(c, {
    onInitial: () => <Text>Loading…</Text>,
    onFailure: f => <Text>Failed: {String(f.cause)}</Text>,
    onSuccess: ({ value }) => <Text style={{ padding: 12 }}>{JSON.stringify(value, null, 1)}</Text>,
  });
}

const Stack = createNativeStackNavigator({
  screens: {
    Cases: { screen: CaseList, options: { title: `Cases (${runnerName()} runner)` } },
    Case: CaseScreen,
  },
});
const Navigation = createStaticNavigation(Stack);

export default function App() {
  return (
    <RegistryProvider>
      <Navigation />
    </RegistryProvider>
  );
}
