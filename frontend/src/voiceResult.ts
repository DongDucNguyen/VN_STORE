import type { SearchResponse } from "./api";
import type { Measure } from "./measurements";

let pending: { id: string; response: SearchResponse; measure?: Measure; expires: number } | null = null;
export function rememberVoice(response: SearchResponse, measure?: Measure): string {
  const id = crypto.randomUUID();
  pending = { id, response, measure, expires: performance.now() + 30_000 };
  setTimeout(() => { if (pending?.id === id) pending = null; }, 30_000);
  return id;
}
export function voiceResult(id: string | null, text: string) {
  if (pending && performance.now() > pending.expires) pending = null;
  return pending?.id === id && pending.response.transcript?.text === text ? pending : null;
}
