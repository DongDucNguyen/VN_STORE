import { useEffect, useRef, useState } from "react";
import { api, ApiError, modalityProblem, type SearchResponse } from "../api";
import { MAX_RECORD_SECONDS, MicError, Recorder } from "../media";
import { beginMeasure, endMeasure, type Measure } from "../measurements";

type VoiceState =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "recording"; startedAt: number }
  | { kind: "processing" }
  | { kind: "error"; message: string; canRetry: boolean };

export interface VoiceSearch {
  state: VoiceState;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  cancel: () => void;
}

/** Bấm để nói → bấm dừng (hoặc tự dừng sau MAX_RECORD_SECONDS) → bản chép lời. */
export function useVoiceSearch(onResult: (response: SearchResponse, measure?: Measure) => void): VoiceSearch {
  const [state, setState] = useState<VoiceState>({ kind: "idle" });
  const rec = useRef<Recorder | null>(null);
  const alive = useRef(true);
  const generation = useRef(0);
  const request = useRef<AbortController | null>(null);
  const busy = useRef(false);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      generation.current++;
      busy.current = false;
      request.current?.abort();
      rec.current?.cancel();
    };
  }, []);

  const set = (s: VoiceState) => {
    if (alive.current) setState(s);
  };

  async function start() {
    if (busy.current) return;
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
      const res = await api.searchVoice(wav, controller.signal);
      if (superseded()) return;
      busy.current = false;
      set({ kind: "idle" });
      if (res.transcript) onResult(res, measure);
      else endMeasure(measure, "error");
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
    set({ kind: "idle" });
  }

  // Tự dừng khi quá thời lượng cho phép.
  useEffect(() => {
    if (state.kind !== "recording") return;
    const t = setTimeout(() => void stop(), MAX_RECORD_SECONDS * 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  return { state, start, stop, cancel };
}

export function VoicePanel({ voice }: { voice: VoiceSearch }) {
  const { state } = voice;
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (state.kind !== "recording") return;
    const t = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(t);
  }, [state.kind]);

  if (state.kind === "idle") return null;
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
            Dừng và tìm
          </button>
          <button className="btn" onClick={voice.cancel}>
            Hủy
          </button>
        </span>
      </div>
    );
  }
  if (state.kind === "processing") {
    return (
      <div className="voice-panel" role="status">
        <span className="spinner" aria-hidden /> Đang chép lời…
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
