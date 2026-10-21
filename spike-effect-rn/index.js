// SPIKE (delmir#43) entry: Effect + registry. The registry migrates with Migrator.fromRecord (needs the
// Migrator.js patch); `delmirspike://migrations` also exercises the local runner on scratch databases.
import 'react-native-get-random-values';
import { AppRegistry } from 'react-native';
import { log } from './src/log';
import './src/LocalRunner';
import './src/MigratorRunner';
import { probe } from './src/probe';
import App from './src/App';
import { name as appName } from './app.json';

log('js-start', { variant: 'effect-migrator' });
probe('effect-migrator');
AppRegistry.registerComponent(appName, () => App);
