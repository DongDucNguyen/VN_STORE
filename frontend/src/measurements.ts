import type { SearchResponse } from "./api";

// Opt-in, bounded, memory only. Never retain query text, product IDs, images or audio.
export type Kind = "keyword" | "voice" | "image";
export type Outcome = "error" | "cancelled";
export interface Measure { kind: Kind; start: number; epoch: number; done: boolean }
export interface Sample {
  kind: Kind; browser_ms: number; server_ms: Record<string, number>; catalog_version: string;
  model_id: string | null; revision: string | null;
  /** Image re-filtered with server-cached embedding/OCR: a different distribution, never pooled. */
  cached: boolean;
}
let enabled = false;
let epoch = 0;
const samples: Sample[] = [];
// Counts only: failures and cancellations stay out of the latency distribution but must be reported.
const fresh = () => ({ keyword: { error: 0, cancelled: 0 }, voice: { error: 0, cancelled: 0 },
  image: { error: 0, cancelled: 0 } }) as Record<Kind, Record<Outcome, number>>;
let outcomes = fresh();
export function recording() { return enabled; }
export function setRecording(value: boolean) { enabled = value; epoch++; }
export function clearMeasurements() { samples.length = 0; outcomes = fresh(); epoch++; }
export function measurementCount() {
  const failed = Object.values(outcomes).reduce((n, o) => n + o.error + o.cancelled, 0);
  return { samples: samples.length, failed };
}
export function beginMeasure(kind: Kind): Measure | undefined {
  return enabled ? { kind, start: performance.now(), epoch, done: false } : undefined;
}
/** Close a measure that ended without a painted result (failed, cancelled or superseded). */
export function endMeasure(measure: Measure | undefined, outcome: Outcome) {
  if (!measure || measure.done || !enabled || measure.epoch !== epoch) return;
  measure.done = true;
  outcomes[measure.kind][outcome]++;
}
export function snapshotMeasurements() {
  return { version: 2, scope: "keyword_request/voice_stop/image_submit to result paint; excludes recording time and product image downloads",
    quality_benchmark: false, samples: samples.map((s) => ({ ...s, server_ms: { ...s.server_ms } })),
    outcomes: structuredClone(outcomes) };
}
export function afterResultPaint(measure: Measure | undefined, response: SearchResponse) {
  let second = 0;
  const first = requestAnimationFrame(() => {
    second = requestAnimationFrame(() => {
      if (!measure || measure.done || !enabled || measure.epoch !== epoch) return;
      measure.done = true;
      const model = response.transcript ?? response.visual;
      samples.push({ kind: measure.kind, browser_ms: Math.round((performance.now() - measure.start) * 100) / 100,
        server_ms: { ...response.timings_ms }, catalog_version: response.catalog_version,
        model_id: model?.model_id ?? null, revision: model?.revision ?? null,
        cached: response.visual?.query_cache === "hit" });
      if (samples.length > 200) samples.shift();
    });
  });
  // A newer request or leaving the page before paint means the user never saw this result.
  return () => { cancelAnimationFrame(first); cancelAnimationFrame(second); endMeasure(measure, "cancelled"); };
}
