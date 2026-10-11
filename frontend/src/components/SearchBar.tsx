import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { href, navigate } from "../router";
import { useVoiceSearch, VoicePanel } from "./VoiceSearch";
import { rememberVoice } from "../voiceResult";

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

export function SearchBar({ initial = "", autoFocus = false }: { initial?: string; autoFocus?: boolean }) {
  const [q, setQ] = useState(initial);
  const [sugs, setSugs] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const reqId = useRef(0);
  // Bản chép lời đi qua trang tìm kiếm chung: hiện trong ô tìm để người dùng sửa được.
  const voice = useVoiceSearch((response, measure) => navigate("/search", {
    q: response.transcript!.text, via: "voice", voice_id: rememberVoice(response, measure),
  }));

  useEffect(() => setQ(initial), [initial]);

  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setSugs([]);
      return;
    }
    const id = ++reqId.current;
    const t = setTimeout(() => {
      api
        .suggest(term)
        .then((r) => id === reqId.current && setSugs(r))
        .catch(() => id === reqId.current && setSugs([]));
    }, 150);
    return () => clearTimeout(t);
  }, [q]);

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    voice.cancel();
    setOpen(false);
    if (active >= 0 && sugs[active]) {
      window.location.hash = suggestionHref(sugs[active]).slice(1);
      return;
    }
    navigate("/search", { q: q.trim() });
  }

  return (
    <div className="searchbar">
      <form role="search" onSubmit={submit} className="searchbar-form">
        <input
          type="search"
          value={q}
          autoFocus={autoFocus}
          placeholder="Tìm: bình gốm Bát Tràng dưới 500k…"
          aria-label="Tìm sản phẩm"
          aria-autocomplete="list"
          aria-expanded={open && sugs.length > 0}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
            setActive(-1);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, sugs.length - 1));
            else if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, -1));
            else if (e.key === "Escape") setOpen(false);
          }}
        />
        <button
          type="button"
          className={`icon-btn ${voice.state.kind === "recording" ? "icon-btn-live" : ""}`}
          aria-label={voice.state.kind === "recording" ? "Dừng ghi âm" : "Tìm bằng giọng nói"}
          onClick={() => void (voice.state.kind === "recording" ? voice.stop() : voice.start())}
        >
          🎤
        </button>
        <button type="button" className="icon-btn" aria-label="Tìm bằng ảnh" onClick={() => navigate("/image")}>
          📷
        </button>
        <button type="submit" className="btn btn-primary">
          Tìm
        </button>
      </form>
      {open && sugs.length > 0 && (
        <ul className="suggest" role="listbox">
          {sugs.map((s, i) => (
            <li key={`${s.type}:${s.id}`} role="option" aria-selected={i === active}>
              <a href={suggestionHref(s)} className={i === active ? "active" : ""}>
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
