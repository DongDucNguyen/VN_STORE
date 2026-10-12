import { useEffect, useRef, useState } from "react";
import { api, ApiError, emptyFilters, modalityProblem, type SearchResponse, type VoiceLanguage, type VoiceReviewResponse } from "../api";
import { MAX_RECORD_SECONDS, MicError, Recorder } from "../media";
import { beginMeasure, endMeasure, type Measure } from "../measurements";

type VoiceState =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "recording"; startedAt: number }
  | { kind: "processing" }
  | { kind: "review"; response: VoiceReviewResponse; query: string }
  | { kind: "searching" }
  | { kind: "error"; message: string; canRetry: boolean };

export interface VoiceSearch {
  state: VoiceState;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  cancel: () => void;
  confirm: () => Promise<void>;
  edit: (query: string) => void;
  language: VoiceLanguage;
  setLanguage: (value: VoiceLanguage) => void;
}

/** Bấm để nói → bấm dừng (hoặc tự dừng sau MAX_RECORD_SECONDS) → bản chép lời. */
export function useVoiceSearch(onResult: (response: SearchResponse, measure?: Measure) => void): VoiceSearch {
  const [state, setState] = useState<VoiceState>({ kind: "idle" });
  const rec = useRef<Recorder | null>(null);
  const alive = useRef(true);
  const generation = useRef(0);
  const request = useRef<AbortController | null>(null);
  const busy = useRef(false);
  const [language, setLanguage] = useState<VoiceLanguage>("vi");
  const selectedLanguage = useRef<VoiceLanguage>("vi");
  const reviewTiming = useRef<{ measure?: Measure; at: number } | null>(null);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      generation.current++;
      busy.current = false;
      request.current?.abort();
      rec.current?.cancel();
      endMeasure(reviewTiming.current?.measure, "cancelled");
    };
  }, []);

  const set = (s: VoiceState) => {
    if (alive.current) setState(s);
  };

  async function start() {
    if (busy.current) return;
    endMeasure(reviewTiming.current?.measure, "cancelled");
    reviewTiming.current = null;
    selectedLanguage.current = language;
    busy.current = true;
    const id = ++generation.current;
    const current = () => alive.current && id === generation.current;
    set({ kind: "checking" });
    const problem = await modalityProblem("voice");
    if (!current()) return;
    if (problem) { busy.current = false; return set({ kind: "error", message: problem, canRetry: false }); }
    const r = new Recorder();
    rec.current = r;
    try {
      await r.start();
    } catch (e) {
      if (!current()) return;
      busy.current = false;
      rec.current = null;
      const kind = e instanceof MicError ? e.kind : "failed";
      return set({ kind: "error", message: (e as Error).message, canRetry: kind !== "unsupported" });
    }
    if (!current()) { r.cancel(); return; }
    set({ kind: "recording", startedAt: Date.now() });
  }

  async function stop() {
    const r = rec.current;
    if (!r) return;
    rec.current = null;
    const id = generation.current;
    const current = () => alive.current && id === generation.current;
    const controller = new AbortController();
    request.current = controller;
    const measure = beginMeasure("voice");
    set({ kind: "processing" });
    const superseded = () => {
      if (current()) return false;
      endMeasure(measure, "cancelled");
      return true;
    };
    try {
      const wav = await r.stop();
      if (superseded()) return;
      const res = await api.reviewVoice(wav, selectedLanguage.current, controller.signal);
      if (superseded()) return;
      busy.current = false;
      reviewTiming.current = { measure, at: performance.now() };
      set({ kind: "review", response: res, query: res.transcript.text });
    } catch (e) {
      if (superseded()) return;
      endMeasure(measure, "error");
      busy.current = false;
      const message = e instanceof ApiError || e instanceof MicError ? e.message : "Không xử lý được đoạn ghi âm.";
      set({ kind: "error", message, canRetry: !(e instanceof ApiError && e.code === "model_unavailable") });
    }
  }

  function cancel() {
    generation.current++;
    busy.current = false;
    request.current?.abort();
    rec.current?.cancel();
    rec.current = null;
    endMeasure(reviewTiming.current?.measure, "cancelled");
    reviewTiming.current = null;
    set({ kind: "idle" });
  }

  async function confirm() {
    if (state.kind !== "review" || busy.current || !state.query.trim() || state.query.trim().length > 300) return;
    busy.current = true;
    const { response, query } = state;
    const id = generation.current;
    const controller = new AbortController();
    request.current = controller;
    const timing = reviewTiming.current;
    const measure = timing?.measure;
    // Exclude time spent reading/editing; preserve ASR + retrieval time.
    if (measure && timing) measure.start += performance.now() - timing.at;
    set({ kind: "searching" });
    try {
      const result = await api.search(query.trim(), emptyFilters(), 24, 0, controller.signal);
      if (!alive.current || id !== generation.current) { endMeasure(measure, "cancelled"); return; }
      const total = response.timings_ms.total + result.timings_ms.total;
      reviewTiming.current = null;
      busy.current = false;
      set({ kind: "idle" });
      onResult({ ...result, mode: "voice", transcript: { ...response.transcript, text: query.trim() },
        warnings: [...response.warnings, ...result.warnings],
        timings_ms: { ...response.timings_ms, search: result.timings_ms.total, total } }, measure);
    } catch (e) {
      if (!alive.current || id !== generation.current) { endMeasure(measure, "cancelled"); return; }
      endMeasure(measure, "error");
      reviewTiming.current = { at: performance.now() };
      busy.current = false;
      set({ kind: "review", response: { ...response, warnings: [...response.warnings,
        e instanceof Error ? e.message : "Chưa tìm được. Hãy thử lại."] }, query });
    }
  }

  // Tự dừng khi quá thời lượng cho phép.
  useEffect(() => {
    if (state.kind !== "recording") return;
    const t = setTimeout(() => void stop(), MAX_RECORD_SECONDS * 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  return { state, start, stop, cancel, confirm, language, setLanguage,
    edit: (query) => { if (state.kind === "review") set({ ...state, query }); } };
}

export function VoicePanel({ voice }: { voice: VoiceSearch }) {
  const { state } = voice;
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (state.kind !== "recording") return;
    const t = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(t);
  }, [state.kind]);

  const languageChoice = <label className="voice-language">Ngôn ngữ giọng nói{" "}
    <select aria-label="Ngôn ngữ giọng nói" value={voice.language}
      onChange={(e) => voice.setLanguage(e.target.value as VoiceLanguage)}>
      <option value="vi">Tiếng Việt</option><option value="en">English</option>
      <option value="auto">Tự nhận diện / Việt–Anh</option>
    </select></label>;
  if (state.kind === "idle") return languageChoice;
  if (state.kind === "review") return <section className="voice-panel voice-review" aria-label="Xác nhận bản chép lời">
    <strong>Kiểm tra lời nói trước khi tìm</strong>
    <p>Bản chép lời gốc: <span className="voice-original">{state.response.transcript.raw_text ?? state.response.transcript.text}</span></p>
    {state.response.transcript.language && <p>Ngôn ngữ nhận dạng: {state.response.transcript.language}</p>}
    {state.response.warnings.map((w, i) => <p className="notice notice-warn" key={i}>{w}</p>)}
    <label>Cụm từ dùng để tìm kiếm
      <textarea autoFocus value={state.query} maxLength={300} rows={2}
        aria-label="Cụm từ dùng để tìm kiếm" onChange={(e) => voice.edit(e.target.value)} />
    </label>
    {!!state.response.transcript.suggestions?.length && <div>
      <p>Gợi ý theo catalog — chỉ chọn nếu đúng ý bạn:</p>
      {state.response.transcript.suggestions.map((s) => <button className="btn" key={s.text}
        onClick={() => voice.edit(s.text)}>{s.text}</button>)}
    </div>}
    {languageChoice}
    <div className="voice-actions">
      <button className="btn btn-primary" disabled={!state.query.trim() || state.query.trim().length > 300}
        onClick={() => void voice.confirm()}>Tìm theo câu này</button>
      <button className="btn" onClick={() => void voice.start()}>Ghi lại</button>
      <button className="btn" onClick={voice.cancel}>Hủy</button>
    </div>
  </section>;
  if (state.kind === "checking") {
    return (
      <div className="voice-panel" role="status">
        <span className="spinner" aria-hidden /> Đang chuẩn bị micro…
        <button className="link" onClick={voice.cancel}>Hủy</button>
      </div>
    );
  }
  if (state.kind === "recording") {
    const secs = Math.min(MAX_RECORD_SECONDS, Math.floor((now - state.startedAt) / 1000));
    return (
      <div className="voice-panel voice-live" role="status" aria-live="polite">
        <span className="rec-dot" aria-hidden />
        <span>
          Đang nghe… <b>0:{String(secs).padStart(2, "0")}</b> / 0:{MAX_RECORD_SECONDS}
        </span>
        <span className="voice-actions">
          <button className="btn btn-primary" onClick={() => void voice.stop()}>
            Dừng và xem lời
          </button>
          <button className="btn" onClick={voice.cancel}>
            Hủy
          </button>
        </span>
      </div>
    );
  }
  if (state.kind === "processing" || state.kind === "searching") {
    return (
      <div className="voice-panel" role="status">
        <span className="spinner" aria-hidden /> {state.kind === "processing" ? "Đang chép lời…" : "Đang tìm sản phẩm…"}
        <button className="link" onClick={voice.cancel}>Hủy</button>
      </div>
    );
  }
  return (
    <div className="notice notice-warn voice-panel" role="alert">
      <span>{state.message}</span>{" "}
      <span className="voice-actions">
        {state.canRetry && (
          <button className="link" onClick={() => void voice.start()}>
            Ghi lại
          </button>
        )}
        <button className="link" onClick={voice.cancel}>
          Đóng
        </button>
      </span>
    </div>
  );
}
