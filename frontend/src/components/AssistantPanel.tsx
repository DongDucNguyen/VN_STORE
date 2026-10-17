import { useEffect, useRef, useState } from "react";
import {
  api, ApiError, assistantApi, modalityProblem, type Assessment, type ChatCard, type Comparison, type ConsentLevel,
  type Evaluation,
} from "../api";
import { OPEN_EVENT, useAssistant, type ChatMessage } from "../assistant/useAssistant";
import { formatPrice } from "../format";
import { isNarrow, useDialogFocus } from "../hooks/useDialogFocus";
import { MicError, Recorder } from "../media";
import { href } from "../router";
import { LotusMark, WaterRipple } from "./brand/Motifs";
import { ProductImage } from "./ProductImage";
import { Icon } from "./ui/Icon";

const STARTERS = [
  "Gợi ý quà tặng mẹ khoảng 500k",
  "Tìm giỏ mây có quai để đi chợ",
  "Đồ gốm trang trí phòng khách dưới 1 triệu",
];

function Stars({ stats }: { stats?: { count: number; average: number | null } }) {
  if (!stats || !stats.count) return <span className="muted">Chưa có đánh giá</span>;
  return <span>★ {stats.average?.toFixed(1).replace(".", ",")} · {stats.count} đánh giá</span>;
}

function CardRow({ c, recId, onOpen }: { c: ChatCard; recId?: number; onOpen: () => void }) {
  const [vote, setVote] = useState(0);
  const send = (v: number) => {
    if (recId == null) return;
    setVote(v);
    assistantApi.recEvent(recId, "feedback", v).catch(() => setVote(0));
  };
  return (
    <li className="chat-card">
      <a href={href(`/p/${c.id}`)} onClick={() => { if (recId != null) assistantApi.recEvent(recId, "clicked").catch(() => {}); onOpen(); }}>
        <div className="chat-card-img">
          {c.image ? <ProductImage src={c.image.url} alt={c.image.alt_vi} /> : <div className="img-missing">Chưa có ảnh</div>}
        </div>
        <div className="chat-card-body">
          <strong>{c.rank}. {c.name_vi}</strong>
          <span className={c.price.min_vnd == null ? "price-unknown" : "chat-price"}>{formatPrice(c.price)}</span>
          <span className="small muted">{c.brand?.name ?? c.maker?.name ?? "Chưa rõ thương hiệu"} · <Stars stats={c.review_stats} /></span>
          {c.reason && <span className="chat-reason">Vì sao gợi ý: {c.reason}</span>}
          {c.origin_badges.length > 0 && (
            <span className="small chat-origin">{c.origin_badges.map((b) => b.label).join(" · ")}</span>
          )}
        </div>
      </a>
      {recId != null && (
        <div className="chat-vote" role="group" aria-label="Gợi ý này có hữu ích không?">
          <button className={`vote-btn ${vote === 1 ? "on" : ""}`} aria-pressed={vote === 1} aria-label="Hữu ích" onClick={() => send(1)}>
            <Icon name="check" size={16} /> <span aria-hidden="true">Hữu ích</span>
          </button>
          <button className={`vote-btn ${vote === -1 ? "on" : ""}`} aria-pressed={vote === -1} aria-label="Không hữu ích" onClick={() => send(-1)}>
            <Icon name="close" size={16} /> <span aria-hidden="true">Không</span>
          </button>
        </div>
      )}
    </li>
  );
}

function EvaluationBlock({ ev, assessment }: { ev: Evaluation; assessment?: Assessment }) {
  const rv = ev.reviews;
  return (
    <div className="chat-eval">
      <a href={href(`/p/${ev.product_id}`)} className="chat-eval-title">{ev.card.name_vi}</a>
      <h4>Thông tin từ catalog</h4>
      <dl className="chat-facts">
        {ev.rows.map((r) => (<div key={r.label}><dt>{r.label}</dt><dd>{r.value}</dd></div>))}
      </dl>
      <h4>Nguồn gốc</h4>
      <ul className="chat-list">
        {ev.origin.map((o) => (<li key={o.label}>{o.label}: <span className={o.status === "Chưa rõ" ? "muted" : ""}>{o.status}</span></li>))}
      </ul>
      <h4>Khách hàng nói gì</h4>
      {rv.count === 0 ? <p className="muted">{rv.note_vi}</p> : (
        <>
          <p>★ {rv.average?.toFixed(1).replace(".", ",")} / 5 từ {rv.count} đánh giá. <span className="muted">{rv.note_vi}</span></p>
          {rv.aspects.length > 0 && (
            <ul className="chat-list">
              {rv.aspects.slice(0, 5).map((a) => (<li key={a.aspect}>{a.aspect}: {a.positive} khen, {a.negative} chê</li>))}
            </ul>
          )}
          <ul className="chat-quotes">
            {rv.excerpts.slice(0, 3).map((x) => (<li key={x.review_id}>“{x.text}” <span className="muted small">({x.rating}★{x.verified_purchase ? ", đã mua" : ""})</span></li>))}
          </ul>
        </>
      )}
      {assessment && (assessment.suits.length > 0 || assessment.not_suits.length > 0) && (
        <>
          <h4>Nhận định của trợ lý <span className="muted small">(suy ra từ thông tin trên)</span></h4>
          {assessment.suits.length > 0 && <p><strong>Phù hợp khi:</strong> {assessment.suits.join("; ")}</p>}
          {assessment.not_suits.length > 0 && <p><strong>Cân nhắc:</strong> {assessment.not_suits.join("; ")}</p>}
        </>
      )}
      {(ev.missing.length > 0 || (assessment?.ask_seller.length ?? 0) > 0) && (
        <p className="small muted">
          Còn thiếu: {[...ev.missing, ...(assessment?.ask_seller ?? [])].join("; ")}. Bạn nên hỏi thêm người bán.
        </p>
      )}
    </div>
  );
}

function ComparisonTable({ cmp }: { cmp: Comparison }) {
  return (
    <div className="chat-compare">
      <table>
        <thead><tr><th></th>{cmp.products.map((p) => <th key={p.id}><a href={href(`/p/${p.id}`)}>{p.name_vi}</a></th>)}</tr></thead>
        <tbody>
          <tr><th>Giá</th>{cmp.products.map((p) => <td key={p.id}>{formatPrice(p.price)}</td>)}</tr>
          {cmp.rows.filter((r) => r.label !== "Giá").map((r) => (
            <tr key={r.label}><th>{r.label}</th>{r.values.map((v, i) => <td key={i}>{v ?? <span className="muted">chưa có</span>}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Bubble({ m, onRetry, onClose, onQuick }: { m: ChatMessage; onRetry: () => void; onClose: () => void;
  onQuick: (t: string) => void }) {
  if (m.role === "user") return <div className="msg msg-user">{m.text}</div>;
  return (
    <div className="msg msg-bot">
      {m.evaluation && <EvaluationBlock ev={m.evaluation} assessment={m.assessment} />}
      {m.comparison && <ComparisonTable cmp={m.comparison} />}
      {m.text && <p className="msg-text">{m.text}</p>}
      {m.status && <p className="msg-status" role="status"><span className="spinner" aria-hidden /> {m.status}</p>}
      {m.cards && m.cards.length > 0 && !m.evaluation && (
        <ul className="chat-cards">
          {m.cards.map((c, i) => <CardRow key={c.id} c={c} recId={m.recIds?.[i]} onOpen={onClose} />)}
        </ul>
      )}
      {m.question && (
        <p className="msg-question"><Icon name="info" size={16} /> {m.question}</p>
      )}
      {m.done && m.cards && m.cards.length > 0 && !m.evaluation && (
        <div className="chips">
          <button className="chip chip-suggest" onClick={() => onQuick("So sánh #1 và #2")}>So sánh #1 và #2</button>
          <button className="chip chip-suggest" onClick={() => onQuick("Sản phẩm #1 có tốt không?")}>#1 có tốt không?</button>
          <button className="chip chip-suggest" onClick={() => onQuick("Còn mẫu nào khác không?")}>Mẫu khác</button>
        </div>
      )}
      {m.mode === "basic" && m.done && (
        <p className="small muted">Trợ lý đang chạy chế độ cơ bản (chưa bật model ngôn ngữ): gợi ý lấy trực tiếp từ kết quả tìm kiếm.</p>
      )}
      {m.error && (
        <div className="notice notice-warn" role="alert">
          <Icon name="alert" size={18} className="notice-icon" />
          <div>{m.error} <button className="link" onClick={onRetry}>Thử lại</button></div>
        </div>
      )}
    </div>
  );
}

function ConsentBox({ options, current, onChoose }: { options: Record<ConsentLevel, string>; current: ConsentLevel;
  onChoose: (l: ConsentLevel) => void }) {
  const [level, setLevel] = useState<ConsentLevel>(current);
  return (
    <form className="consent" onSubmit={(e) => { e.preventDefault(); onChoose(level); }}>
      <p><strong>Trợ lý có nên lưu cuộc trò chuyện không?</strong></p>
      <p className="small muted">Mặc định không lưu. Bạn chọn một mức rồi bấm Lưu lựa chọn.</p>
      {(["none", "history", "memory"] as ConsentLevel[]).map((l) => (
        <label key={l} className="check">
          <input type="radio" name="consent" value={l} checked={level === l} onChange={() => setLevel(l)} />
          <span>{options[l]}</span>
        </label>
      ))}
      <button className="btn btn-primary" type="submit">Lưu lựa chọn</button>
      <p className="small muted">Đổi bất cứ lúc nào ở trang <a href={href("/assistant/memory")}>Trợ lý ghi nhớ gì</a>.</p>
    </form>
  );
}

export function AssistantPanel({ hideLauncher = false }: { hideLauncher?: boolean }) {
  const a = useAssistant();
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState(false);
  const [input, setInput] = useState("");
  const [inputMode, setInputMode] = useState<"text" | "voice">("text");
  const [context, setContext] = useState<{ id: string; name: string } | null>(null);
  const [voice, setVoice] = useState<"idle" | "recording" | "processing">("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [unseen, setUnseen] = useState(false);
  const [announce, setAnnounce] = useState("");
  const rec = useRef<Recorder | null>(null);
  const panelRef = useRef<HTMLElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const nearBottom = useRef(true);
  const last = useRef<{ text: string; mode: "text" | "voice"; pid: string | null } | null>(null);

  // Desktop: nonmodal, vẫn xem sản phẩm bên cạnh. Màn hình hẹp: toàn màn hình, modal, giữ focus trong panel.
  useDialogFocus(open, panelRef, () => setOpen(false), modal);

  useEffect(() => {
    const onOpen = (e: Event) => {
      const d = (e as CustomEvent<{ productId?: string; text?: string }>).detail ?? {};
      setModal(isNarrow());
      setOpen(true);
      if (d.productId) {
        api.product(d.productId).then((p) => setContext({ id: p.id, name: p.name_vi })).catch(() => setContext(null));
      }
      if (d.text) setInput(d.text);
      setTimeout(() => inputRef.current?.focus(), 50);
    };
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (open) a.ensure(context?.id).catch(() => {});
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  // Nền phía sau không cuộn khi panel phủ toàn màn hình.
  useEffect(() => {
    if (!open || !modal) return;
    document.body.classList.add("is-locked");
    return () => document.body.classList.remove("is-locked");
  }, [open, modal]);

  // Chỉ tự cuộn khi người dùng đang ở gần cuối; đang đọc lịch sử thì giữ vị trí và báo có tin mới.
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    if (nearBottom.current) el.scrollTo({ top: el.scrollHeight });
    else setUnseen(true);
  }, [a.messages]);

  // Báo ngắn cho trình đọc màn hình khi một câu trả lời hoàn chỉnh, không đọc lại từng token. Lỗi đã có role=alert.
  const lastMsg = a.messages[a.messages.length - 1];
  useEffect(() => {
    if (lastMsg?.role === "assistant" && lastMsg.done && !lastMsg.error) {
      setAnnounce(lastMsg.cards?.length ? `Trợ lý đã trả lời, kèm ${lastMsg.cards.length} gợi ý.` : "Trợ lý đã trả lời.");
    }
  }, [lastMsg?.id, lastMsg?.done]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => rec.current?.cancel(), []);

  const show = () => {
    setModal(isNarrow());
    nearBottom.current = true;
    setOpen(true);
  };

  const submit = (text = input, mode = inputMode) => {
    if (!text.trim() || a.busy) return;
    last.current = { text, mode, pid: context?.id ?? null };
    nearBottom.current = true;
    setUnseen(false);
    a.send(text, { inputMode: mode, productId: context?.id ?? null });
    setInput("");
    setInputMode("text");
  };

  async function toggleVoice() {
    setVoiceError(null);
    if (voice === "recording" && rec.current) {
      const r = rec.current;
      rec.current = null;
      setVoice("processing");
      try {
        const wav = await r.stop();
        const res = await api.reviewVoice(wav, "vi");
        setInput(res.transcript.text);
        setInputMode("voice");
        inputRef.current?.focus();
      } catch (e) {
        setVoiceError(e instanceof ApiError || e instanceof MicError ? e.message : "Không xử lý được đoạn ghi âm.");
      }
      setVoice("idle");
      return;
    }
    const problem = await modalityProblem("voice");
    if (problem) { setVoiceError(problem); return; }
    const r = new Recorder();
    rec.current = r;
    try {
      await r.start();
      setVoice("recording");
    } catch (e) {
      rec.current = null;
      setVoiceError((e as Error).message);
    }
  }

  const s = a.session;
  return (
    <>
      {!open && !hideLauncher && (
        <button className="assistant-fab" onClick={show} aria-label="Mở trợ lý mua sắm">
          <LotusMark size={22} /> <span>Trợ lý</span>
        </button>
      )}
      {open && (
        <section className={`assistant-panel ${modal ? "is-modal" : ""}`} role="dialog" aria-label="Trợ lý mua sắm"
          aria-modal={modal} ref={panelRef}>
          <header className="assistant-head">
            <span className="assistant-title">
              <LotusMark size={26} className="nv-lotus is-playing" />
              <strong>Trợ lý VNStore</strong>
              {s?.assistant.state === "basic" && <span className="chip chip-static">Cơ bản</span>}
            </span>
            <span className="assistant-actions">
              <button className="link" onClick={() => a.reset()} disabled={!a.messages.length}>Cuộc trò chuyện mới</button>
              <a href={href("/assistant/memory")} onClick={() => setOpen(false)}>Ghi nhớ</a>
              <button className="icon-link" aria-label="Đóng trợ lý" onClick={() => setOpen(false)}>
                <Icon name="close" size={22} />
              </button>
            </span>
          </header>
          <div className="assistant-body" ref={listRef}
            onScroll={(e) => {
              const el = e.currentTarget;
              nearBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
              if (nearBottom.current) setUnseen(false);
            }}>
            {a.error && (
              <div className="notice notice-warn" role="alert">
                <Icon name="alert" size={18} className="notice-icon" />
                <div>{a.error} <a href={href("/search")}>Tìm bằng ô tìm kiếm</a></div>
              </div>
            )}
            {s?.consent_needed && <ConsentBox options={s.consent_options} current={s.consent_level} onChoose={(l) => a.setConsent(l).catch(() => {})} />}
            {!a.messages.length && (
              <div className="msg msg-bot msg-welcome">
                <LotusMark size={40} className="welcome-lotus" />
                <p className="msg-text">{s?.greeting_vi || "Chào bạn, mình có thể giúp bạn tìm sản phẩm hợp nhu cầu."}</p>
                <div className="chips">
                  {STARTERS.map((t) => (
                    <button key={t} className="chip chip-suggest" onClick={() => submit(t, "text")}>{t}</button>
                  ))}
                </div>
                <p className="small muted">Trợ lý chỉ dùng thông tin trong catalog VNStore; giá và nguồn gốc lấy từ dữ liệu đã kiểm tra.</p>
              </div>
            )}
            {a.messages.map((m) => (
              <Bubble key={m.id} m={m} onClose={() => { if (isNarrow()) setOpen(false); }}
                onRetry={() => last.current && a.send(last.current.text, { inputMode: last.current.mode, productId: last.current.pid })}
                onQuick={(t) => submit(t, "text")} />
            ))}
          </div>
          <p className="sr-only" aria-live="polite">{announce}</p>
          {unseen && (
            <button type="button" className="new-messages" onClick={() => {
              listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
              nearBottom.current = true;
              setUnseen(false);
            }}>
              Có tin nhắn mới <Icon name="chevron" size={16} />
            </button>
          )}
          <form className="assistant-input" onSubmit={(e) => { e.preventDefault(); submit(); }}>
            <WaterRipple className="composer-water" />
            {context && (
              <div className="chips">
                <span className="chip chip-hard">Đang hỏi về: {context.name}
                  <button type="button" className="chip-x" aria-label="Bỏ sản phẩm đang hỏi" onClick={() => setContext(null)}>
                    <Icon name="close" size={14} />
                  </button>
                </span>
              </div>
            )}
            {voiceError && <p className="small field-error" role="alert">{voiceError}</p>}
            {voice === "recording" && <p className="small voice-live-line"><span className="rec-dot" aria-hidden /> Đang ghi âm — bấm nút dừng khi nói xong.</p>}
            {voice === "processing" && <p className="small muted">Đang chép lời…</p>}
            {inputMode === "voice" && <p className="small muted">Bản chép lời từ giọng nói — bạn có thể sửa câu vừa nói rồi bấm Gửi.</p>}
            <div className="assistant-row">
              <textarea ref={inputRef} rows={2} maxLength={1000} value={input} placeholder="Bạn cần tìm gì? Ví dụ: quà tân gia dưới 500k"
                aria-label="Tin nhắn cho trợ lý" onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  // Không gửi khi bộ gõ tiếng Việt (IME) đang ghép chữ.
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); }
                }} />
              <button type="button" className={`icon-link composer-mic ${voice === "recording" ? "is-live" : ""}`} onClick={toggleVoice}
                disabled={voice === "processing"} aria-label={voice === "recording" ? "Dừng ghi âm" : "Nói với trợ lý"}>
                <Icon name={voice === "recording" ? "stop" : "microphone"} size={22} />
              </button>
              <button className="btn btn-primary" type="submit" disabled={a.busy || !input.trim()}>Gửi</button>
            </div>
          </form>
        </section>
      )}
    </>
  );
}
