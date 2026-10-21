// SPIKE (delmir#43): workaround B, a local `fromRecord`-style runner that never imports effect/sql/Migrator.
import * as Effect from 'effect/Effect';
import * as SqlClient from 'effect/sql/SqlClient';
import { runners, type Migrations } from './runners';

runners.local = (migrations: Migrations) =>
  Effect.gen(function* () {
    const sql = yield* SqlClient.SqlClient;
    yield* sql`CREATE TABLE IF NOT EXISTS local_migrations (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at INTEGER NOT NULL)`;
    return yield* sql.withTransaction(
      Effect.gen(function* () {
        const done = new Set((yield* sql<{ id: number }>`SELECT id FROM local_migrations`).map(r => r.id));
        const pending = Object.keys(migrations)
          .map(key => { const [, id, name] = key.match(/^(\d+)_(.+)$/)!; return { key, id: Number(id), name }; })
          .filter(m => !done.has(m.id))
          .sort((a, b) => a.id - b.id);
        for (const m of pending) {
          yield* migrations[m.key];
          yield* sql`INSERT INTO local_migrations ${sql.insert({ id: m.id, name: m.name, created_at: Date.now() })}`;
        }
        return pending.map(m => m.key);
      }),
    );
  });
