// SPIKE (delmir#43) entry, size only: index.js plus effect/Arbitrary in the import graph.
import * as Arbitrary from 'effect/Arbitrary';
import './index';

globalThis.__spikeArbitrary = Arbitrary;
