// SPIKE (delmir#43): migration runners register here, so an entry file can leave
// `effect/sql/Migrator` out of the bundle entirely (index.local.js).
import type * as Effect from 'effect/Effect';
import type * as SqlClient from 'effect/sql/SqlClient';

export type Migrations = Record<string, Effect.Effect<void, unknown, SqlClient.SqlClient>>;
export type Runner = (migrations: Migrations) => Effect.Effect<ReadonlyArray<string>, unknown, SqlClient.SqlClient>;

export const runners: Record<string, Runner> = {};
