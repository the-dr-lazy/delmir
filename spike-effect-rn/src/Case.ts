// SPIKE (delmir#43): a stand-in case schema, not the real one (#26/#28 decide that).
// ~30 fields, with nested arrays, so decoding cost is in the right ballpark.
import * as Schema from 'effect/Schema';

const Lead = Schema.Literals(['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']);

const LeadFinding = Schema.Struct({
  lead: Lead,
  stDeviationMv: Schema.Number,
  tWaveAmplitudeMv: Schema.Number,
  qWave: Schema.Boolean,
  qualityScore: Schema.Number,
});

const ModelOutput = Schema.Struct({
  modelId: Schema.String,
  modelVersion: Schema.String,
  pOmi: Schema.Number,
  vesselProbabilities: Schema.Array(Schema.Struct({ vessel: Schema.Literals(['LAD', 'LCx', 'RCA']), p: Schema.Number })),
  latencyMs: Schema.Number,
});

export const Case = Schema.Struct({
  id: Schema.String,
  createdAt: Schema.Number,
  updatedAt: Schema.Number,
  label: Schema.String,
  note: Schema.NullOr(Schema.String),
  imagePath: Schema.String,
  imageWidth: Schema.Number,
  imageHeight: Schema.Number,
  imageSha256: Schema.String,
  paperSpeedMmPerS: Schema.Literals([25, 50]),
  gainMmPerMv: Schema.Literals([5, 10, 20]),
  layout: Schema.Literals(['3x4', '3x4+1', '6x2', '12x1']),
  rhythmLeads: Schema.Array(Lead),
  heartRateBpm: Schema.NullOr(Schema.Number),
  qrsDurationMs: Schema.NullOr(Schema.Number),
  qtcMs: Schema.NullOr(Schema.Number),
  axisDeg: Schema.NullOr(Schema.Number),
  leadFindings: Schema.Array(LeadFinding),
  outputs: Schema.Array(ModelOutput),
  declined: Schema.Boolean,
  declineReasons: Schema.Array(Schema.String),
  pOmi: Schema.NullOr(Schema.Number),
  culpritVessel: Schema.NullOr(Schema.Literals(['LAD', 'LCx', 'RCA'])),
  confidence: Schema.NullOr(Schema.Number),
  reviewed: Schema.Boolean,
  reviewerVerdict: Schema.NullOr(Schema.Literals(['agree', 'disagree', 'unsure'])),
  tags: Schema.Array(Schema.String),
  appVersion: Schema.String,
  schemaVersion: Schema.Number,
  deviceModel: Schema.String,
});
export type Case = typeof Case.Type;

export const Cases = Schema.Array(Case);

const LEADS = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'] as const;
const VESSELS = ['LAD', 'LCx', 'RCA'] as const;

const hex = (n: number) => {
  const bytes = new Uint8Array(n);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
};

export const uuid = () => {
  const h = hex(16);
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-a${h.slice(17, 20)}-${h.slice(20, 32)}`;
};

export const randomKeyHex = () => hex(32);

export const generateCase = (i: number): Case => {
  const declined = i % 11 === 0;
  const pOmi = declined ? null : Math.random();
  return {
    id: uuid(),
    createdAt: Date.now() - i * 60_000,
    updatedAt: Date.now(),
    label: `Case ${i}`,
    note: i % 3 === 0 ? `Stand-in note for case ${i}` : null,
    imagePath: `/data/user/0/com.delmirspike/files/ecg/${i}.jpg`,
    imageWidth: 3024,
    imageHeight: 4032,
    imageSha256: hex(32),
    paperSpeedMmPerS: 25,
    gainMmPerMv: 10,
    layout: '3x4+1',
    rhythmLeads: ['II'],
    heartRateBpm: 60 + (i % 60),
    qrsDurationMs: 80 + (i % 40),
    qtcMs: 380 + (i % 80),
    axisDeg: (i % 180) - 30,
    leadFindings: LEADS.map(lead => ({
      lead,
      stDeviationMv: Math.random() * 0.4 - 0.2,
      tWaveAmplitudeMv: Math.random(),
      qWave: Math.random() < 0.1,
      qualityScore: Math.random(),
    })),
    outputs: [
      {
        modelId: 'omi-stand-in',
        modelVersion: '0.0.1',
        pOmi: pOmi ?? 0,
        vesselProbabilities: VESSELS.map(vessel => ({ vessel, p: Math.random() })),
        latencyMs: 120 + Math.random() * 50,
      },
    ],
    declined,
    declineReasons: declined ? ['image quality'] : [],
    pOmi,
    culpritVessel: declined ? null : VESSELS[i % 3],
    confidence: declined ? null : Math.random(),
    reviewed: i % 5 === 0,
    reviewerVerdict: i % 5 === 0 ? 'agree' : null,
    tags: ['stand-in', `batch-${Math.floor(i / 100)}`],
    appVersion: '0.0.1',
    schemaVersion: 1,
    deviceModel: 'stand-in',
  };
};
