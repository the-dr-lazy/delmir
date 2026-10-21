// SPIKE (delmir#43): workaround A, effect's own Migrator.fromRecord. Bundles only with
// dist/sql/Migrator.js patched (its non-literal `import()` is replaced in package.nix).
import * as Effect from 'effect/Effect';
import * as Migrator from 'effect/sql/Migrator';
import { runners, type Migrations } from './runners';

const run = Migrator.make({});

runners.migrator = (migrations: Migrations) =>
  run({ loader: Migrator.fromRecord(migrations) }).pipe(Effect.map(done => done.map(([id, name]) => `${id}_${name}`)));
