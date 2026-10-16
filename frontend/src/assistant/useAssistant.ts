// Trạng thái hội thoại với trợ lý: phiên, tin nhắn, stream SSE, hủy yêu cầu cũ, mức đồng ý lưu dữ liệu.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError, assistantApi, chatStream, type Assessment, type AssistantSession, type ChatCard, type Comparison,
  type ConsentLevel, type Evaluation,
} from "../api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: string;
  cards?: ChatCard[];
  evaluation?: Evaluation;
  assessment?: Assessment;
  comparison?: Comparison;
  question?: string;
  recIds?: number[];
  error?: string;
  done?: boolean;
  fallback?: boolean;
  mode?: string;
}

const SESSION_KEY = "vnstore:assistant-session";
export const OPEN_EVENT = "vnstore:assistant-open";

/** Mở khung trợ lý từ nơi khác (trang sản phẩm…), tùy chọn kèm sản phẩm đang xem và câu hỏi soạn sẵn. */
export function openAssistant(detail: { productId?: string; text?: string } = {}) {
  window.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail }));
}

function readSession(): string | null {
  try { return sessionStorage.getItem(SESSION_KEY); } catch { return null; }
}
function writeSession(sid: string | null) {
  try {
    if (sid) sessionStorage.setItem(SESSION_KEY, sid); else sessionStorage.removeItem(SESSION_KEY);
  } catch { /* chế độ riêng tư */ }
}

let seq = 0;
const nextId = () => `m${Date.now()}-${++seq}`;

export function useAssistant() {
  const [session, setSession] = useState<AssistantSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sid = useRef<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; controller.current?.abort(); };
  }, []);

  const patch = useCallback((id: string, f: (m: ChatMessage) => ChatMessage) => {
    if (alive.current) setMessages((ms) => ms.map((m) => (m.id === id ? f(m) : m)));
  }, []);

  /** Mở (hoặc khôi phục) phiên. Trả về id phiên, null nếu trợ lý không dùng được. */
  const ensure = useCallback(async (productId?: string): Promise<string | null> => {
    if (sid.current) return sid.current;
    setError(null);
    const saved = readSession();
    try {
      if (saved) {
        // Tải lại trang: dùng tiếp phiên còn mở của tab này (mở phiên mới sẽ kết thúc phiên cũ).
        try {
          const old = await assistantApi.session(saved);
          if (!old.ended_at) {
            const me = await assistantApi.me();
            const s: AssistantSession = { session_id: saved, consent_level: me.consent_level,
              consent_needed: me.consent_needed, consent_options: me.consent_options, greeting_vi: "",
              assistant: me.assistant };
            if (alive.current) {
              setMessages(old.messages.map((m) => ({ id: nextId(), role: m.role, text: m.content, done: true })));
              setSession(s);
            }
            sid.current = saved;
            return saved;
          }
        } catch { /* phiên cũ đã hết hạn hoặc bị xóa */ }
      }
      const s = await assistantApi.createSession(productId);
      sid.current = s.session_id;
      writeSession(s.session_id);
      if (alive.current) setSession(s);
      return s.session_id;
    } catch (e) {
      if (alive.current) setError(e instanceof ApiError ? e.message : "Không mở được trợ lý.");
      return null;
    }
  }, []);

  const send = useCallback(async (text: string, opts: { inputMode?: "text" | "voice"; productId?: string | null } = {}) => {
    const clean = text.trim();
    if (!clean || busy) return;
    const id = await ensure(opts.productId ?? undefined);
    if (!id) return;
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    const reply: ChatMessage = { id: nextId(), role: "assistant", text: "", status: "Đang gửi…" };
    setMessages((ms) => [...ms, { id: nextId(), role: "user", text: clean, done: true }, reply]);
    setBusy(true);
    setError(null);
    try {
      await chatStream(id, { text: clean, input_mode: opts.inputMode ?? "text", context_product_id: opts.productId ?? null },
        (e) => {
          if (ctrl.signal.aborted) return;
          switch (e.kind) {
            case "status": patch(reply.id, (m) => ({ ...m, status: e.data.label })); break;
            case "delta": patch(reply.id, (m) => ({ ...m, text: m.text + e.data.text, status: undefined })); break;
            case "cards": patch(reply.id, (m) => ({ ...m, cards: e.data.items })); break;
            case "clarify": patch(reply.id, (m) => ({ ...m, question: e.data.question })); break;
            case "evaluation": patch(reply.id, (m) => ({ ...m, evaluation: e.data })); break;
            case "assessment": patch(reply.id, (m) => ({ ...m, assessment: e.data })); break;
            case "comparison": patch(reply.id, (m) => ({ ...m, comparison: e.data })); break;
            case "saved": patch(reply.id, (m) => ({ ...m, recIds: e.data.recommendation_ids })); break;
            case "error": patch(reply.id, (m) => ({ ...m, error: e.data.message, status: undefined, done: true })); break;
            case "done":
              patch(reply.id, (m) => ({ ...m, text: e.data.message || m.text, status: undefined, done: true,
                fallback: e.data.fallback, mode: e.data.mode }));
              break;
          }
        }, ctrl.signal);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      const message = e instanceof ApiError ? e.message : "Mất kết nối với trợ lý. Bạn thử lại nhé.";
      if (e instanceof ApiError && (e.code === "session_not_found" || e.code === "session_ended")) {
        sid.current = null;
        writeSession(null);
      }
      patch(reply.id, (m) => ({ ...m, error: message, status: undefined, done: true }));
    } finally {
      if (controller.current === ctrl) {
        controller.current = null;
        if (alive.current) setBusy(false);
      }
    }
  }, [busy, ensure, patch]);

  const reset = useCallback(async () => {
    controller.current?.abort();
    const old = sid.current;
    sid.current = null;
    writeSession(null);
    setMessages([]);
    setBusy(false);
    setSession(null);
    if (old) {
      try { await assistantApi.end(old); } catch { /* đã kết thúc */ }
    }
  }, []);

  const setConsent = useCallback(async (level: ConsentLevel) => {
    await assistantApi.setConsent(level);
    setSession((s) => (s ? { ...s, consent_level: level, consent_needed: false } : s));
  }, []);

  return { session, messages, busy, error, ensure, send, reset, setConsent };
}
