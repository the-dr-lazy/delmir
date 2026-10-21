// SPIKE (delmir#43): the encrypted case registry and every on-device measurement.
import * as Effect from 'effect/Effect';
import * as Layer from 'effect/Layer';
import * as Schema from 'effect/Schema';
import * as SqlClient from 'effect/sql/SqlClient';
import * as SqliteClient from '@effect/sql-sqlite-react-native/SqliteClient';
import { ANDROID_EXTERNAL_FILES_PATH, open } from '@op-engineering/op-sqlite';
import * as Keychain from 'react-native-keychain';
import { Case, Cases, generateCase, randomKeyHex } from './Case';
import { log } from './log';
import { runners, type Migrations } from './runners';

const SERVICE = 'delmir-spike-db-key';

// Random key made on first run, kept by react-native-keychain (Android Keystore wraps it).
export const getOrCreateKey = Effect.promise(async () => {
  const t0 = performance.now();
  const existing = await Keychain.getGenericPassword({ service: SERVICE });
  if (existing) {
    log('key', { created: false, ms: performance.now() - t0, storage: existing.storage });
    return existing.password;
  }
  const key = randomKeyHex();
  const result = await Keychain.setGenericPassword('db', key, { service: SERVICE });
  log('key', { created: true, ms: performance.now() - t0, result });
  return key;
});

// SQLCipher raw-key form, so no PBKDF2 on every open.
const cipherKey = (hex: string) => `x'${hex}'`;

export const migrations: Migrations = {
  '0001_cases': Effect.gen(function* () {
    const sql = yield* SqlClient.SqlClient;
    yield* sql`CREATE TABLE cases (id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, label TEXT NOT NULL, data TEXT NOT NULL)`;
  }),
  '0002_cases_created_at': Effect.gen(function* () {
    const sql = yield* SqlClient.SqlClient;
    yield* sql`CREATE INDEX cases_created_at ON cases (created_at DESC)`;
  }),
};

export const runnerName = (): string => (runners.migrator ? 'migrator' : 'local');

export const RegistryLayer = Layer.unwrap(
  Effect.gen(function* () {
    const key = yield* getOrCreateKey;
    const name = runnerName();
    const client = SqliteClient.layer({ filename: `delmir-spike-${name}.db`, encryptionKey: cipherKey(key) });
    const migrate = Layer.effectDiscard(
      Effect.gen(function* () {
        const t0 = performance.now();
        const applied = yield* runners[name](migrations);
        log('migrate', { runner: name, applied, ms: performance.now() - t0 });
      }).pipe(Effect.orDie),
    );
    return Layer.provideMerge(migrate, client);
  }),
);

const decodeCases = Schema.decodeUnknownEffect(Cases);
const decodeCase = Schema.decodeUnknownEffect(Case);

export const listCases = Effect.gen(function* () {
  const sql = yield* SqlClient.SqlClient;
  const rows = yield* sql<{ data: string }>`SELECT data FROM cases ORDER BY created_at DESC`;
  return yield* decodeCases(rows.map(r => JSON.parse(r.data)));
}).pipe(SqliteClient.withAsyncQuery);

export const getCase = (id: string) =>
  Effect.gen(function* () {
    const sql = yield* SqlClient.SqlClient;
    const rows = yield* sql<{ data: string }>`SELECT data FROM cases WHERE id = ${id}`;
    return yield* decodeCase(JSON.parse(rows[0].data));
  });

export const seed = (n: number) =>
  Effect.gen(function* () {
    const sql = yield* SqlClient.SqlClient;
    const t0 = performance.now();
    yield* sql`DELETE FROM cases`;
    yield* sql.withTransaction(
      Effect.forEach(
        Array.from({ length: n / 100 }, (_, b) => b),
        b =>
          sql`INSERT INTO cases ${sql.insert(
            Array.from({ length: 100 }, (_, j) => {
              const c = generateCase(b * 100 + j);
              return { id: c.id, created_at: c.createdAt, label: c.label, data: JSON.stringify(c) };
            }),
          )}`,
        { discard: true },
      ),
    );
    const [{ count }] = yield* sql<{ count: number }>`SELECT count(*) AS count FROM cases`;
    const [{ bytes }] = yield* sql<{ bytes: number }>`SELECT sum(length(data)) AS bytes FROM cases`;
    log('seed', { n, count, jsonBytes: bytes, ms: performance.now() - t0 });
  });

// JS frame watcher: counts requestAnimationFrame gaps while a benchmark runs.
const watchFrames = () => {
  let last = performance.now();
  let frames = 0, dropped = 0, longest = 0, running = true;
  const tick = () => {
    if (!running) return;
    const now = performance.now();
    const gap = now - last;
    last = now;
    frames++;
    if (gap > 16.7 * 1.5) dropped += Math.round(gap / 16.7) - 1;
    longest = Math.max(longest, gap);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  return () => { running = false; return { frames, dropped, longestGapMs: Math.round(longest) }; };
};

const stats = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  const q = (p: number) => s[Math.min(s.length - 1, Math.ceil(p * s.length) - 1)];
  return { median: +q(0.5).toFixed(1), p90: +q(0.9).toFixed(1), min: +s[0].toFixed(1), max: +s[s.length - 1].toFixed(1) };
};

export const bench = (mode: 'sync' | 'async', runs: number) =>
  Effect.gen(function* () {
    const sql = yield* SqlClient.SqlClient;
    const query = sql<{ data: string }>`SELECT data FROM cases ORDER BY created_at DESC`;
    const q = mode === 'async' ? SqliteClient.withAsyncQuery(query) : query;
    yield* Effect.promise(() => new Promise<void>(r => setTimeout(r, 300)));
    const stop = watchFrames();
    const total: number[] = [], queryMs: number[] = [], decodeMs: number[] = [];
    let count = 0;
    for (let i = 0; i < runs; i++) {
      const t0 = performance.now();
      const rows = yield* q;
      const t1 = performance.now();
      const cases = yield* decodeCases(rows.map(r => JSON.parse(r.data)));
      const t2 = performance.now();
      count = cases.length;
      total.push(t2 - t0); queryMs.push(t1 - t0); decodeMs.push(t2 - t1);
      yield* Effect.promise(() => new Promise<void>(r => setTimeout(r, 50)));
    }
    const frames = stop();
    log('bench', { mode, runs, count, total: stats(total), query: stats(queryMs), decode: stats(decodeMs), jsFrames: frames });
  });

// op-sqlite behaviour checks for the 17 vs 18 comparison.
export const checks = Effect.gen(function* () {
  const sql = yield* SqlClient.SqlClient;
  yield* sql`CREATE TABLE IF NOT EXISTS check_t (v TEXT NOT NULL)`;
  yield* sql`DELETE FROM check_t`;
  const count = sql<{ c: number }>`SELECT count(*) AS c FROM check_t`.pipe(Effect.map(r => r[0].c));
  const result: Record<string, unknown> = {};
  // 1. commit
  yield* sql.withTransaction(sql`INSERT INTO check_t (v) VALUES ('a')`);
  result.commit = (yield* count) === 1;
  // 2. rollback on failure
  yield* sql.withTransaction(Effect.andThen(sql`INSERT INTO check_t (v) VALUES ('b')`, Effect.fail('boom'))).pipe(Effect.ignore);
  result.rollback = (yield* count) === 1;
  // 3. savepoint: inner fails and is caught, outer commits
  yield* sql.withTransaction(
    Effect.gen(function* () {
      yield* sql`INSERT INTO check_t (v) VALUES ('outer')`;
      yield* sql.withTransaction(Effect.andThen(sql`INSERT INTO check_t (v) VALUES ('inner')`, Effect.fail('inner boom'))).pipe(Effect.ignore);
    }),
  );
  const vs = (yield* sql<{ v: string }>`SELECT v FROM check_t ORDER BY rowid`).map(r => r.v);
  result.savepoint = JSON.stringify(vs) === JSON.stringify(['a', 'outer']);
  // 4. withAsyncQuery, alone and inside a transaction
  result.asyncQuery = (yield* SqliteClient.withAsyncQuery(count)) === 2;
  yield* SqliteClient.withAsyncQuery(
    sql.withTransaction(Effect.andThen(sql`INSERT INTO check_t (v) VALUES ('async')`, Effect.fail('x'))),
  ).pipe(Effect.ignore);
  yield* SqliteClient.withAsyncQuery(sql.withTransaction(sql`INSERT INTO check_t (v) VALUES ('async-ok')`));
  result.asyncTransaction = (yield* count) === 3;
  result.values = (yield* sql<{ v: string }>`SELECT v FROM check_t ORDER BY rowid`).map(r => r.v);
  const [{ cipher_version }] = yield* sql<{ cipher_version: string }>`PRAGMA cipher_version`;
  result.cipherVersion = cipher_version;
  const [{ sqlite_version }] = yield* sql<{ sqlite_version: string }>`SELECT sqlite_version() AS sqlite_version`;
  result.sqliteVersion = sqlite_version;
  log('checks', result);
});

// Writes two probe databases to the app's external files dir, which `adb pull` can read
// on a non-debuggable release build: one with the key (should be unreadable by sqlite3),
// one without (positive control).
export const cipherProbe = Effect.gen(function* () {
  const key = yield* getOrCreateKey;
  const write = (name: string, encryptionKey?: string) => {
    const db = open({ name, location: ANDROID_EXTERNAL_FILES_PATH, ...(encryptionKey ? { encryptionKey } : {}) });
    db.executeSync('CREATE TABLE IF NOT EXISTS probe (v TEXT)');
    db.executeSync("INSERT INTO probe (v) VALUES ('DELMIR-SECRET-MARKER')");
    db.close();
  };
  write('cipher-probe.db', cipherKey(key));
  write('plain-probe.db');
  log('cipher-probe', { dir: ANDROID_EXTERNAL_FILES_PATH, keyHex: key });
});

// Both migration runners on fresh encrypted scratch databases: apply, then re-run (must apply nothing).
export const migrationsCheck = Effect.gen(function* () {
  const key = yield* getOrCreateKey;
  for (const name of Object.keys(runners)) {
    yield* Effect.gen(function* () {
      const sql = yield* SqlClient.SqlClient;
      const first = yield* runners[name](migrations);
      const second = yield* runners[name](migrations);
      const objects = (yield* sql<{ name: string }>`SELECT name FROM sqlite_master ORDER BY name`).map(r => r.name);
      log('migrations', { runner: name, first, second, objects });
    }).pipe(
      Effect.provide(SqliteClient.layer({ filename: `migrate-check-${name}-${Date.now()}.db`, encryptionKey: cipherKey(key) })),
      Effect.tapCause(cause => Effect.sync(() => log('migrations-failed', { runner: name, cause: String(cause) }))),
      Effect.ignore,
    );
  }
});
