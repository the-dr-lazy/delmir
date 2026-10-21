# Effect Schema is the single source of every contract Python and TypeScript share

The 12-lead signal, the classifier output, the case export and the model manifest are each defined once, as an Effect Schema data-type module in `contracts/`. Python never defines them: Nix builds JSON Schema from each module's `json` codec and pydantic models from that JSON Schema, and training parses through those models at its boundary. A language-neutral source (hand-written JSON Schema or protobuf) was declined because it loses Effect Schema's readability and transformations, and the app is the side that changes these contracts most.

## Consequences

- Brands and Effect transformations do not cross into Python, so every wire form carries its own meaning: units and lead order are literals, variants are tagged unions, versions are literal tags. Brands are labels only, never validation.
- Shape agreement is not taken on trust. A flake check generates values from each schema, round-trips them through Python and back, and requires both sides to reject the same mutated values; its seed is the hash of `contracts/`. Meaning (units, amplitudes) is checked against real ECGs in the golden fixtures.
- Contract versions are literals. The manifest pins a digitizer that `produces` and a classifier that `consumes` the one signal contract version the app is built against, so a mismatched model pair fails to decode at build time.
