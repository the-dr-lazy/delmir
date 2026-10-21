# How a bare React Native Android app reports OpenTelemetry, and to what backend

Research for [#18](https://github.com/the-dr-lazy/delmir/issues/18), feeding the decision ticket [#27 What does DELMIR report through OpenTelemetry, and where to?](https://github.com/the-dr-lazy/delmir/issues/27) and the "experiment tracking for training runs" fog on map [#1](https://github.com/the-dr-lazy/delmir/issues/1). Researched 2026-10-21 against primary sources: source code at pinned commits, official docs, npm and Maven metadata, and the nixpkgs tree. Nothing here was tried on a device or a server; the claims a spike should confirm are marked **unverified**.

## Answer

**On the phone, run two exporters that share a `service.name` and a `session.id`. Neither uses the OpenTelemetry JS SDK.**

- **JS side.**
  - **What to use.** Effect 4's own OTLP exporters, in core `effect` 4.0.5 under `effect/observability`: `OtlpTracer`, `OtlpLogger` and `OtlpMetrics`. Use `OtlpSerialization.layerJson` over `FetchHttpClient`.
  - **No polyfills on React Native ≥ 0.74 with Hermes.** IDs come from `Math.random`, and Hermes has a native `TextEncoder`.
  - **No gzip.** Hermes has no `CompressionStream`, and the exporter treats a compression failure as a transport failure.
  - **Not `@effect/opentelemetry`.** It bridges to the OpenTelemetry JS SDK and is pinned to OTel JS 2.x, whose `sdk-trace-base` and `sdk-trace-web` packages OTel JS 3.0.0 removed.
  - **OpenTelemetry JS does not support React Native.** There is no official React Native package or SIG.
- **Native side.**
  - **What to use.** opentelemetry-android 1.7.0 (`android-agent`), initialised in `MainApplication.onCreate`.
  - **Turn on:** JVM crashes, ANRs, sessions, slow rendering, startup, disk buffering and the opt-in `native-crash` module.
  - **Turn off:** network-change (records the carrier), view-click (records tap coordinates) and any OkHttp or HttpURLConnection instrumentation (records URLs).
  - **JS fatal errors reach its crash handler** as a `JavascriptException` that carries the full JS message.
  - **Crashes in C++ (ONNX Runtime, Hermes)** give only "signal N at time T in session S" on the next launch, with no stack.
- **Offline is the gap.**
  - **What Effect does on failure.** After three transient retries the exporter drops the batch and turns itself off for 60 s. Nothing is written to disk.
  - **The fix: an "OTLP outbox".** Give Effect a custom `HttpClient` that hands each encoded OTLP payload to a native file queue and returns 200 at once. A Kotlin WorkManager job then posts the queue to the server when the phone is online.
  - **Native signals** already have opentelemetry-android's disk buffer.
- **No patient data, in three layers.**
  1. **At the source.**
     - Error messages are constant, and patient values are wrapped in `Redacted`. Effect copies every failure's `message` and stack into spans and logs on its own.
     - A custom `OtlpSerialization` layer keeps only allow-listed attribute keys. It also replaces exception messages with error tags and log bodies with template IDs.
     - On Android, a pre-disk `SpanProcessor` and `LogRecordProcessor` scrub `exception.message`. Exporter wrappers run after the disk write, so they are too late.
  2. **At the collector.**
     - `transform` `keep_keys` on resource and data-point attributes.
     - A `redaction` allow-list. An empty `allowed_keys` keeps no attributes.
     - Scrubbing of span names and log bodies.
     - `filter` to drop unknown services.
  3. **At the boundary.** The collector is the only way in; every store listens on localhost. A test feeds fake PII through the collector config and checks that none comes out.

**Backend: the OpenTelemetry Collector (contrib build), Grafana Tempo, Loki, Prometheus and Grafana, all from nixpkgs with NixOS modules.**

- **Collector package.** Set `services.opentelemetry-collector.package = pkgs.opentelemetry-collector-contrib`. The module defaults to the core build, which has no `transform`, `redaction`, auth or `file_storage`.
- **Signal stores.** Prometheus takes OTLP natively with `--web.enable-otlp-receiver`; Mimir isn't needed for one user. Loki takes OTLP at `/otlp`.
- **Crashes** are log records carrying `exception.type` and `exception.stacktrace`. Grafana has no grouped exceptions inbox, so a dashboard grouped by `exception.type` stands in for one.
- **Runner-up: OpenObserve.** It is packaged, one AGPL binary, but has no NixOS module.
- **Rejected:**
  - **SigNoz and ClickStack/HyperDX:** not packaged, they need ClickHouse plus Postgres or MongoDB, and their docs ask for ≥ 4 GB RAM.
  - **Jaeger:** not packaged, and it stores traces only.

**Transport: Tailscale.**

- **How.** `tailscale serve --bg --https=443 localhost:4318` puts the collector on `https://<host>.<tailnet>.ts.net` behind a publicly trusted Let's Encrypt certificate. Android 9+ blocks cleartext and ignores user CAs, and this needs neither exception.
- **Machine names are public.** They appear in Certificate Transparency logs, so keep them non-sensitive.
- **Second check.** A `bearertokenauth` token on the collector's receiver.
- **Headscale** works but loses ts.net certificates and needs a public control server.
- **Plain WireGuard** works but needs your own certificate or a cleartext exception.

**Experiment tracking: share the host, Prometheus and Grafana, but not the stores.**

- **Why not the OTel stores.** A metrics TSDB indexes by wall-clock time, not training step. Every run ID or hyperparameter set as a label is a new series, which Prometheus warns against. It also has no params, artifacts (checkpoints, ONNX files) or run comparison.
- **What to use: MLflow** (`mlflow-server` 3.17.1 in nixpkgs, Apache-2.0, no NixOS module, so a small systemd unit). Store runs in SQLite with a local artifact directory, published through `tailscale serve` like the collector.
  - MLflow's OTLP endpoint takes traces only, for GenAI tracing, so it does not unify the two.
- **GPU telemetry goes into the shared Prometheus** through node_exporter's `drm` collector (off by default, AMD only) and `hwmon` (temperature, power, fan, clocks). AMD's device-metrics-exporter does not support the RX 6600 XT.

## What a spike must confirm

- **Effect 4 itself on Hermes in a bare Android build.** A community report on [Effect-TS/effect#6252](https://github.com/Effect-TS/effect/issues/6252) says it works with Babel tweaks: `import.meta` → `{}`, export-namespace-from, and object-rest-spread on `effect` sources. This belongs to [#17](https://github.com/the-dr-lazy/delmir/issues/17) and [#26](https://github.com/the-dr-lazy/delmir/issues/26).
- **Whether JS fatal errors under the New Architecture (bridgeless)** still reach `ExceptionsManagerModule`, and so opentelemetry-android's crash handler.
- **Whether nixpkgs' Tempo 3.1.0 runs monolithic** with the current `services.tempo` defaults, and the stack's real RAM footprint. The rough estimate is 1–1.5 GB, unverified.
- **Whether the `redaction` processor touches resource attributes.** Until then, also run `transform` `keep_keys` on `resource.attributes`.
- **If a symbolicated C++ backtrace matters,** whether Crashpad or Breakpad minidumps are worth adding. Not researched.

## Sources and detail

The two parts below are the full findings, with a source for every claim. Part A covers the phone and Part B the server.

## Part A: the phone (Effect, OpenTelemetry JS, opentelemetry-android)


Research date: 2026-10-21. Primary sources only. "unverified" marks claims I could not confirm in a primary source.

Abbreviations used for pinned sources:

- **EFX** = `Effect-TS/effect` at commit `bc873ec4951dff0238ddcfb5b60e0e533b647bcc` (main on 2026-10-21; `packages/effect/package.json` there says `"version": "4.0.5"`). Base URL: `https://github.com/Effect-TS/effect/blob/bc873ec4951dff0238ddcfb5b60e0e533b647bcc/`
- **OTA** = `open-telemetry/opentelemetry-android` at tag `v1.7.0`. Base URL: `https://github.com/open-telemetry/opentelemetry-android/blob/v1.7.0/`
- **RN** = `facebook/react-native` at tag `v0.88.0`. Base URL: `https://github.com/facebook/react-native/blob/v0.88.0/packages/react-native/`

### Current versions (as of 2026-10-21)

| Thing | Version | Source |
|---|---|---|
| `effect` (npm `latest`) | 4.0.5, published 2026-10-15. Effect 3 is now the `prev` tag (3.22.3). | https://registry.npmjs.org/effect |
| `@effect/opentelemetry` | 4.0.5, published 2026-10-15 | https://registry.npmjs.org/@effect/opentelemetry |
| Effect v4 source | Now lives in **`Effect-TS/effect` main**. `Effect-TS/effect-smol` is the older v4 incubator; its last push was 2026-07-14, and it still has the modules under `src/unstable/observability`. | `gh api repos/Effect-TS/effect-smol` (pushed_at); EFX tree |
| React Native | 0.88.0, released 2026-10-15 | https://github.com/facebook/react-native/releases/tag/v0.88.0 |
| opentelemetry-android | v1.7.0, released 2026-09-04. `android-agent` 1.7.0 is stable; the BOM, `core` and instrumentations are `1.7.0-alpha`. | https://github.com/open-telemetry/opentelemetry-android/releases/tag/v1.7.0 ; https://repo1.maven.org/maven2/io/opentelemetry/android/android-agent/maven-metadata.xml ; https://repo1.maven.org/maven2/io/opentelemetry/android/opentelemetry-android-bom/maven-metadata.xml |
| OTel JS | `@opentelemetry/sdk-trace` 3.0.0 (2026-10-20). `sdk-trace-base` and `sdk-trace-web` 2.12.0 are **deprecated** ("Use @opentelemetry/sdk-trace package"). `exporter-trace-otlp-http` is 0.300.0. | https://registry.npmjs.org/@opentelemetry/sdk-trace ; https://registry.npmjs.org/@opentelemetry/sdk-trace-base ; https://github.com/open-telemetry/opentelemetry-js/blob/main/CHANGELOG.md (3.0.0) |
| OTel Java contrib disk-buffering | 1.61.0-alpha | https://repo1.maven.org/maven2/io/opentelemetry/contrib/opentelemetry-disk-buffering/maven-metadata.xml |

---

### 1. Exporting Effect tracing, metrics and logs over OTLP

#### 1.1 Where the code lives in Effect 4

- The lightweight OTLP exporters are **in core `effect`**, imported from **`effect/observability`**. They are no longer `unstable`.
  - Modules: `Otlp`, `OtlpExporter`, `OtlpTracer`, `OtlpLogger`, `OtlpMetrics`, `OtlpResource`, `OtlpSerialization`, `PrometheusMetrics`.
  - Export map entry: `"./observability": "./src/observability/index.ts"`.
  - Source: EFX `packages/effect/src/observability/` and EFX `packages/effect/package.json` (exports).
  - Every module is still tagged `@stability unstable` in its JSDoc (EFX `packages/effect/src/observability/OtlpExporter.ts`, header).
- In effect-smol (the older v4 prerelease line) the same modules were at `effect/unstable/observability/*` (https://github.com/Effect-TS/effect-smol/tree/main/packages/effect/src/unstable/observability).
- They do **not** depend on the OTel JS SDK. They build OTLP payloads themselves and POST them through Effect's own `HttpClient` (EFX `packages/effect/src/observability/OtlpExporter.ts`, imports and `make`).
- `@effect/opentelemetry` 4.0.5 is the other route. It is the bridge to the real OTel JS SDK and offers `NodeSdk`, `WebSdk`, `OtelTracer`, `OtelLogger`, `OtelMetrics` and `Resource` (EFX `packages/opentelemetry/src/`).
  - Its README says "The relevant `@opentelemetry/*` SDK packages are required as peer dependencies" (EFX `packages/opentelemetry/README.md`).
  - Its peer ranges are `@opentelemetry/sdk-trace-base|web|node >=2.0.0 <3.0.0` (EFX `packages/opentelemetry/package.json`).
  - **Gotcha:** OTel JS 3.0.0 (2026-10-20) *removed* `sdk-trace-base`, `sdk-trace-web` and `sdk-trace-node` in favour of `@opentelemetry/sdk-trace` (https://github.com/open-telemetry/opentelemetry-js/blob/main/CHANGELOG.md, "3.0.0", #7117 and #7054). So `@effect/opentelemetry` 4.0.5 is pinned to the 2.x line. For DELMIR this is one more reason to use the native `effect/observability` modules.

#### 1.2 API surface (EFX `packages/effect/src/observability/Otlp.ts`)

- `Otlp.layer(options)` merges `OtlpLogger.layer`, `OtlpMetrics.layer` and `OtlpTracer.layer`.
  - It derives the signal URLs from `baseUrl` + `/v1/logs`, `/v1/metrics` and `/v1/traces`.
  - It requires `HttpClient.HttpClient | OtlpSerialization.OtlpSerialization`.
- `Otlp.layerJson(options)` and `Otlp.layerProtobuf(options)` are the same layer with `OtlpSerialization.layerJson` or `.layerProtobuf` pre-provided. They still need an `HttpClient`.
- `Otlp.layerFromConfig` reads the standard `OTEL_*` environment variables through `Config`. Examples: `OTEL_SDK_DISABLED`, `OTEL_EXPORTER_OTLP_*`, `OTEL_BSP_SCHEDULE_DELAY`, `OTEL_BSP_MAX_EXPORT_BATCH_SIZE`, `OTEL_RESOURCE_ATTRIBUTES` and `OTEL_SERVICE_NAME` (EFX `OtlpTracer.ts` around lines 166–220; EFX `OtlpResource.ts`). This is not useful on a phone; use explicit `layer`.
- Options:
  - `baseUrl`
  - `resource {serviceName, serviceVersion, attributes}`
  - `headers`
  - `compression: "gzip" | "none"`
  - `maxBatchSize`
  - `tracerContext`
  - `loggerExportInterval`, `loggerExcludeLogSpans`, `loggerMergeWithExisting`
  - `metricsExportInterval`, `metricsTemporality`
  - `tracerExportInterval`
  - `shutdownTimeout`
- Canonical usage (EFX `ai-docs/src/08_observability/20_otlp-tracing.ts`):
  ```ts
  import { FetchHttpClient } from "effect/http"
  import { OtlpLogger, OtlpSerialization, OtlpTracer } from "effect/observability"
  const Observability = Layer.merge(OtlpTracer.layer({ url, resource }), OtlpLogger.layer({ url, resource }))
    .pipe(Layer.provide(OtlpSerialization.layerJson), Layer.provide(FetchHttpClient.layer))
  ```

#### 1.3 Transport, encoding, batching and shutdown

- **Transport.** Requests go through Effect `HttpClient`. On RN you provide `FetchHttpClient.layer` (from `effect/http`). Its `Fetch` reference defaults to `globalThis.fetch` (EFX `packages/effect/src/http/FetchHttpClient.ts` line 36). The exporter uses the client like this (EFX `OtlpExporter.ts` lines 196–204):
  - It drains every response body.
  - It applies `filterStatusOk`.
  - It disables trace propagation on its own requests.
  - It uses `retryTransient({ schedule: policy, times: 3 })`. The policy waits 1 s, honours `Retry-After` on 429, and otherwise waits 5 s (lines 31–63).
  - Exporter calls run with `Effect.withTracerEnabled(false)`, so exports do not trace themselves.
- **Encoding.** `OtlpSerialization.layerJson` sends `application/json` via `JSON.stringify`, with NaN and Infinity written as strings. `layerProtobuf` sends `application/x-protobuf` using a hand-written encoder in `internal/otlpProtobuf.ts`, so there is no protobufjs dependency (EFX `OtlpSerialization.ts` lines 54–84).
- **Compression.** Optional gzip uses `HttpClientRequest.compressBody` and "requires runtime `CompressionStream` support". Per the JSDoc, "compression failures follow the same temporary-disable behavior as transport failures" (EFX `OtlpExporter.ts`, JSDoc of `make`).
  - Hermes: searching facebook/hermes commits for `CompressionStream` returns 0 hits. Treat it as **absent** on Hermes, which means **do not enable gzip on RN** or the exporter will keep disabling itself. "Absent in RN" is unverified beyond the commit search.
- **Batching and intervals** (all from EFX):
  - Tracer: `exportInterval` defaults to **5 s**, `maxBatchSize` to **1000**, `shutdownTimeout` to **3 s** (`OtlpTracer.ts` lines 85–99).
  - Logger: interval **1 s**, batch 1000, shutdown 3 s (`OtlpLogger.ts` lines 82–96).
  - Metrics: interval **10 s**, `exportEmpty: true`, temporality default `"cumulative"`, shutdown 3 s (`OtlpMetrics.ts` lines 109 and 399–402).
  - The buffer is an unbounded in-memory array, flushed when the interval elapses or `maxBatchSize` is reached (`OtlpExporter.ts` lines 224–285).
- **Shutdown and flush.**
  - When the exporter's `Scope` closes, a finalizer runs one last export, bounded by `shutdownTimeout` (`OtlpExporter.ts` lines 258–268).
  - There is also an explicit **`OtlpExporter.Flusher`** service (`layerFlusher`). It drains all registered exporters (traces, logs and metrics) together and "cannot fail"; you bound it with `Effect.timeoutOption` (`OtlpExporter.ts` lines 65–160).
  - On a phone, call `flusher.flush` when RN `AppState` goes to `background`, because the process can be killed without the scope ever closing. This is a design inference, not something stated in the source.
- **Resource attributes** (EFX `OtlpResource.ts`):
  - Always set: `telemetry.sdk.name="effect"`, `telemetry.sdk.language` and `telemetry.sdk.version`.
  - `service.name` and `service.version` come from the options. Extra `attributes` are merged in.
  - `telemetry.sdk.language` is `"webjs"` if `"window" in globalThis` (line 32), otherwise `"nodejs"`. RN defines `globalThis.window` (RN `Libraries/Core/setUpGlobals.js` lines 18–20), so on RN it reports `webjs`. Override it via attributes if that matters.
- **Trace context in logs.** `OtlpLogger` copies the current span's `traceId` and `spanId` onto each log record, plus all log annotations, `effect.fiberId` and log-span durations (`OtlpLogger.ts` `makeLogRecord`, around lines 228–268).

#### 1.4 Does it run on Hermes? Runtime requirements I found in the source

| Need | Where Effect uses it | Hermes / RN status |
|---|---|---|
| `fetch` | `FetchHttpClient` uses `globalThis.fetch` | RN provides `fetch`, `Headers`, `Request` and `Response` via the `whatwg-fetch` polyfill over XHR (RN `Libraries/Network/fetch.js`). |
| Random IDs | `Hex.random(32)` for the trace id and `Hex.random(16)` for the span id (EFX `OtlpTracer.ts` lines 267–272). They use **`Math.random()`** (EFX `packages/effect/src/encoding/Hex.ts` line 74, documented as "not cryptographically secure"). | **No `crypto.getRandomValues` needed** for the Effect exporters, so no `react-native-get-random-values`. |
| `TextEncoder` | `Hex.ts` builds one at module load (`const encoder = new TextEncoder()`, line 246). The protobuf encoder uses `new TextEncoder().encode` (`internal/protobuf.ts` line 85). | Hermes ships a native `TextEncoder`: `encode`, `encodeInto` and `encoding` were added in Feb 2024 (facebook/hermes commits `36d0e12656`, `d3b34bb26c`, `d9eda00503`; `lib/VM/JSLib/TextEncoder.cpp` exists on main). OTel contributors report that RN 0.73 needed a polyfill and **RN ≥ 0.74 does not** (https://github.com/open-telemetry/opentelemetry-js/issues/5178#issuecomment-2492001424). Hermes has **no `TextDecoder`** (`lib/VM/JSLib/TextDecoder.cpp` returns 404 on main). The exporters do not need it as far as I saw. |
| `BigInt` | The clock is nanosecond `bigint` throughout, and the protobuf varint encoder uses BigInt (EFX `internal/effect.ts` around line 6363; `internal/protobuf.ts` lines 32–38). | Hermes supports BigInt. That Effect v4 runs on Hermes is reported in #6252 below. The exact RN version that introduced BigInt support is unverified. |
| Monotonic time | `process.hrtime.bigint` → `performance.now()` → a monotonic `Date.now()` fallback (EFX `internal/effect.ts` lines 6365–6382) | RN has `performance.now()`. The OTel demo notes that RN 0.83's Performance API supports only the "mark" and "measure" entry types (https://github.com/open-telemetry/opentelemetry-demo/blob/main/src/react-native-app/hooks/useTracer.ts). `now()` itself is fine. |
| `FinalizationRegistry` | Optional; `HttpClient` feature-detects it (EFX `http/HttpClient.ts` line 1849) | Not required. |
| `AbortController` / `AbortSignal.any` | `AbortSignal.any` is used only for **streaming** request bodies (EFX `FetchHttpClient.ts` lines 80–127). OTLP bodies are text or `Uint8Array`. | Not needed for OTLP. |
| `CompressionStream` | gzip only | Absent; don't use gzip (see above). |

- **Binary bodies on RN.** RN XHR converts an `ArrayBuffer` or `ArrayBufferView` body to base64 to cross the bridge (RN `Libraries/Network/convertRequestBody.js`). Protobuf therefore probably works but adds bridge overhead.
  - OTel JS users saw "Base64 encoded" OTLP bodies on RN 0.73 (https://github.com/open-telemetry/opentelemetry-js/issues/5178).
  - **Prefer `layerJson` on RN.** Protobuf-on-RN correctness is unverified.
- **Effect v4 on RN in general.** Issue https://github.com/Effect-TS/effect/issues/6252 ("Can't use Effect with React Native", closed 2026-07-23) has a community comment (2026-07-23) reporting "Effect v4 family works well" on react-native-macos 0.87 / Hermes. The comment's Babel config:
  - replaces `import.meta` with `{}`;
  - adds `@babel/plugin-transform-export-namespace-from`;
  - applies `@babel/plugin-transform-object-rest-spread` to `effect`/`@effect/*` sources.

  This is a community report, not official support, so it is unverified for bare RN Android. Also see #6347: Migrator dynamic imports are incompatible with RN (https://github.com/Effect-TS/effect/issues/6347).
- **Polyfills summary for RN ≥ 0.74 + Hermes + Effect OTLP exporters.** None required for the exporters; I found no RN-specific requirement for `react-native-get-random-values` in these modules. You still need the Babel tweaks above for Effect v4 itself (community-reported).

#### 1.5 What Effect does when an export fails

EFX `OtlpExporter.ts` lines 222–247 and 278–284:

1. After the transient retries are exhausted, or on a non-2xx response, the `catchCause` handler **clears the buffer (drops the batch)**.
2. It sets `disabledUntil = now + 60_000`, so **the exporter is disabled for 60 s**. While disabled, `push` silently **drops** new data and both `flush` and the shutdown finalizer are skipped.
3. Nothing is persisted. **Offline means data loss**, so see §4.

---

### 2. Upstream OTel JS SDKs on React Native, plus vendor SDKs

#### 2.1 Official status

- **There is no official OTel React Native SDK, package or SIG** as of 2026-10-21.
  - The `open-telemetry` org has no RN repository. A repo search for "react native" returns only opentelemetry-js, opentelemetry-dotnet, opentelemetry-cpp, **opentelemetry-browser** and semantic-conventions-client-side.
  - The SIG list has "Client Instrumentation", "Android", "Browser" and "Swift", but no RN SIG (https://github.com/open-telemetry/community/blob/main/README.md).
  - `@opentelemetry/react-native` does not exist on npm.
- The OTel JS maintainer wrote: "please note that React Native is not officially supported by this project" (https://github.com/open-telemetry/opentelemetry-js/issues/5240#issuecomment-2536711768).
- The long-running issue "Support for react-native environment" (https://github.com/open-telemetry/opentelemetry-js/issues/1089) is still **open**; last updated 2026-04-17.
- opentelemetry-android's roadmap lists RN and Flutter as an "integration gap … we should improve one day" and says cross-stack context sharing "should be made possible one day" (OTA `docs/ROADMAP.md` around lines 238–248). Issue #696 "react native mode in demo app" is open (https://github.com/open-telemetry/opentelemetry-android/issues/696).
- **Closest thing to an official reference:** the OTel Demo's `src/react-native-app` (Expo 58, RN 0.88.0). Its setup (https://github.com/open-telemetry/opentelemetry-demo/blob/2c4be61741536937f1486ecaf74f44dbfd15d707/src/react-native-app/hooks/useTracer.ts and `package.json`):
  - `@opentelemetry/sdk-trace` ^2.12 with `TracerProvider`, `BatchSpanProcessor` and `StackContextManager`;
  - `exporter-trace-otlp-http` ^0.223;
  - fetch and XHR instrumentations;
  - `react-native-get-random-values` ~2.0.0, needed by OTel JS ID generation (inference);
  - a hand-written `SessionIdProcessor`.

  Gotchas called out in its comments:
  - It must set `propagateTraceHeaderCorsUrls: /.*/` and `clearTimingResources: false` to avoid the web-only Performance API.
  - It patches `performance.getEntriesByType` to silence RN warnings.
  - RN `fetch` is a polyfill over XHR, so instrumenting both produces duplicate spans.
  - There is "TODO … a resource detector for React Native" and "TODO … a React Native session processor package".
- Other RN gotchas with the OTel JS SDK:
  - `@opentelemetry/resources` Node detectors try to import `os` unless Metro resolves the `browser` field (#5240).
  - TextEncoder is missing on RN < 0.74 (#5178).
  - Honeycomb's RN README requires `config.resolver.unstable_enablePackageExports` in Metro for OTel imports (https://github.com/honeycombio/honeycomb-opentelemetry-react-native/blob/main/README.md).
- **Browser OTLP exporter transport.** `@opentelemetry/otlp-exporter-base` browser builds are now **fetch-only**:
  - The XHR transport was removed in **0.211.0** (#6317).
  - `sendBeacon` was removed "in favor of fetch with keepalive" in **0.214.0** (#6391).
  - `createOtlpSendBeaconExportDelegate` now just returns the fetch delegate.
  - Retries go through `createRetryingTransport`.

  Sources: https://github.com/open-telemetry/opentelemetry-js/blob/main/experimental/CHANGELOG.md ; https://github.com/open-telemetry/opentelemetry-js/blob/main/experimental/packages/otlp-exporter-base/src/platform/browser/otlp-browser-http-export-delegate.ts. On RN, `fetch` is whatwg-fetch over XHR, and `keepalive` is meaningless there (inference).
- Also in 0.300.0, `@opentelemetry/instrumentation-fetch` and `instrumentation-xml-http-request` are **soft-deprecated** (#7109, same CHANGELOG).

#### 2.2 Vendor and community RN SDKs (licence, OTLP to an arbitrary endpoint)

| SDK (npm) | Version | Licence | Basis | Arbitrary OTLP endpoint? | Notes |
|---|---|---|---|---|---|
| `@embrace-io/react-native` + `@embrace-io/react-native-otlp` | 7.2.0 | Apache-2.0 | Embrace native Android/iOS SDKs (OTel-based) plus a JS layer | Yes: traces and logs to any OTLP/HTTP endpoint. Docs say you can initialise **without an app_id/token** to send only to your own backend; on Android, also set `embrace.disableMappingFileUpload=true` (https://embrace.io/docs/react-native/features/otlp/ ; Embrace docs search summary, the native-Android-only flow is unverified). | The `react-native-otlp` JS package is **deprecated**: "start Embrace in native code and configure OTLP export in the native SDKs" (https://github.com/embrace-io/embrace-react-native-sdk/blob/main/packages/react-native-otlp/README.md). Native exporters are attached via `Embrace.addJavaSpanExporter` / `addJavaLogRecordExporter`. The export URL must go in `disabled_url_patterns` to avoid export loops. Whether crashes are exported over OTLP is not stated (unverified). |
| `@honeycombio/opentelemetry-react-native` | 0.8.0 | MIT | OTel JS (built on the Honeycomb web SDK) + `honeycomb-opentelemetry-android` + `io.opentelemetry.android:android-agent` | Options defer to the Honeycomb Web SDK, which (unverified) accepts a custom `endpoint`. | README: "**STATUS: this library is experimental.**" Default auto-instrumentation: uncaught-exception handler, fetch, slow event loop, RN startup. Source-map symbolication goes through Honeycomb's collector symbolicator (https://github.com/honeycombio/honeycomb-opentelemetry-react-native/blob/main/README.md). |
| `@splunk/otel-react-native` | 1.3.0 | Apache-2.0 | OTel JS | Only partly: it exports via **Zipkin**, and "Adding your own exporters and processors isn't supported yet". `beaconEndpoint` can override the realm URL. | BETA (https://github.com/signalfx/splunk-otel-react-native/blob/main/README.md). |
| `@grafana/faro-react-native` (+ `-tracing`) | 1.4.2 | Apache-2.0 | Faro (not pure OTLP); tracing package exports OTLP to the Faro backend | Self-hostable: Grafana Alloy `faro.receiver` accepts Faro payloads and can forward traces to `otelcol.exporter.otlphttp`; logs go to Loki (https://grafana.com/docs/alloy/latest/reference/components/faro/faro.receiver/). | Has an `offline` transport, `anrTracking` (Android, default off) and `enableCrashReporting` (default off). Native crashes on Android 11+ are "reported on the next launch" and retried for up to 7 days. Console capture and user-action tracking are **on by default**, a privacy risk (https://github.com/grafana/faro-react-native-sdk/blob/main/packages/react-native/README.md). |
| `@launchdarkly/observability-react-native` | 0.18.0 | Apache-2.0 | (not investigated) | unverified | https://registry.npmjs.org/@launchdarkly/observability-react-native/latest |

Licences and versions come from `https://registry.npmjs.org/<pkg>/latest`, fetched 2026-10-21.

---

### 3. Native crash and ANR capture with opentelemetry-android

#### 3.1 Basics

- **Version.** v1.7.0 (2026-09-04), "based on OpenTelemetry Java Instrumentation 2.31.1 and the OpenTelemetry Java Core 1.65.0". Many artifacts are still `-alpha` (https://github.com/open-telemetry/opentelemetry-android/releases/tag/v1.7.0).
- **Min SDK.** The badge says API 23. If `minSdk < 26` you must enable core-library desugaring, use AGP 8.3.0+ and set `android.useFullClasspathForDexingTransform=true` (OTA `README.md`).
- **Gradle** (the OTA README still shows `1.6.0-alpha`; the current BOM is `1.7.0-alpha` per Maven Central):
  ```kotlin
  // android/app/build.gradle(.kts) in the bare RN project
  implementation(platform("io.opentelemetry.android:opentelemetry-android-bom:1.7.0-alpha"))
  implementation("io.opentelemetry.android:android-agent")
  implementation("io.opentelemetry.android.instrumentation:native-crash:1.7.0-alpha") // opt-in
  ```
- **Initialisation.** Call `OpenTelemetryRumInitializer.initialize(context) { httpExport { baseUrl = … }; instrumentations { … }; session { … }; globalAttributes { … }; resource { … }; diskBuffering { enabled(true) }; semanticConventions { … }; disableMetrics() }` in `Application.onCreate()`; in a bare RN app that is `MainApplication.kt`.
  - Sources: OTA `README.md`; OTA `android-agent/src/main/kotlin/io/opentelemetry/android/agent/dsl/OpenTelemetryConfiguration.kt`.
  - It returns `OpenTelemetryRum`, which exposes `openTelemetry`, `sessionProvider`, `clock`, `emitEvent(...)` and `shutdown()` (OTA `agent-api/src/main/java/io/opentelemetry/android/OpenTelemetryRum.kt`).
  - `httpExport` builds `OtlpHttpSpanExporter`, `OtlpHttpLogRecordExporter` and `OtlpHttpMetricExporter` (OTA `OpenTelemetryRumInitializer.kt` lines 57–110). v1.4.0 added a `fullUrl` option to bypass signal-path appending.
- **Advanced composition** uses `OpenTelemetryRumBuilder` (core):
  - `addTracerProviderCustomizer`, `addLoggerProviderCustomizer`, `addMeterProviderCustomizer`;
  - `addSpanExporterCustomizer`, `addLogRecordExporterCustomizer`, `addMetricExporterCustomizer`;
  - `setSessionProvider`, `setExportScheduleEnablement`, `addOtelReadyListener`, `setResource` / `mergeResource`.

  Source: OTA `core/src/main/java/io/opentelemetry/android/OpenTelemetryRumBuilder.kt`.

#### 3.2 Bundled instrumentation

The agent bundles: activity, ANR, crash, fragment, network change, slow rendering, startup, sessions, screen orientation and view-click (OTA `README.md`). Optional modules (OTA `instrumentation/`) include `android-log`, `compose`, `httpurlconnection`, `okhttp3`, `okhttp3-websocket`, `native-crash`, `power-save-mode` and `thermal`. Instrumentations are found on the classpath and auto-installed. You can turn off auto-discovery with `disableInstrumentationAutoDiscovery()` (v1.6.0 release notes).

- **Crash (JVM).** Uncaught exceptions produce an `app.crash` event with `exception.message`, `exception.stacktrace`, `exception.type`, `thread.id` and `thread.name` (OTA `instrumentation/crash/README.md`). Stack traces are truncated to 1,000 lines (v1.5.0). v1.7.0: "Flush telemetry on crash before delegating to the previous uncaught exception handler".
- **ANR.** It polls the UI thread every 1 s; 5 consecutive failures emit a `device.anr` event with the main-thread `exception.stacktrace`. Foreground only (OTA `instrumentation/anr/README.md`).
- **Native crash (NDK signals), opt-in, "Status: development", added in v1.6.0.**
  - It handles `SIGILL`, `SIGTRAP`, `SIGABRT`, `SIGBUS`, `SIGFPE`, `SIGSEGV` and `SIGSYS`, writes a marker file (`signal.number`, `timestamp.epoch_nanos`), restores the previous handler and re-raises the signal.
  - On next launch it replays a single `app.crash` event with `exception.type`, `exception.message`, `session.id`, `service.version`, `os.name` and `os.version`.
  - Limitations:
    - "**Native stack capture is not included.** This module does not create or attach a binary crash dump."
    - Crashes before init are missed.
    - Replay is **at most once**: the marker is deleted right after emit.
    - Building it needs CMake ≥ 3.22.1.

    Source: OTA `instrumentation/native-crash/README.md`.
  - **So an ONNX Runtime SIGSEGV in C++ would be recorded as "a SIGSEGV happened at time T in session S", with no frames.**
  - A complementary platform API is Android 11+ `ApplicationExitInfo`, which Faro RN uses for native crashes on next launch (Faro README). Whether opentelemetry-android uses `ApplicationExitInfo` is unverified; I did not see it.
- **Slow rendering, network change, lifecycle and sessions.**
  - Slow rendering emits events only, no zero-duration spans (v1.4.0).
  - Network change emits a `network.change` event (§5.2).
  - Sessions emit `session.start` and `session.end`. Defaults: `backgroundInactivityTimeout` 15 min, `maxLifetime` 4 h (OTA `instrumentation/sessions/README.md`).

#### 3.3 Coexisting with JS telemetry in a bare RN app

- **Two SDKs, one backend.** The Effect exporters POST JSON OTLP from JS; opentelemetry-android POSTs from Kotlin. Both go to the same collector `baseUrl` with the same `service.name` and `service.version`. Correlate them with a shared **`session.id`**:
  - Expose `otelRum.sessionProvider.getSessionId()` (OTA `session/src/main/kotlin/io/opentelemetry/android/session/SessionProvider.kt`) through a small TurboModule.
  - Stamp it onto JS spans and logs. Because sessions rotate, stamp it per record rather than in the resource; the JS serialization hook in §5.1 is a good place.
  - Also share `app.installation.id` if wanted.
- **JS fatal errors and red-box errors.**
  - In RN, `ExceptionsManager.handleException` calls `reportException`. On Android, `ExceptionsManagerModule.reportException` **throws `JavascriptException(format(message, stack))` when `isFatal`** (RN `ReactAndroid/src/main/java/com/facebook/react/modules/core/ExceptionsManagerModule.kt` lines 46–60). The JVM uncaught-exception handler then sees it, so opentelemetry-android's crash instrumentation records it as `app.crash` with type `com.facebook.react.common.JavascriptException`, and the JS message and stack in `exception.message`.
  - Under the new architecture, `global.RN$handleException` may intercept the error first (RN `Libraries/Core/ExceptionsManager.js` lines 151–176). Whether bridgeless fatal errors still reach `ExceptionsManagerModule` is **unverified**.
  - For a JS-side record, wrap `ErrorUtils.getGlobalHandler()` / `ErrorUtils.setGlobalHandler()`:
    1. Synchronously hand a **sanitised** error record (type, a hashed or whitelisted message, a symbolicatable stack) to native through a sync TurboModule call that emits an OTel log via `openTelemetry.logsBridge`, which lands in the disk buffer.
    2. Then call the previous handler.

    Don't rely on the Effect exporter here. Its buffer is in memory and the process is about to die (design inference).
  - Red-box errors are dev-only. Non-fatal `console.error` calls go through `reactConsoleErrorHandler` and are only logged natively via `FLog.e`; they are not reported to OTel unless you hook them.
- **Native C++ crashes** (ONNX Runtime, Hermes): see 3.2. You get the signal number only, no backtrace. For symbolicated native crashes you would need an extra tool such as Crashpad or Breakpad minidumps. That was not researched, so it is unverified.

---

### 4. Offline buffering and batching on a phone

#### 4.1 What exists

- **Effect exporters:** in-memory only. After about 3 retries they **drop the batch and disable for 60 s** (§1.5). No persistence hook exists except the `HttpClient` they depend on (§4.2).
- **opentelemetry-android disk buffering** (OTA `docs/EXPORTER_CHAIN.md`; DiskBufferingConfig in OTA `core/src/main/java/io/opentelemetry/android/features/diskbuffering/DiskBufferingConfig.kt`):
  - Chain: `BufferDelegating*Exporter` (in memory, 5,000 items per signal until async init finishes) → `*ToDiskExporter` → your customised exporter chain → OTLP. A scheduler reads batches back through `SignalFromDiskExporter`.
  - Failed from-disk exports **stay on disk**, subject to age and size pruning.
  - If disk init fails, it falls back to no disk buffering.
  - Defaults:
    - max cache 10 MB, max file 1 MB;
    - file write window 30 s, min read age 33 s, max read age **18 h**;
    - export period 10 s.
  - The agent DSL's `diskBuffering {}` spec starts with `enabled = true` (OTA `android-agent/.../dsl/DiskBufferingConfigurationSpec.kt`). The core `DiskBufferingConfig` default is `enabled = false`.
  - Export scheduling can be gated with `setExportScheduleEnablement(ScheduleEnablement)`, for example only on unmetered networks (v1.4.0 release notes).
  - **Privacy gotcha:** "the fully customized exporter … is then wrapped by `*ToDiskExporter` so data is persisted to disk **before reaching any of the custom wrappers**" (EXPORTER_CHAIN.md). Redaction placed in an *exporter customizer* therefore runs after the plaintext hits disk. Redact in a **span or log processor** instead (`addTracerProviderCustomizer` / `addLoggerProviderCustomizer`).
- The underlying library is `io.opentelemetry.contrib:opentelemetry-disk-buffering` (1.61.0-alpha): `FileSpanStorage`, `FileLogRecordStorage`, `FileMetricStorage`, and the `SpanToDiskExporter`, `LogRecordToDiskExporter` and `MetricToDiskExporter` wrappers. Items are deleted on iteration by default (https://github.com/open-telemetry/opentelemetry-java-contrib/blob/main/disk-buffering/README.md).
- Faro RN has an `offline` transport (§2.2). I found no OTel-JS-side persistence for RN.

#### 4.2 Design options for persisting JS-side telemetry

A. **Swap Effect's `HttpClient` for an "OTLP outbox" client (recommended).**

- Why it works: the exporter is generic over `HttpClient.HttpClient`, and the body is already a fully encoded OTLP payload (EFX `OtlpExporter.ts`; `HttpClient.make` takes a runner `(request, url, signal, fiber)`, EFX `http/HttpClient.ts` around line 674).
- What to build: a custom `HttpClient` layer that, for the OTLP URLs:
  1. calls a native module that **appends `{signalPath, contentType, bodyBytes}` to an on-device queue**;
  2. immediately returns a synthetic 200, e.g. `HttpClientResponse.fromWeb(request, new Response(null, {status: 200}))`;
  3. a Kotlin uploader (WorkManager, network-constrained, backoff) then POSTs the stored payloads verbatim to `https://<home-server>/v1/{traces,logs,metrics}` and deletes them on 2xx.
- Benefits:
  - It keeps Effect's batching.
  - It never triggers the 60 s disable.
  - Nothing is lost when offline.
  - Payloads are already OTLP JSON, so no conversion to Java `SpanData` is needed.
- This is an inference from the source; I found no published example.

B. **Bridge JS signals into opentelemetry-android's SDK** with a TurboModule that recreates spans and logs via `openTelemetry.getTracer(...)` and `logsBridge`. Records then share its session id, resource and disk buffer.

- It needs custom span start/end with explicit timestamps and parent IDs. Recreating JS span IDs inside the Java SDK is awkward because the Java SDK generates its own IDs.
- It gives a single exporter and a single disk buffer, but costs more than A.

C. **Effect-side persistence in MMKV or SQLite from JS** (same `HttpClient` seam, storage in JS). Simpler native code, but JS-only uploads stop whenever the JS runtime is not running. Prefer A for native background upload.

Battery: Effect metrics export every 10 s with `exportEmpty: true` (§1.3). On a phone, raise `metricsExportInterval` to 60 s or more and keep traces at about 5–30 s. This is a design suggestion.

---

### 5. Privacy at the source (keeping patient data out)

#### 5.1 Effect side

- **Where data enters Effect telemetry:**
  - span names;
  - `Effect.withSpan(name, {attributes})` and `Effect.annotateSpans(...)`;
  - span events;
  - log message bodies;
  - log annotations (`Effect.annotateLogs`), which `OtlpLogger` copies onto every log record (EFX `OtlpLogger.ts` around line 237);
  - **error messages and stacks.**
- **Errors get exported automatically:**
  - On span failure the tracer adds an `exception` event with `exception.type`, **`exception.message`** and **`exception.stacktrace`**, and sets span status `message = errors[0].message` (EFX `OtlpTracer.ts` lines 333–366).
  - The logger does the same for any log carrying a `Cause` (`OtlpLogger.ts` lines 244–249).
  - **Any tagged error whose message interpolates patient data will leak.** Keep error messages free of patient data, for example using `Schema.TaggedError` fields that are not in `message`.
- **`Redacted`.** `Redacted.make(x)` stringifies and serialises to JSON as `<redacted>` or `<redacted:label>` (EFX `packages/effect/src/Redacted.ts` lines 185–213). Effect's `Formatter.format` redacts any `Redactable` (EFX `Formatter.ts` lines 159–160 and 316–318). `OtlpResource.unknownToAttributeValue` calls `format()` for non-primitive values, so a `Redacted` passed as a span attribute or log value is exported as `<redacted>` (EFX `OtlpResource.ts`, `unknownToAttributeValue`). Primitives (string, number, boolean) pass through untouched, so **wrap patient values in `Redacted` at the domain boundary.**
- **HTTP client spans.** Effect `HttpClient` creates client spans with `http.request.method`, URL attributes and the status code. URL params are redactable via `UrlParams.CurrentRedactedNames`. Header capture is **opt-in** (`TracerHeaderFilter` defaults to recording no headers). Tracing can be turned off per request (`TracerDisabledWhen`) or globally (`Tracer.DisablePropagation`). Source: EFX `http/HttpClient.ts` lines 704–747 and 1755–1800.
- **No built-in allow-list in the Effect OTLP exporter.** The best choke point is **`OtlpSerialization`**, a plain service `{ traces(data), metrics(data), logs(data) } => HttpBody` (EFX `OtlpSerialization.ts`). Provide your own layer that:
  1. walks `TraceData`, `LogsData` and `MetricsData`;
  2. **keeps only allow-listed attribute keys** on resources, spans, events, links, logs and metric data points;
  3. replaces `exception.message` and status messages with the error `_tag`, and log bodies with a static template ID;
  4. stamps `session.id`;
  5. then delegates to `OtlpSerialization.layerJson`.

  One function then covers all three signals, after which data reaches the outbox (§4.2 A). This is a design built on the documented service; it is not an Effect-provided feature.

#### 5.2 opentelemetry-android: what it collects by default

- **Resource** (OTA `core/src/main/java/io/opentelemetry/android/AndroidResource.kt`):
  - `service.name` (app name), `service.version`;
  - `device.model.name`, `device.model.identifier`, `device.manufacturer`;
  - `os.name`, `os.type`, `os.version`, `os.build_id`, `os.description`, `android.os.api_level`;
  - `telemetry.sdk.version`;
  - **`app.installation.id`**, a persistent per-install ID.
- **Network change event:** `network.connection.type`, plus a default `CurrentNetworkAttributesExtractor` that adds **carrier name** and, with `READ_PHONE_STATE`, the mobile network type (OTA `instrumentation/network/README.md`; v1.5.0 notes say carrier info is added even on Wi-Fi when a SIM is present). Disable it with `instrumentations { network { enabled(false) } }`, or don't grant the permission.
- **Screen and lifecycle:** activity and fragment lifecycle spans named after Activity and Fragment classes; `app.screen.name` / `app.screen.previous.name` (v1.7.0). In a bare RN app that is essentially `MainActivity`, so low risk.
- **View click: not enabled by default.** It emits `app.widget.click` with `app.widget.id`, `app.widget.name` and tap **coordinates** (OTA `instrumentation/view-click/README.md`). Keep it off.
- **Crash and ANR:** `exception.message` and `exception.stacktrace` (§3.2). JS fatal errors arrive with the **full JS error message** inside `JavascriptException`, which is a leak vector. Scrub `exception.message` in a `LogRecordProcessor` added via `addLoggerProviderCustomizer`, so it runs before disk.
- **HTTP:** OkHttp and HttpURLConnection instrumentation (which would record URLs) are **not bundled by default**. v1.5.1 fixed an accidental pull-in of network instrumentation via `core` (release notes). Don't add `okhttp3-agent`: RN's networking stack is OkHttp, so the agent would record every URL (inference).
- **Filtering hooks:**
  - `SpanDataModifier` / `AttributeModifyingSpanExporter` (reject spans by name or attribute, remove or modify attributes) (OTA `core/src/main/java/io/opentelemetry/android/export/SpanDataModifier.java`). These are exporter wrappers, so they run *after* the disk layer (§4.1).
  - Pre-disk redaction needs a `SpanProcessor` or `LogRecordProcessor` via the provider customizers.
  - `globalAttributes{}`, `resource{}` and per-instrumentation `enabled(false)`.
  - `disableTracing()`, `disableLogging()` and `disableMetrics()`.
- **Defence in depth on the NixOS server:** the OTel Collector `redaction` processor "deletes span, log, and metric datapoint attributes that don't match a list of allowed attributes" and masks blocked values. It is beta for traces and alpha for logs and metrics (https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/redactionprocessor/README.md).

---

### Recommendation for DELMIR

1. **JS side: Effect's native exporters, no OTel JS SDK.**
   - Use `effect/observability`'s `OtlpTracer`, `OtlpLogger` and `OtlpMetrics` (effect 4.0.5), with `OtlpSerialization.layerJson` and no gzip.
   - Skip `@effect/opentelemetry`, which is pinned to OTel JS 2.x, and skip all OTel JS SDK packages.
   - No crypto or TextEncoder polyfills are needed on RN ≥ 0.74 + Hermes.
   - Apply the Babel `import.meta` and export-namespace-from tweaks reported in Effect #6252, and verify early with a spike.
2. **Privacy choke point: a custom `OtlpSerialization` layer.**
   - Allow-list attribute keys.
   - Replace `exception.message` and status messages with error tags, and log bodies with template IDs.
   - Stamp the native `session.id`.
   - Combine it with `Redacted` for any domain value that could touch patient data, and with error types whose `message` is constant.
3. **Offline: a custom `HttpClient` "OTLP outbox".**
   - The JS client enqueues the encoded payload into a native file queue and returns 200.
   - A Kotlin WorkManager uploader POSTs it to the home server when connected.
   - Flush the Effect `Flusher` on `AppState` → background.
4. **Native side: opentelemetry-android `android-agent` 1.7.0 (BOM 1.7.0-alpha)**, initialised in `MainApplication.onCreate`.
   - Turn on: `crash`, `anr`, `slowrendering`, `startup`, `sessions`, the opt-in `native-crash` module, and `diskBuffering { enabled(true) }`.
   - Turn off: `network` (carrier), `view-click`, and any OkHttp/HttpURLConnection instrumentation.
   - Add a pre-disk `LogRecordProcessor` and `SpanProcessor` that scrub `exception.message`, because JS fatal errors arrive as `JavascriptException` carrying the JS message.
5. **JS fatal errors:** wrap `ErrorUtils.setGlobalHandler` to synchronously emit a sanitised record via a TurboModule into the native OTel logger (disk-buffered), then delegate. Native C++ (ONNX) crashes give only a signal-number `app.crash` on next launch, with no backtrace; accept this or evaluate minidumps separately.
6. **Server:** OTel Collector on NixOS with a `redaction` processor allow-list as a second line of defence.
7. **Skip vendor RN SDKs.** Embrace is the only one with a credible "own OTLP backend, no vendor account" story, but it brings a large proprietary-backed native SDK. Honeycomb is experimental, Splunk is Zipkin-only, and Faro is not OTLP-native.

---

## Part B: the server (backends on NixOS, transport, redaction, experiment tracking)


Date: 2026-10-21. Scope: self-hosted OpenTelemetry backend on the user's NixOS home server for a bare React Native Android app (Effect TS, OTLP/HTTP). Also covers experiment tracking for PyTorch runs on the same machine (RX 6600 XT).

### How the facts were checked

- **nixpkgs facts** come from evaluating the flake locally (`nix eval nixpkgs#<attr>.version`) and reading the nixpkgs source tree. The search.nixos.org backend (and with it the nixos MCP tool) returned TLS errors throughout the session. Three branches were checked:
  - **unstable**: the `nixpkgs-unstable` channel at commit `5adc50831c259f87faeb09ddf930d43597197473` (lib.version `26.11.20261020.5adc508`). Source: https://github.com/NixOS/nixpkgs/tree/5adc50831c259f87faeb09ddf930d43597197473
  - **26.05**: `nixos-26.05` at `cd4ea8d57de16f4810bc5f14207bac45fbf19f67`.
  - **25.11**: `nixos-25.11` at `b6018f87da91d19d0ab4cf979885689b469cdd41`.
- **Module paths** below are relative to `nixos/modules/` at the unstable commit. Package paths are relative to `pkgs/`.
- **"unverified"** means I could not confirm the claim from a primary source in this session.

---

### 1. Backends

#### 1a. OpenTelemetry Collector + Grafana + Tempo + Loki + Prometheus (or Mimir), the "LGTM" path

**nixpkgs versions** (from `nix eval`):

| Attribute | unstable | 26.05 | 25.11 | NixOS module |
|---|---|---|---|---|
| `opentelemetry-collector-contrib` | 0.155.0 | 0.151.0 | 0.135.0 | `services.opentelemetry-collector` (`monitoring/opentelemetry-collector.nix`) |
| `opentelemetry-collector` (core) | 0.155.0 | – | – | same module; **this is its default package** |
| `grafana` | 13.2.4 | 13.0.11 | 12.3.6+security-01 | `services.grafana` (`monitoring/grafana.nix`; `settings`, `provision.datasources`, `provision.dashboards`, `declarativePlugins`) |
| `tempo` | 3.1.0 | 2.10.5 | 2.9.0 | `services.tempo` (`tracing/tempo.nix`; `settings`, `configFile`, `extraFlags`) |
| `grafana-loki` | 3.7.8 | 3.7.8 | 3.6.3 | `services.loki` (`monitoring/loki.nix`; `configuration`, `configFile`, `dataDir`, `extraFlags`) |
| `prometheus` | 3.15.0 | 3.12.0 | 3.7.2 | `services.prometheus` (`monitoring/prometheus/default.nix`; `extraFlags`, `retentionTime`, `enableAgentMode`, `exporters.*`) |
| `mimir` | 3.2.2 | 3.0.8 | 3.0.6 | `services.mimir` (`monitoring/mimir.nix`; `configuration`, `configFile`, `extraFlags`) |
| `grafana-alloy` | 1.17.1 | 1.16.0 | 1.12.2 | `services.alloy` (`monitoring/alloy.nix`; `configPath`, `environmentFile`, `extraFlags`) |

**Licences** (from nixpkgs `meta.license`):
- Grafana: AGPL-3.0-only.
- Tempo: AGPL-3.0-only AND Apache-2.0.
- Loki: AGPL-3.0-only, Apache-2.0.
- Mimir: AGPL-3.0-only.
- Prometheus: Apache-2.0.
- Collector: Apache-2.0 (`pkgs/tools/misc/opentelemetry-collector/releases.nix`).
- Alloy: Apache-2.0.

**How nixpkgs builds the collector.** `releases.nix` runs the upstream builder (`ocb`) over the official `opentelemetry-collector-releases` manifests at `v0.155.0`. So `opentelemetry-collector-contrib` contains exactly the upstream `otelcol-contrib` component set. Source: `pkgs/tools/misc/opentelemetry-collector/releases.nix`, and https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.155.0/distributions/otelcol-contrib/manifest.yaml

**Gotcha: the module defaults to the core collector.** `services.opentelemetry-collector.package` defaults to `pkgs.opentelemetry-collector` (`mkPackageOption pkgs "opentelemetry-collector"`, module line 44). That is the *core* `otelcol` distribution. Its manifest has only batch, memory_limiter, attributes, resource, span, probabilistic_sampler and filter processors. It has **no** `transform`, `redaction`, `bearertokenauth`, `basicauth` or `file_storage`. You must set `package = pkgs.opentelemetry-collector-contrib`. Source: https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.155.0/distributions/otelcol/manifest.yaml

**What the collector module does.** It runs `--config=file:<generated>` with `DynamicUser = true` and `StateDirectory = "opentelemetry-collector"`, so `/var/lib/opentelemetry-collector` is available for `file_storage`. It also validates the config at build time (`validateConfigFile`). Source: module lines 64–121.

**OTLP ingest**
- **Collector `otlp` receiver.**
  - Defaults are gRPC `localhost:4317` and HTTP `localhost:4318`.
  - HTTP paths are `/v1/traces`, `/v1/metrics` and `/v1/logs`.
  - HTTP accepts both binary protobuf and OTLP JSON.
  - It supports a `cors:` block.
  - Sources: https://github.com/open-telemetry/opentelemetry-collector/blob/main/receiver/otlpreceiver/README.md and https://opentelemetry.io/docs/specs/otlp/ (`application/x-protobuf` and `application/json`).
- **Prometheus native OTLP.**
  - Enabled with `--web.enable-otlp-receiver` (off by default). Endpoint is `/api/v1/otlp/v1/metrics`, over HTTP only (no gRPC mentioned).
  - Recommended settings:
    - `storage.tsdb.out_of_order_time_window: 30m`
    - `otlp.promote_resource_attributes` (nothing is promoted by default)
    - `otlp.translation_strategy` (default `UnderscoreEscapingWithSuffixes`)
  - Resource attributes land on `target_info`.
  - Delta temporality needs the experimental `otlp-deltatocumulative` feature flag.
  - Source: https://prometheus.io/docs/guides/opentelemetry/
  - On NixOS, pass the flag through `services.prometheus.extraFlags`.
- **Loki native OTLP.**
  - HTTP only: the collector's `otlphttp` exporter points at `http://<loki>/otlp`.
  - Needs `limits_config.allow_structured_metadata: true` (the default since 3.0).
  - Only a default list of resource attributes becomes index labels (`default_resource_attributes_as_index_labels`, e.g. `service.name`). Everything else becomes structured metadata.
  - Per-line limits are 64 KB and 128 entries.
  - Source: https://grafana.com/docs/loki/latest/send-data/otel/
- **Tempo.**
  - Configured under `distributor.receivers.otlp.protocols.{grpc,http}`, listening on localhost 4317/4318 by default.
  - "By default, receivers listen to localhost and need a configured IP to listen on an external interface."
  - `storage.trace.backend: local` is "only supported in the monolithic mode".
  - Monolithic mode (`-target=all`) does **not** need Kafka. Microservices mode requires a Kafka-compatible bus.
  - Source: https://grafana.com/docs/tempo/latest/configuration/
  - Whether nixpkgs' Tempo 3.1.0 in monolithic mode works with the current `services.tempo` defaults is unverified. Test it.
- **Mimir.** Native OTLP over HTTP at `/otlp`. Source: https://grafana.com/docs/mimir/latest/configure/configure-otel-collector/

**Signals.** Traces (Tempo), metrics (Prometheus/Mimir) and logs (Loki), all viewed in Grafana.

**Crash and exception views.** There is no dedicated "exceptions inbox" in this stack: my assessment, from not finding one. Crashes are queried as:
- log records with `exception.type`, `exception.message` and `exception.stacktrace` in Loki, or
- span events in Tempo.

OTel semconv defines these attributes as Stable. It notes that `exception.message` "may contain sensitive information". Source: https://opentelemetry.io/docs/specs/semconv/exceptions/exceptions-logs/

**Storage engines**
- Prometheus: local TSDB.
- Loki: TSDB index plus chunks on filesystem or object store.
- Tempo: Parquet blocks on local disk or object store (per the Tempo config docs above).
- Mimir: object storage oriented, designed for horizontal scale (nixpkgs description: "horizontally scalable, highly available, multi-tenant, long-term storage for Prometheus").

**Prometheus or Mimir?** For one user, Prometheus is enough. Mimir adds nothing except long-term object storage. That is my judgement.

**Footprint (unverified).** Single-user, low-volume estimate: roughly 1–1.5 GB RAM total for collector + Prometheus + Loki + Tempo + Grafana, and less than 1 CPU core idle. No primary source gives single-user minimums.

**Operational complexity.** Five services, but all have NixOS modules and declarative config. Grafana datasources can be provisioned declaratively through `services.grafana.provision`.

**Related options**
- **`grafana/otel-lgtm`.** A single Docker image bundling the collector, Prometheus, Tempo, Loki, Pyroscope and Grafana. It is "intended for development, demo, and testing environments" (Apache-2.0). Useful as a reference config, not as the home-server deployment. Source: https://github.com/grafana/docker-otel-lgtm
- **Grafana Alloy.** "A distribution of the OpenTelemetry Collector with built-in Prometheus pipelines". Source: https://grafana.com/docs/alloy/latest/introduction/ It is in nixpkgs with `services.alloy`. It could replace the upstream collector, but it uses its own config language. Whether it ships the `redaction` processor equivalent (`otelcol.processor.*`) is unverified. For DELMIR the upstream contrib collector is the simpler, better-documented gatekeeper.

#### 1b. SigNoz

- **nixpkgs:** not packaged. No `signoz*` attribute or path exists in unstable (`nix eval` and a source grep at 5adc508), and there is no NixOS module.
- **Latest release:** v0.146.0 (2026-10-14). It ships `signoz_linux_amd64.tar.gz` and `signoz-community_linux_amd64.tar.gz` binaries. Source: https://github.com/SigNoz/signoz/releases/tag/v0.146.0
- **Docker install:**
  - Starts ClickHouse 25.5.6, ClickHouse Keeper, PostgreSQL 16, `signoz-otel-collector` and the `signoz` UI (8080), with OTLP on 4317/4318.
  - Needs "At least 4GB of memory allocated to Docker".
  - The legacy install script and the compose files under `deploy/` are deprecated as of v0.130.0.
  - Source: https://signoz.io/docs/install/docker/
- **Linux (non-Docker) install:**
  - Binary plus systemd, via the `foundryctl` tool or manual units.
  - Components: ClickHouse, Keeper or ZooKeeper, PostgreSQL or SQLite, the SigNoz backend, the SigNoz OTel collector, and a DB migrator.
  - Needs "at least 4 GB of memory for a small test installation".
  - Source: https://signoz.io/docs/install/linux/
- **Signals:** traces, metrics, logs. It has an **Exceptions view** (grouped by service, type and message, with stack trace), but it reads exceptions only from span events, not logs. Source: https://signoz.io/docs/userguide/exceptions/
- **Licence:** MIT outside `ee/`; `ee/` is under a separate enterprise licence. Source: https://github.com/SigNoz/signoz/blob/main/LICENSE
- **Storage:** ClickHouse. nixpkgs has `clickhouse` 26.8.7.19-lts and `services.clickhouse`, but SigNoz pins its own ClickHouse version, schema and migrator. Whether nixpkgs' ClickHouse is compatible is unverified.
- **Complexity:** high for NixOS. You would package two Go binaries yourself, run ClickHouse, Keeper and Postgres, and handle migrations.

#### 1c. OpenObserve

- **nixpkgs `openobserve`:**
  - unstable 1.0.4; 26.05 0.91.1; 25.11 0.15.3.
  - Built from source: Rust plus an npm-built UI.
  - Licence AGPL-3.0-or-later.
  - An `enableEnterprise ? false` override fetches the unfree prebuilt EE binary instead.
  - Source: `pkgs/by-name/op/openobserve/package.nix`
- **NixOS module:** none. No `openobserve` hit under `nixos/` at 5adc508. You would write a small systemd unit.
- **Architecture:**
  - A single binary. `ZO_LOCAL_MODE=true` is the default (single node), with `ZO_LOCAL_MODE_STORAGE=disk` by default and a SQLite metadata store in local mode.
  - HTTP on 5080, gRPC on 5081.
  - Root user set through `ZO_ROOT_USER_EMAIL` and `ZO_ROOT_USER_PASSWORD`.
  - Source: https://openobserve.ai/docs/environment-variables/
- **Storage:** Parquet columnar files (on object storage or local disk). Source: https://github.com/openobserve/openobserve
- **Signals:** logs, metrics, traces, plus RUM with error tracking and session replay (the RUM is browser-oriented). Queried with SQL, or PromQL for metrics. Source: https://github.com/openobserve/openobserve
- **OTLP:**
  - HTTP traces at `/api/<org>/v1/traces` with `Authorization: Basic …`. Source: https://openobserve.ai/docs/ingestion/traces/opentelemetry/
  - gRPC on 5081 (per the env-var docs).
  - JSON vs protobuf: not stated (unverified).
- **Footprint:** no primary RAM figure (unverified). As a single Rust process it is likely lighter than the LGTM stack (unverified).
- **Complexity:** low. One process plus a hand-written unit. But only one UI paradigm, and no collector in front unless you add one. You should still put the contrib collector in front for redaction.

#### 1d. Jaeger v2

- **nixpkgs:** not packaged in unstable (no `jaeger*` attribute or path at 5adc508). No module.
- **Upstream:**
  - v2.22.0 (2026-10-06), with linux-amd64 tarballs on GitHub releases. Source: https://github.com/jaegertracing/jaeger/releases/tag/v2.22.0
  - Built on the "OpenTelemetry Collector framework as the base".
  - Storage: memory, Badger (single-node local), Cassandra, Elasticsearch/OpenSearch, Kafka as a buffer.
  - CNCF graduated.
  - Source: https://www.jaegertracing.io/docs/latest/
  - All-in-one uses "transient in-memory storage" by default, with the UI on 16686. Source: https://www.jaegertracing.io/docs/2.22/getting-started/
- **Signals:** traces only, as a tracing platform. It has no logs or metrics store, so you would still need Loki and Prometheus.
- **Licence:** Apache-2.0 (unverified in this session; the docs page did not state it).
- **Verdict:** strictly dominated by Tempo here. Tempo is packaged, has a module, and is integrated with Grafana.

#### 1e. HyperDX / ClickStack

- **nixpkgs:** not packaged (no `hyperdx` or `clickstack` attribute). No module.
- **ClickStack** = HyperDX UI + a custom OTel collector + ClickHouse. The open-source deployment also needs **MongoDB** for app state. Source: https://clickhouse.com/docs/use-cases/observability/clickstack/overview
- **HyperDX:**
  - MIT licence.
  - Signals: logs, metrics, traces, session replays, errors.
  - All-in-one Docker image exposing 8080, 4317 and 4318.
  - Recommends at least 4 GB RAM and 2 cores for testing.
  - Source: https://github.com/hyperdxio/hyperdx
- **Deployment options:**
  - All-in-one is "Not recommended for production".
  - Docker Compose is the single-server production option.
  - Helm for Kubernetes.
  - No binary or systemd path is documented.
  - Source: https://clickhouse.com/docs/use-cases/observability/clickstack/deployment
- **Complexity:** high on NixOS. It needs Docker or OCI containers (`virtualisation.oci-containers`) plus ClickHouse and MongoDB.

#### Backend comparison

| | LGTM (collector + Tempo + Loki + Prometheus + Grafana) | OpenObserve | SigNoz | Jaeger v2 | ClickStack/HyperDX |
|---|---|---|---|---|---|
| nixpkgs (unstable) | all packaged (versions above) | `openobserve` 1.0.4 | no | no | no |
| NixOS module | yes, every component | no (write a unit) | no | no | no (only `services.clickhouse` for the DB) |
| Traces / metrics / logs | yes / yes / yes | yes / yes / yes | yes / yes / yes | yes / no / no | yes / yes / yes |
| Crash or exception view | none dedicated; query logs or span events | error tracking via RUM (browser-oriented) | Exceptions tab (span events only) | no | "errors" |
| OTLP HTTP / gRPC | collector: both. Backends: Prometheus, Loki, Mimir HTTP only; Tempo both | HTTP `/api/<org>/v1/*` and gRPC 5081 | both (4317/4318) | both (4317/4318; protocol labels unverified) | both (4317/4318) |
| OTLP JSON | collector: yes (spec + receiver README) | unverified | yes via its OTel collector (unverified) | unverified | unverified |
| Storage | Prometheus TSDB; Loki TSDB + chunks; Tempo Parquet | Parquet on disk or S3, SQLite metadata | ClickHouse + Postgres | Badger, ES, Cassandra, … | ClickHouse + MongoDB |
| Footprint (single user) | ~1–1.5 GB (unverified) | small, one process (unverified) | ≥4 GB (documented) | small | ≥4 GB, 2 cores (documented, testing) |
| Licence | AGPL-3.0 (Grafana, Loki, Tempo, Mimir); Apache-2.0 (Prometheus, collector) | AGPL-3.0 (OSS build) | MIT core + `ee/` proprietary | Apache-2.0 (unverified) | MIT (HyperDX) |
| UI | Grafana | built-in | built-in | built-in | HyperDX |
| Ops complexity on NixOS | medium (5 services, all declarative) | low–medium | high | low, but incomplete | high |

---

### 2. How the phone reaches the home server

**Android constraint.** "Starting with Android 9 (API level 28), cleartext support is disabled by default." Per-domain opt-in is possible with `<domain-config cleartextTrafficPermitted="true">`. Apps targeting API 24+ do not trust user-added CAs by default (only `src="system"`). Source: https://developer.android.com/privacy-and-security/security-config

This means:
- plain `http://` OTLP needs a network-security-config exception, and
- a self-signed or private-CA HTTPS endpoint needs an explicit trust anchor in the app.

A publicly trusted certificate avoids both.

#### Tailscale (hosted control plane)

- **nixpkgs and modules.**
  - `tailscale` is 1.104.1 on unstable (26.05: 1.98.10; 25.11: 1.90.9). The module is `services.tailscale` (`enable`, `authKeyFile`, `extraUpFlags`, `extraSetFlags`, `permitCertUid`, `useRoutingFeatures`, …).
  - There is a separate `services.tailscale.serve` module (`networking/tailscale-serve.nix`) in **unstable and 26.05, but not 25.11**.
  - That module configures **Tailscale Services** (`svc:<name>`, via `tailscale serve set-config --all`). Services require the host to use a **tag-based identity** ("a device authenticated with a user account can't be a Service host") and Tailscale ≥ 1.86. Source: https://tailscale.com/kb/1552/tailscale-services
- **HTTPS certificates.**
  - Tailscale gets Let's Encrypt certificates for `<machine>.<tailnet>.ts.net` via DNS-01. MagicDNS must be enabled.
  - Certificates last 90 days.
  - Machine names appear in public Certificate Transparency logs: "Do not enable the HTTPS feature if any of your machine names contain sensitive information."
  - Source: https://tailscale.com/kb/1153/enabling-https
- **`tailscale serve`.**
  - Proxies a local port to the tailnet over HTTPS with automatic certificates. It is tailnet-only; Funnel is the public variant.
  - Command: `tailscale serve --bg --https=443 localhost:4318`.
  - With `--bg` it persists across reboots and `tailscale down`/`up`.
  - It adds `Tailscale-User-Login`/`-Name` identity headers.
  - Sources: https://tailscale.com/kb/1312/serve and https://tailscale.com/kb/1242/tailscale-serve
  - Result: the phone exports to `https://<host>.<tailnet>.ts.net/v1/traces` with a publicly trusted certificate, so no Android network-security-config change is needed.
- **Android app:** the official Tailscale Android client exists and is supported (it is also listed as a supported client by headscale; see below).
- **Cost:** the free Personal plan has up to 6 users and unlimited user devices. Source: https://tailscale.com/pricing

#### Headscale (self-hosted control plane)

- **nixpkgs and module.** `headscale` is 0.29.5 on unstable (26.05: 0.28.0; 25.11: 0.27.1), BSD-3-Clause, with module `services.headscale`.
- **Clients.** Supported clients include Android (extra setup needed). Source: https://headscale.net/stable/about/clients/
- **Features.**
  - MagicDNS is listed.
  - Serve and Funnel only link to GitHub issues, so their status is unclear.
  - Tailscale HTTPS certificates (`tailscale cert`) are not mentioned, so treat them as unsupported (unverified).
  - Source: https://headscale.net/stable/about/features/
- **Requirements.** Headscale itself needs reachable TLS: Let's Encrypt via HTTP-01 on port 80 or TLS-ALPN-01 on 443. The full chain is needed or "the Tailscale Android client, will reject it". Source: https://headscale.net/stable/ref/tls/
- **Consequence.** The control server must be publicly reachable, and the OTLP endpoint needs your own domain certificate (e.g. `security.acme` DNS-01) because there is no ts.net certificate.

#### Plain WireGuard

- **Module:** `networking.wireguard` (`networking/wireguard.nix`; there is also `wireguard-networkd.nix`).
- **Android:** the official app is on the Play Store or as an APK. Source: https://www.wireguard.com/install/
- **Trade-off:** no DNS names or certificates come with it. You would use a private IP plus your own domain with a DNS-01 certificate, or allow cleartext to that IP in network-security-config. The traffic is already encrypted by WireGuard, but Android's policy is per-app.
- **Complexity:** you manage keys, roaming and NAT yourself. For one phone it is fine, but there is no MagicDNS.

#### Public exposure with collector authentication

- **`bearertokenauth`** (contrib, beta) works as a server authenticator on receivers (`token`, `tokens`, `filename`, `scheme`, `header`). Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/bearertokenauthextension/README.md
- **`basicauth`** (contrib, beta): server side through `htpasswd.file` or `htpasswd.inline`, attached via `receivers.otlp.protocols.http.auth.authenticator`. Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/extension/basicauthextension/README.md
- Both are in nixpkgs' contrib build (manifest lines 15–16) and absent from core.
- **Downside:** a token baked into an APK is extractable. It also exposes an internet-facing parser on the home server. Use this only behind a reverse proxy with ACME, and only if a VPN is not acceptable.

#### Offline buffering

- **The OTLP spec gives the phone no buffer.** It defines retries (429/502/503/504 are retryable; honour `Retry-After`; exponential backoff with jitter). It does not define buffering while a single server is unreachable. Source: https://opentelemetry.io/docs/specs/otlp/
- **So the phone must buffer itself.** When the phone is off the tailnet, the app must queue to disk (bounded, oldest-first eviction) and flush on reconnect. This is an app-side design item for the Effect TS exporter. Whether `@effect/opentelemetry` has built-in persistent buffering is unverified.
- **The collector buffer covers a different failure.** Collector-side `sending_queue.storage: file_storage/...` persists batches to disk across collector restarts and backend outages, with retry defaults of 5s initial, 30s max, 300s max elapsed. That protects the collector→backend hop, not the phone→collector hop. Source: https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md

---

### 3. Collector-side guarantees that no patient data reaches storage

#### Processors (contrib manifest v0.155.0, which is what nixpkgs builds)

| Processor | Distribution | Stability | What it does |
|---|---|---|---|
| `attributes` | core + contrib + k8s | beta (traces, metrics, logs) | insert, update, upsert, delete, hash (SHA1), extract, convert on span, log or metric attributes; include/exclude match. The README says it is **superseded by `transform`**. |
| `resource` | core + contrib | (not fetched) | Same operations on resource attributes. Present in both manifests. |
| `transform` (OTTL) | contrib + k8s only | beta (traces, metrics, logs) | OTTL statements per context: `resource`, `scope`, `span`, `spanevent`, `metric`, `datapoint`, `log`. Functions include `keep_keys`, `keep_matching_keys`, `delete_matching_keys`, `replace_pattern`, `set(log.body, …)`. `error_mode` is `ignore` (default), `silent` or `propagate`. |
| `filter` | core + contrib + k8s | alpha (traces, metrics, logs) | Drops spans, span events, metrics, datapoints or logs matching any OTTL condition (`trace_conditions`, `metric_conditions`, `log_conditions`). Dropping a parent span can orphan its children. |
| `redaction` | contrib + k8s only | traces beta; logs and metrics alpha | Allow-list: "If `allowed_keys` is empty, then no attributes are allowed". Non-allowed attributes "are removed before any value checks are done". `blocked_values` regexes mask matches in allowed values. `allowed_values` and `blocked_key_patterns` are also available. `hash_function` (incl. hmac-sha256) hashes instead of masking. `url_sanitizer` and `db_sanitizer` also rewrite span names. `summary` adds audit attributes. Whether it touches **resource** attributes is not stated (unverified), so also apply `transform` `keep_keys` on `resource.attributes`. |

Sources:
- `attributes`: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/attributesprocessor/README.md
- `transform`: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/transformprocessor/README.md
- `filter`: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/filterprocessor/README.md
- `redaction`: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/redactionprocessor/README.md

**What nixpkgs ships.** `opentelemetry-collector-contrib` 0.155.0 includes `attributes` (manifest line 105), `filter` (111), `redaction` (124), `resource` (127), `transform` (132), `memory_limiter` and `batch` (103–104), `bearertokenauth` and `basicauth` (15–16) and `file_storage` (44). The core `opentelemetry-collector` lacks `transform`, `redaction` and the auth and storage extensions. So set `services.opentelemetry-collector.package = pkgs.opentelemetry-collector-contrib;`.

#### Allow-list policy (defence in depth; the app must still never emit patient data)

1. **Only one entry point.**
   - The collector binds `127.0.0.1:4318`, reached only through `tailscale serve`. Tempo, Loki and Prometheus bind to localhost too.
   - Prometheus's OTLP receiver and Loki's `/otlp` are **not** exposed, so no path to storage bypasses the collector.
2. **Resource allow-list** (`transform`, `resource` context): `keep_keys(resource.attributes, ["service.name","service.version","service.namespace","deployment.environment.name","telemetry.sdk.name","telemetry.sdk.language","telemetry.sdk.version","os.type","os.version","device.model.identifier"])`.
   - Deliberately excluded: anything identifying the device or person (e.g. `device.id`, `host.name`, `user.*`, `enduser.*`).
3. **Signal-attribute allow-list** (`redaction`, `allowed_keys`). List an explicit DELMIR vocabulary, for example:
   - `delmir.screen`, `delmir.step`, `delmir.outcome`, `delmir.model.version`, `delmir.latency_bucket`
   - `exception.type`, `exception.stacktrace`
   - `http.request.method`, `http.response.status_code`, `url.template`

   Configuration:
   - Leave `allow_all_keys: false`.
   - Set `blocked_values` regexes for anything that looks like an ID, date of birth, phone number, email or long free-text digits.
   - Set `summary: info` so the redaction counts are themselves visible.
4. **Scrub the free-text fields that `redaction` does not cover** (`transform`):
   - `set(span.name, ...)` and `replace_pattern` on span names to collapse IDs, or make span names a fixed enum app-side.
   - `set(log.body, "")` unless `log.body` matches an allow-listed template.
   - Drop `exception.message` (or hash it with `hmac-sha256`), because semconv warns it "may contain sensitive information". Keep `exception.type` and `exception.stacktrace`; stack frames are code locations.
   - Clear `spanevent` attributes the same way.
5. **Metric datapoint allow-list** (`transform`, `datapoint` context): `keep_keys(datapoint.attributes, [...])`. This also prevents label-cardinality blowups in Prometheus.
6. **Drop anything unexpected** with `filter`: for example, any span or log whose `service.name` is not `delmir-android` or is missing.
7. **Order the pipeline:** `memory_limiter → transform(resource/body/names) → redaction → filter → batch`.
8. **Test it.** A NixOS VM test or a golden-file test feeds a fixture containing fake PII through the collector config (with the `file` or `debug` exporter) and asserts that the PII is absent. The collector config is already validated at build time by the module (`validateConfigFile`).

---

### 4. Experiment tracking for PyTorch training runs

#### Can the OTel backend serve it?

Only partially.

- **What fits.** Prometheus and Mimir can store per-step loss as gauges, and Grafana can plot them.
- **What does not fit:**
  - **Run identity as labels.** Every run ID or hyperparameter combination becomes a new series. Prometheus warns: "Do not use labels to store dimensions with high cardinality … unbounded sets of values". Source: https://prometheus.io/docs/practices/naming/
  - **Step-indexed data.** Metrics are indexed by wall-clock time, not by training step.
  - **Run metadata.** There is no place for params, artifacts (checkpoints, ONNX), datasets, run comparison, confusion matrices or ROC curves.
- **Training-side traces.** These are possible but of limited value.

#### Tools

| Tool | nixpkgs (unstable) | NixOS module | Licence | Notes |
|---|---|---|---|---|
| **MLflow** | `mlflow-server` 3.17.1 (26.05: 3.12.0; 25.11: 3.3.1); `python3Packages.mlflow` 3.17.1 | **none** (no `mlflow` under `nixos/`) | Apache-2.0 | See details below. |
| **TensorBoard** | `python3Packages.tensorboard` 2.21.0 (no top-level attribute) | none | Apache-2.0 | Scalars, images, PR curves from event files. No run registry, artifact store or param search. |
| **Aim** | not packaged | none | Apache-2.0 | Tracks hparams and metric series with step and context; UI via `aim up`. Latest release v3.29.1 (2025-05-08), over 17 months old on 2026-10-21, which is a maintenance-risk signal. Sources: https://github.com/aimhubio/aim and https://github.com/aimhubio/aim/releases/tag/v3.29.1 |
| **W&B Self-Managed** | client `python3Packages.wandb` 0.31.0 (MIT); server not packaged | none | Server needs a licence ("You must obtain a license before installation") | Delivered via a Kubernetes operator. Needs MySQL 8.4, S3-compatible storage and Redis. Whether a free personal licence exists is unverified. Source: https://docs.coreweave.com/platform/hosting/self-managed/ |
| **ClearML** | neither SDK nor server packaged | none | Server: SSPL v1.0 | Docker Compose with MongoDB and Elasticsearch. Source: https://github.com/clearml/clearml-server |

**MLflow details**
- **nixpkgs:** `mlflow-server` is `toPythonApplication` with boto3 and mysqlclient added (`pkgs/by-name/ml/mlflow-server/package.nix`).
- **What it tracks:** params, per-step metrics (`log_metric(..., step=)`), artifacts (weights, images), tags, datasets (`log_input`) and models. The UI supports run comparison and search. Source: https://mlflow.org/docs/latest/ml/tracking/
- **Server:** a SQLite, Postgres or MySQL backend store plus a local or S3 artifact store, with basic-auth login. Source: https://mlflow.org/docs/latest/self-hosting/
- **System metrics:** optional, including GPU through `pyrsmi` for AMD/HIP. Source: https://mlflow.org/docs/latest/ml/tracking/system-metrics/
- **OTel support:**
  - The MLflow server accepts **OTLP traces only**, at `/v1/traces`.
  - It is OTLP/HTTP only ("the OTLP/gRPC endpoint is not yet supported"), needs MLflow ≥ 3.6.0, the `x-mlflow-experiment-id` header and a SQL backend store.
  - It does **not** accept OTLP metrics or logs. It can export its own traces to OTel backends.
  - This feature targets GenAI tracing, not training metrics.
  - Sources: https://mlflow.org/docs/latest/genai/tracing/opentelemetry/ingest/ and https://mlflow.org/docs/latest/genai/tracing/opentelemetry/

#### GPU telemetry of the training box (RX 6600 XT, ROCm)

- **node_exporter `drm` collector.**
  - Registered `defaultDisabled`. AMD-only (`updateAMDCards`).
  - Exports `node_drm_gpu_busy_percent`, `node_drm_memory_vram_{size,used}_bytes`, GTT and visible VRAM, and `node_drm_card_info`.
  - Source: https://github.com/prometheus/node_exporter/blob/master/collector/drm_linux.go
  - Enable it with `services.prometheus.exporters.node.enabledCollectors = [ "drm" ];` (nixpkgs `prometheus-node-exporter` 1.12.1).
- **node_exporter `hwmon` collector** (default on). This picks up the amdgpu hwmon sensors:
  - `temp1-3_input`
  - `power1_average`/`power1_input`
  - `fan1_input`
  - `freq1_input` (gfx clock) and `freq2_input` (memory clock)
  - `in0_input`

  Source: https://docs.kernel.org/gpu/amdgpu/thermal.html
- **AMD Device Metrics Exporter.** v1.5.3 (2026-10-07) lists support for "MI2xx, MI3xx" and "MI350P, Radeon AI" only, so **not the RX 6600 XT**. It is not in nixpkgs. Source: https://github.com/ROCm/device-metrics-exporter/releases/tag/v1.5.3
- **`rocmPackages.rdc`** (7.2.4, MIT) is datacenter-oriented. Whether its Prometheus plugin supports consumer RDNA2 is unverified.
- `rocmPackages.amdsmi` and `rocm-smi` are both 7.2.4 in nixpkgs. They are CLIs, not exporters.

#### Recommendation on sharing

- **Share** the host, Prometheus and Grafana for **infrastructure** signals of training: GPU utilisation, VRAM, temperature and power from node_exporter `drm` + `hwmon`, and the training process's host metrics.
- **Do not share** storage for **experiment tracking**. Run MLflow (`mlflow-server`) as its own systemd service (there is no NixOS module, so write a small unit) with SQLite and a local artifact directory, bound to localhost and published through `tailscale serve` on another port or path.
- Keep run IDs out of Prometheus labels.
- Optionally show MLflow runs in Grafana (unverified whether a maintained Grafana MLflow datasource exists), or just link between the two UIs.

---

### Recommendation for DELMIR

1. **Backend: the LGTM path, all from nixpkgs with NixOS modules.**
   - Components:
     - `services.opentelemetry-collector` with `package = pkgs.opentelemetry-collector-contrib` (0.155.0)
     - `services.tempo` (traces)
     - `services.loki` (logs and crashes as exception log records)
     - `services.prometheus` with `extraFlags = [ "--web.enable-otlp-receiver" ]` (metrics; skip Mimir for one user)
     - `services.grafana` with provisioned datasources
   - The collector is the **only** OTLP entry point. Every backend listens on localhost.
   - **Runner-up:** OpenObserve (packaged, AGPL, one binary, has error-tracking UI, but no module).
   - **Rejected:** SigNoz and ClickStack (not packaged, ClickHouse plus Postgres/Mongo, documented ≥4 GB RAM) and Jaeger (not packaged, traces only).
2. **Crash reports:** emit them as OTel log records with `exception.type` and `exception.stacktrace` (semconv Stable), and with `exception.message` scrubbed. View them in Grafana/Loki. Accept that there is no grouped exceptions inbox; build a Grafana dashboard grouped by `exception.type`.
3. **Transport: Tailscale**, with `tailscale serve --bg --https=443 localhost:4318` on the server (or `services.tailscale.serve`, which needs a tagged host and 26.05 or unstable).
   - The phone gets `https://<host>.<tailnet>.ts.net` with a Let's Encrypt certificate, so there are no cleartext or trust-anchor exceptions in Android.
   - Avoid sensitive machine names because of the Certificate Transparency logs.
   - Add `bearertokenauth` on the receiver as a second factor.
   - Headscale is viable but loses ts.net certificates and needs a public control server. Plain WireGuard works but needs your own certificate or a cleartext exception.
4. **Offline:** the app must buffer to disk and retry, because the OTLP spec gives the client no persistence. Configure collector `file_storage` in `sending_queue` for the backend hop.
5. **No patient data:** use the allow-list pipeline from §3:
   - `transform` `keep_keys` on resource and datapoint attributes
   - `redaction` with explicit `allowed_keys` and `blocked_values`
   - scrubbing of span names, log bodies and `exception.message`
   - `filter` to drop unknown services
   - a golden test proving that fake PII does not survive
6. **Training:** MLflow (`mlflow-server`, custom systemd unit) for experiment tracking, separate from the OTel stores. GPU and host telemetry go into the same Prometheus and Grafana via node_exporter `drm` and `hwmon`, not AMD's device-metrics-exporter (no RX 6600 XT support).
