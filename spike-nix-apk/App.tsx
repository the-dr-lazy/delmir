// THROWAWAY SPIKE (delmir#32): proves onnxruntime-react-native links and bundles.
import React from 'react';
import { Text, View } from 'react-native';
import { InferenceSession } from 'onnxruntime-react-native';

export default function App() {
  return (
    <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
      <Text>DELMIR spike: ONNX Runtime {typeof InferenceSession.create}</Text>
    </View>
  );
}
