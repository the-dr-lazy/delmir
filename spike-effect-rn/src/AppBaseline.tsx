// SPIKE (delmir#43): the same two-screen app without Effect, op-sqlite or atoms, for size and cold-start baselines.
import React from 'react';
import { FlatList, Pressable, Text, View } from 'react-native';
import { createStaticNavigation, useNavigation } from '@react-navigation/native';
import { createNativeStackNavigator, type NativeStackScreenProps } from '@react-navigation/native-stack';
import { log } from './log';

const cases = Array.from({ length: 20 }, (_, i) => ({ id: String(i), label: `Case ${i}` }));
let firstScreenLogged = false;

function CaseList() {
  const nav = useNavigation<any>();
  return (
    <View
      style={{ flex: 1 }}
      onLayout={() => { if (!firstScreenLogged) { firstScreenLogged = true; log('first-screen', { variant: 'baseline' }); } }}>
      <FlatList
        data={cases}
        keyExtractor={c => c.id}
        renderItem={({ item }) => (
          <Pressable onPress={() => nav.navigate('Case', { id: item.id })} style={{ padding: 12 }}>
            <Text>{item.label}</Text>
          </Pressable>
        )}
      />
    </View>
  );
}

function CaseScreen({ route }: NativeStackScreenProps<{ Case: { id: string } }, 'Case'>) {
  return <Text style={{ padding: 12 }}>Case {route.params.id}</Text>;
}

const Navigation = createStaticNavigation(
  createNativeStackNavigator({ screens: { Cases: { screen: CaseList, options: { title: 'Cases (baseline)' } }, Case: CaseScreen } }),
);

export default function App() {
  return <Navigation />;
}
