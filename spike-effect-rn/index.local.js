// SPIKE (delmir#43) entry: Effect + registry with the local migration runner; never imports effect/sql/Migrator.
import 'react-native-get-random-values';
import { AppRegistry } from 'react-native';
import { log } from './src/log';
import './src/LocalRunner';
import { probe } from './src/probe';
import App from './src/App';
import { name as appName } from './app.json';

log('js-start', { variant: 'effect-local' });
probe('effect-local');
AppRegistry.registerComponent(appName, () => App);
