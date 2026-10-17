// Kiểu dữ liệu và lời gọi API. Mọi thông tin hiển thị đến từ backend (snapshot catalog).

export interface Ref { id: string; name: string }
export interface PlaceRef { id: string; name: string; name_as_sourced: string; place_type: string }
export interface Price { min_vnd: number | null; max_vnd: number | null; has_unknown: boolean; observed_at: string | null }
export interface Badge { claim_type: string; label: string; status: string; status_label: string }

export interface ProductSummary {
  id: string;
  slug: string;
  name_vi: string;
  status: string;
  category: { id: string; name_vi: string };
  brand: Ref | null;
  maker: Ref | null;
  craft_village: PlaceRef | null;
  price: Price;
  image: { id: string; url: string; alt_vi: string } | null;
  materials: string[];
  colors: string[];
  origin_badges: Badge[];
  score?: number;
  matched_fields?: string[];
  similarity?: number | null; // chỉ có khi tìm bằng ảnh; cosine chưa hiệu chỉnh, không hiển thị như %
}

export interface Variant {
  sku: string;
  name_vi?: string;
  attributes?: Record<string, string>;
  price_vnd: number | null;
  original_price_vnd?: number | null;
  observed_at?: string | null;
  availability: string;
}

export interface Claim {
  claim_type: string;
  value: boolean | "unknown";
  status: string;
  label: string;
  status_label: string;
  detail_vi?: string;
  source_ids: string[];
  checked_at: string | null;
  places: PlaceRef[];
}

export interface Source {
  id: string;
  url: string | null;
  title?: string | null;
  publisher: string;
  source_type: string;
  retrieved_at: string;
}

export interface ProductDetail extends ProductSummary {
  category_path: { id: string; name_vi: string }[];
  short_description_vi: string;
  description_vi: string;
  tags: string[];
  intended_uses: string[];
  dimensions: Record<string, number | null | string[]>;
  craft_techniques: string[];
  motifs: string[];
  variants: Variant[];
  origin: { places: PlaceRef[]; manufacturing_country: string | null; brand_origin_country: string | null };
  origin_claims: Claim[];
  certifications: { name: string; issuer?: string | null; source_ids: string[] }[];
  images: { id: string; url: string; alt_vi: string; view_type: string }[];
  sources: Source[];
  updated_at: string;
  reviewed_at: string | null;
}

export interface Facets {
  categories: { id: string; name: string; count: number }[];
  root_categories: { id: string; name: string; count: number }[];
  materials: { value: string; count: number }[];
  colors: { value: string; count: number }[];
  brands: { id: string; name: string; count: number }[];
  craft_villages: { id: string; name: string; count: number }[];
  claim_types: { id: string; name: string; count: number }[];
  price: { known: number; unknown: number; min_vnd: number | null; max_vnd: number | null };
}

export interface Filters {
  category_ids: string[];
  brand_ids: string[];
  place_ids: string[];
  materials: string[];
  colors: string[];
  claim_types: string[];
  price_min: number | null;
  price_max: number | null;
}

export const emptyFilters = (): Filters => ({
  category_ids: [], brand_ids: [], place_ids: [], materials: [], colors: [], claim_types: [],
  price_min: null, price_max: null,
});

export const hasFilters = (f: Filters): boolean =>
  f.price_min != null || f.price_max != null ||
  [f.category_ids, f.brand_ids, f.place_ids, f.materials, f.colors, f.claim_types].some((x) => x.length > 0);

export interface SearchResponse {
  query: string;
  interpreted_query: {
    keywords: string;
    price_label: string | null;
    exclusions: { field: string; value: string; id: string | null; text: string }[];
    expansions: { relation: string; term: string; weight: number; from?: string }[];
    unmatched_terms: string[];
    match_coverage: number | null;
    warnings: string[];
  };
  applied_filters: { key: string; label: string; source: "query" | "user"; hard: boolean }[];
  suggested_filters: { field: string; value: string; id: string | null; text: string }[];
  total: number;
  results: ProductSummary[];
  facets: Facets;
  unknown_price_excluded: number;
  relaxations: { key: string; label: string; count: number }[];
  warnings: string[];
  catalog_version: string;
  timings_ms: { total: number } & Record<string, number>;
  mode?: "voice" | "image";
  transcript?: VoiceTranscript;
  visual?: { model_id: string; revision: string; top_similarity: number | null; match_label: "similar";
    query_cache?: "hit" | "miss" | null };
}

export type VoiceLanguage = "vi" | "en" | "auto";
export interface VoiceTranscript {
  text: string; raw_text?: string; model_id: string; revision: string; duration_s: number; editable: boolean;
  language?: string | null; requested_language?: string | null; language_probability?: number | null;
  truncated?: boolean; requires_confirmation?: boolean;
  quality?: { low_volume: boolean; clipped_fraction: number; gain_db: number };
  suggestions?: { text: string; phrase: string; reason: string; evidence: string }[];
}
export interface VoiceReviewResponse {
  mode: "voice"; transcript: VoiceTranscript; warnings: string[]; timings_ms: { total: number } & Record<string, number>;
}

export interface CategoryNode { id: string; name_vi: string; count: number; children: CategoryNode[] }

export interface ModelStatus {
  state: string; // ok | unavailable | error | index_missing | index_stale | index_invalid
  model_id: string | null;
  revision: string | null;
  reason: string | null;
  detail?: string | null;
}

export interface Health {
  status: string;
  catalog: { version: string; products_visible: number; include_drafts: boolean;
    publication_mode?: "standard" | "internal_demo" } | null;
  search?: { keyword: string; voice: string; image: string; semantic?: string; assistant?: string;
    models?: { voice: ModelStatus; image: ModelStatus; text?: ModelStatus; assistant?: ModelStatus | null } };
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch (error) {
    if (init?.signal?.aborted) throw error;
    throw new ApiError(0, "network", "Không kết nối được máy chủ. Kiểm tra backend đã chạy chưa.");
  }
  if (!res.ok) {
    let code = "http_error";
    let message = `Lỗi máy chủ (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail?.message) {
        code = body.detail.code ?? code;
        message = body.detail.message;
      }
    } catch {
      /* giữ thông báo mặc định */
    }
    throw new ApiError(res.status, code, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),
  categories: () => request<CategoryNode[]>("/categories"),
  brands: () => request<(Ref & { count: number; official_url: string | null })[]>("/brands"),
  places: () => request<(PlaceRef & { count: number })[]>("/places?place_type=craft_village"),
  products: (params: Record<string, string>) =>
    request<{ total: number; results: ProductSummary[] }>(`/products?${new URLSearchParams(params)}`),
  product: (id: string) => request<ProductDetail>(`/products/${encodeURIComponent(id)}`),
  similar: (id: string) => request<{ results: ProductSummary[] }>(`/products/${encodeURIComponent(id)}/similar`),
  suggest: (q: string, signal?: AbortSignal) =>
    request<{ type: string; id: string; text: string }[]>(`/suggest?${new URLSearchParams({ q })}`, { signal }),
  search: (query: string, filters: Filters, limit = 24, offset = 0, signal?: AbortSignal) =>
    request<SearchResponse>("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, filters, limit, offset }),
      signal,
    }),
  searchVoice: (wav: Blob, signal?: AbortSignal) =>
    request<SearchResponse>("/search/voice", { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav, signal }),
  reviewVoice: (wav: Blob, language: VoiceLanguage, signal?: AbortSignal) =>
    request<VoiceReviewResponse>(`/search/voice?${new URLSearchParams({ review: "true", language })}`,
      { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav, signal }),
  /** reuse: same prepared image re-sent for a filter change; the server may reuse its embedding/OCR. */
  searchImage: (image: Blob, text = "", filters?: Filters, signal?: AbortSignal, reuse = false) =>
    request<SearchResponse>(`/search/image?${new URLSearchParams({
      text, ...(filters && hasFilters(filters) ? { filters: JSON.stringify(filters) } : {}),
      ...(reuse ? { reuse: "1" } : {}),
    })}`, {
      method: "POST",
      headers: { "Content-Type": image.type || "image/jpeg" },
      body: image,
      signal,
    }),
};

let healthCache: { at: number; value: Promise<Health> } | null = null;
const HEALTH_TTL_MS = 15_000;

/** /health dùng chung cho các nút giọng nói/ảnh. Hỏi lại sau HEALTH_TTL_MS để thấy model vừa bật/tắt
 *  mà không cần tải lại trang; lỗi thì lần sau hỏi lại ngay. */
export function cachedHealth(refresh = false): Promise<Health> {
  if (refresh || !healthCache || Date.now() - healthCache.at > HEALTH_TTL_MS) {
    const value = api.health();
    healthCache = { at: Date.now(), value };
    value.catch(() => {
      if (healthCache?.value === value) healthCache = null;
    });
  }
  return healthCache.value;
}

export type Modality = "voice" | "image";
const MODALITY_NAME: Record<Modality, string> = { voice: "giọng nói", image: "ảnh" };

/** null nếu sẵn sàng; ngược lại là thông báo cho người dùng. */
export async function modalityProblem(kind: Modality, refresh = false): Promise<string | null> {
  let h: Health;
  try {
    h = await cachedHealth(refresh);
  } catch (e) {
    return e instanceof ApiError ? e.message : "Không kiểm tra được trạng thái máy chủ.";
  }
  const st = h.search?.models?.[kind];
  if (h.search?.[kind] === "ok") return null;
  const reason = st?.reason ?? "model chưa được chọn qua benchmark";
  return `Tìm bằng ${MODALITY_NAME[kind]} chưa sẵn sàng: ${reason}. Bạn vẫn có thể tìm bằng chữ.`;
}

// ---------- Trợ lý tư vấn ----------

export type ConsentLevel = "none" | "history" | "memory";

export interface ReviewStats { count: number; average: number | null }
export interface ReviewSummary extends ReviewStats {
  distribution: Record<string, number>;
  verified_share: number | null;
  aspects: { aspect: string; positive: number; negative: number; review_ids: string[] }[];
  excerpts: { review_id: string; rating: number | null; text: string; origin: string; source_url: string | null;
    verified_purchase: boolean; created_at: string }[];
  note_vi: string;
}
export type ChatCard = ProductSummary & { reason: string; rank: number; review_stats?: ReviewStats };
export interface Evaluation {
  product_id: string;
  rows: { label: string; value: string; field: string }[];
  origin: { label: string; status: string; detail: string | null }[];
  missing: string[];
  description: string;
  reviews: ReviewSummary;
  card: ChatCard;
}
export interface Assessment { suits: string[]; not_suits: string[]; ask_seller: string[] }
export interface Comparison { products: ChatCard[]; rows: { label: string; values: (string | null)[] }[] }

export interface AssistantSession {
  session_id: string;
  consent_level: ConsentLevel;
  consent_needed: boolean;
  consent_options: Record<ConsentLevel, string>;
  greeting_vi: string;
  assistant: { state: "ok" | "basic" | "off"; model: ModelStatus; prompt_version: string };
}
export interface MemoryFact { id: number; kind: string; kind_label: string; label_vi: string; origin: string;
  last_confirmed_at: string; expires_at: string | null }
export interface AssistantMe {
  consent_level: ConsentLevel;
  consent_needed: boolean;
  consent_options: Record<ConsentLevel, string>;
  facts: MemoryFact[];
  sessions: { id: string; started_at: string; ended_at: string | null; summary_vi: string | null;
    first_message: string | null }[];
  assistant: AssistantSession["assistant"];
}

export type AssistantEvent =
  | { kind: "session"; data: { session_id: string; mode: string } }
  | { kind: "status"; data: { stage: string; label: string } }
  | { kind: "delta"; data: { text: string } }
  | { kind: "cards"; data: { items: ChatCard[] } }
  | { kind: "clarify"; data: { question: string } }
  | { kind: "evaluation"; data: Evaluation }
  | { kind: "assessment"; data: Assessment }
  | { kind: "comparison"; data: Comparison }
  | { kind: "saved"; data: { recommendation_ids: number[] } }
  | { kind: "error"; data: { code: string; message: string } }
  | { kind: "done"; data: { intent: string; message: string; fallback: boolean; mode: string;
      timings_ms: Record<string, number> } };

const json = (body: unknown): RequestInit => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

export const assistantApi = {
  createSession: (productId?: string) =>
    request<AssistantSession>("/assistant/sessions", json({ product_id: productId ?? null })),
  session: (sid: string) =>
    request<{ session_id: string; ended_at: string | null; messages: { role: "user" | "assistant"; content: string;
      payload?: { recommendations?: { product_id: string; reason: string }[] } | null }[] }>(
      `/assistant/sessions/${sid}`),
  end: (sid: string) => request<{ ended: boolean }>(`/assistant/sessions/${sid}/end`, { method: "POST" }),
  deleteSession: (sid: string) => request<{ deleted: boolean }>(`/assistant/sessions/${sid}`, { method: "DELETE" }),
  me: () => request<AssistantMe>("/assistant/me"),
  setConsent: (level: ConsentLevel) =>
    request<{ consent_level: ConsentLevel }>("/assistant/me/consent", { ...json({ level }), method: "PUT" }),
  editFact: (id: number, label: string) =>
    request<{ ok: boolean }>(`/assistant/me/facts/${id}`, { ...json({ label_vi: label }), method: "PATCH" }),
  deleteFact: (id: number) => request<{ ok: boolean }>(`/assistant/me/facts/${id}`, { method: "DELETE" }),
  deleteMe: () => request<{ deleted: boolean }>("/assistant/me", { method: "DELETE" }),
  exportMe: () => request<unknown>("/assistant/me/export"),
  recEvent: (id: number, event: "clicked" | "favorited" | "feedback", value?: number) =>
    request<{ ok: boolean }>(`/assistant/recommendations/${id}/event`, json({ event, value: value ?? null })),
  reviews: (pid: string) => request<ReviewSummary>(`/products/${encodeURIComponent(pid)}/reviews`),
  addReview: (pid: string, body: { rating: number; body_vi: string; author_display?: string }) =>
    request<{ status: string; message: string }>(`/products/${encodeURIComponent(pid)}/reviews`, json(body)),
};

/** Gửi tin nhắn và đọc luồng SSE. Lỗi HTTP (429/503/404…) ném ApiError như các lời gọi khác. */
export async function chatStream(sid: string, body: { text: string; input_mode?: "text" | "voice";
  context_product_id?: string | null }, onEvent: (e: AssistantEvent) => void, signal?: AbortSignal): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`/api/assistant/sessions/${sid}/messages`, { ...json(body), signal });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, "network", "Không kết nối được máy chủ. Kiểm tra backend đã chạy chưa.");
  }
  if (!res.ok || !res.body) {
    let code = "http_error";
    let message = `Lỗi máy chủ (${res.status})`;
    try {
      const b = await res.json();
      if (b?.detail?.message) { code = b.detail.code ?? code; message = b.detail.message; }
    } catch { /* giữ mặc định */ }
    throw new ApiError(res.status, code, message);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let terminal = false;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(buf)) !== null) {
        const block = buf.slice(0, boundary.index);
        buf = buf.slice(boundary.index + boundary[0].length);
        let kind = "message";
        const data: string[] = [];
        for (const line of block.split(/\r?\n/)) {
          if (line.startsWith("event:")) kind = line.slice(6).trimStart();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        if (data.length) {
          onEvent({ kind, data: JSON.parse(data.join("\n")) } as AssistantEvent);
          if (kind === "done" || kind === "error") terminal = true;
        }
      }
    }
    if (!terminal) throw new ApiError(0, "stream_incomplete", "Mất kết nối trước khi trợ lý trả lời xong. Bạn thử lại nhé.");
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
