# One module per data type, re-exported by name, with no TypeScript namespaces

Each data type is its own module exporting the type under the module's name plus `identity`, `schema`, `arbitrary` and `json`; a package's only entry is `public-api.ts`, which re-exports each module as `export * as Foo from "./foo"`, so consumers write `Foo.Foo` and `Foo.schema` as with Effect's own modules. This follows the data-type shape settled in pressnxpress (`Interface`/`TaggedUnion` checked against a hand-written type, fields given as modules, `makeModule` for type constructors) but, by the owner's choice, drops its `namespace Foo` co-location. `export * as` gives consumers the same `Foo.x` reading while keeping every file plain ES modules with erasable type syntax.

## Consequences

- Without a namespace value, `Interface(identity)` reads the type from the module's own `identity`, the same witness fields are read through.
- `json` is `Schema.toCodecJson(schema)` and every JSON boundary goes through it; the JSON Schema Python sees is emitted from it.
- Inside a package, siblings import each other as `import * as Label from "./label"`, never through `public-api.ts`. oxlint enforces this, no namespaces, no unchecked `Schema.brand`, and no Effect combinators around a module's `.schema` inside `Interface`/`TaggedUnion` fields.
