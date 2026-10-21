// SPIKE (delmir#43) entry: no Effect, no polyfill.
import { AppRegistry } from 'react-native';
import { log } from './src/log';
import { probe } from './src/probe';
import App from './src/AppBaseline';
import { name as appName } from './app.json';

log('js-start', { variant: 'baseline' });
probe('baseline');
AppRegistry.registerComponent(appName, () => App);
