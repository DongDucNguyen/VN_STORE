import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api";
import { ripple } from "../hooks/ripple";
import { href, navigate } from "../router";
import { useVoiceSearch, VoicePanel } from "./VoiceSearch";
import { rememberVoice } from "../voiceResult";
import { Icon } from "./ui/Icon";

type Suggestion = { type: string; id: string; text: string };

const TYPE_LABEL: Record<string, string> = {
  product: "Sản phẩm",
  category: "Danh mục",
  brand: "Thương hiệu",
  place: "Làng nghề",
};

function suggestionHref(s: Suggestion): string {
  if (s.type === "product") return href(`/p/${s.id}`);
  if (s.type === "category") return href("/search", { cat: s.id });
  if (s.type === "brand") return href("/search", { brand: s.id });
  if (s.type === "place") return href("/search", { place: s.id });
  return href("/search", { q: s.text });
}

export function SearchBar({ initial = "", size = "md" }: { initial?: string; size?: "md" | "lg" }) {
  const [q, setQ] = useState(initial);
  const [sugs, setSugs] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const reqId = useRef(0);
  const submitRef = useRef<HTMLButtonElement>(null);
  const listId = useId();
  // Bản chép lời đi qua trang tìm kiếm chung: hiện trong ô tìm để người dùng sửa được.
  const voice = useVoiceSearch((response, measure) => navigate("/search", {
    q: response.transcript!.text, via: "voice", voice_id: rememberVoice(response, measure),
  }));

  useEffect(() => setQ(initial), [initial]);

  useEffect(() => {
    const term = q.trim();
    const id = ++reqId.current;
    setSugs([]);
    setActive(-1);
    if (term.length < 2 || term.length > 200) {
      return;
    }
    const controller = new AbortController();
    const t = setTimeout(() => {
      api
        .suggest(term, controller.signal)
        .then((r) => id === reqId.current && setSugs(r))
        .catch(() => id === reqId.current && setSugs([]));
    }, 150);
    return () => {
      clearTimeout(t);
      controller.abort();
      reqId.current++;
    };
  }, [q]);

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    ripple(submitRef.current);
    voice.cancel();
    setOpen(false);
    if (open && active >= 0 && sugs[active]) {
      window.location.hash = suggestionHref(sugs[active]).slice(1);
      return;
    }
    navigate("/search", { q: q.trim() });
  }

  const recording = voice.state.kind === "recording";
  const expanded = open && sugs.length > 0;
  return (
    <div className={`searchbar searchbar-${size}`}>
      <form role="search" onSubmit={submit} className="searchbar-form">
        <div className="search-field">
          <Icon name="search" size={20} className="search-field-icon" />
          <input
            type="search"
            value={q}
            maxLength={300}
            placeholder="Bạn đang tìm món gì?"
            aria-label="Tìm sản phẩm"
            aria-autocomplete="list"
            aria-expanded={expanded}
            aria-controls={expanded ? listId : undefined}
            aria-activedescendant={expanded && active >= 0 ? `${listId}-${active}` : undefined}
            autoComplete="off"
            onChange={(e) => {
              setQ(e.target.value);
              setOpen(true);
              setActive(-1);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            onKeyDown={(e) => {
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                setOpen(true);
                setActive((a) => e.key === "ArrowDown" ? Math.min(a + 1, sugs.length - 1) : Math.max(a - 1, -1));
              } else if (e.key === "Escape") {
                e.preventDefault();
                setOpen(false);
                setActive(-1);
              }
            }}
          />
          {/* Desktop: nằm trong ô tìm. Mobile: xuống một hàng riêng kèm nhãn chữ để không phải đoán icon. */}
          <div className="search-modes">
            <button
              type="button"
              className={`field-btn ${recording ? "is-live" : ""}`}
              aria-label={recording ? "Dừng ghi âm" : "Tìm bằng giọng nói"}
              onClick={() => void (recording ? voice.stop() : voice.start())}
            >
              <Icon name={recording ? "stop" : "microphone"} size={20} />
              <span className="mode-label" aria-hidden="true">{recording ? "Dừng ghi âm" : "Tìm bằng giọng nói"}</span>
            </button>
            <button type="button" className="field-btn" aria-label="Tìm bằng ảnh" onClick={() => navigate("/image")}>
              <Icon name="camera" size={20} />
              <span className="mode-label" aria-hidden="true">Tìm bằng ảnh</span>
            </button>
          </div>
        </div>
        <button type="submit" className="btn btn-primary search-submit" ref={submitRef}>
          Tìm
        </button>
      </form>
      {expanded && (
        <ul className="suggest" role="listbox" id={listId} aria-label="Gợi ý tìm kiếm">
          {sugs.map((s, i) => (
            <li key={`${s.type}:${s.id}`} id={`${listId}-${i}`} role="option" aria-selected={i === active}>
              {/* mousedown chặn blur để click gợi ý không bị mất */}
              <a href={suggestionHref(s)} className={i === active ? "active" : ""} tabIndex={-1}
                onMouseDown={(e) => e.preventDefault()}>
                <span>{s.text}</span>
                <small>{TYPE_LABEL[s.type] ?? s.type}</small>
              </a>
            </li>
          ))}
        </ul>
      )}
      <VoicePanel voice={voice} />
    </div>
  );
}
