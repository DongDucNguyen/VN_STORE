import { useEffect, useRef, useState } from "react";
import { api, ApiError, modalityProblem } from "../api";
import { MAX_RECORD_SECONDS, MicError, Recorder } from "../media";

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
export function useVoiceSearch(onTranscript: (text: string) => void): VoiceSearch {
  const [state, setState] = useState<VoiceState>({ kind: "idle" });
  const rec = useRef<Recorder | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      rec.current?.cancel();
    };
  }, []);

  const set = (s: VoiceState) => {
    if (alive.current) setState(s);
  };

  async function start() {
    if (state.kind === "recording" || state.kind === "processing") return;
    set({ kind: "checking" });
    const problem = await modalityProblem("voice");
    if (problem) return set({ kind: "error", message: problem, canRetry: false });
    const r = new Recorder();
    try {
      await r.start();
    } catch (e) {
      const kind = e instanceof MicError ? e.kind : "failed";
      return set({ kind: "error", message: (e as Error).message, canRetry: kind !== "unsupported" });
    }
    rec.current = r;
    set({ kind: "recording", startedAt: Date.now() });
  }

  async function stop() {
    const r = rec.current;
    if (!r) return;
    rec.current = null;
    set({ kind: "processing" });
    try {
      const wav = await r.stop();
      const res = await api.searchVoice(wav);
      set({ kind: "idle" });
      if (res.transcript) onTranscript(res.transcript.text);
    } catch (e) {
      const message = e instanceof ApiError || e instanceof MicError ? e.message : "Không xử lý được đoạn ghi âm.";
      set({ kind: "error", message, canRetry: !(e instanceof ApiError && e.code === "model_unavailable") });
    }
  }

  function cancel() {
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
