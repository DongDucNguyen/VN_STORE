import { useEffect, useRef, useState } from "react";
import { Notice } from "../components/common";
import { isSplit, PROMPT_SETS } from "../collect/prompts";
import { makeZip, sha256Hex } from "../collect/zip";
import { MAX_RECORD_SECONDS, MicError, Recorder } from "../media";

// Công cụ nội bộ thu clip cho benchmark voice (benchmarks/voice/README.md). Audio ở lại trong trình
// duyệt cho đến khi người điều phối tải file zip; trang không gửi audio lên máy chủ.

const ID = /^[a-z0-9][a-z0-9_-]{0,39}$/;
const REGIONS = [["bac", "Bắc"], ["trung", "Trung"], ["nam", "Nam"], ["khac", "Khác"], ["unknown", "Không rõ"]];
const ENVS = [["quiet", "Yên tĩnh"], ["noisy", "Ồn"], ["cafe", "Quán cà phê"], ["street", "Ngoài đường"],
              ["unknown", "Không rõ"]];

interface Take {
  wav: Blob;
  url: string;
  seconds: number;
}

function stamp(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}t${p(d.getHours())}${p(d.getMinutes())}`;
}

export function CollectVoicePage() {
  const [speaker, setSpeaker] = useState("");
  const [region, setRegion] = useState("unknown");
  const [device, setDevice] = useState("");
  const [env, setEnv] = useState("quiet");
  const [split, setSplit] = useState("");
  const [consent, setConsent] = useState(false);
  const [evidence, setEvidence] = useState("");
  const [takes, setTakes] = useState<Record<string, Take>>({});
  const [active, setActive] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exported, setExported] = useState<string | null>(null);
  const rec = useRef<Recorder | null>(null);
  const session = useRef(stamp());

  useEffect(() => () => rec.current?.cancel(), []);
  // Tự dừng sau thời lượng tối đa, giống nút micro ở trang tìm kiếm.
  useEffect(() => {
    if (!active) return;
    const t = setTimeout(() => void stop(), MAX_RECORD_SECONDS * 1000);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const ready = ID.test(speaker) && ID.test(device) && !!split && consent && evidence.trim().length > 0;
  // Mỗi split đọc bộ câu riêng; đã ghi thì khóa split để clip không lẫn bộ câu.
  const prompts = isSplit(split) ? PROMPT_SETS[split] : [];

  async function start(id: string) {
    setError(null);
    const r = new Recorder();
    try {
      await r.start();
    } catch (e) {
      setError(e instanceof MicError ? e.message : "Không ghi âm được.");
      return;
    }
    rec.current = r;
    setActive(id);
  }

  async function stop() {
    const r = rec.current;
    const id = active;
    if (!r || !id) return;
    rec.current = null;
    setActive(null);
    try {
      const wav = await r.stop();
      setTakes((t) => {
        if (t[id]) URL.revokeObjectURL(t[id].url);
        return { ...t, [id]: { wav, url: URL.createObjectURL(wav), seconds: (wav.size - 44) / (16000 * 2) } };
      });
    } catch (e) {
      setError(e instanceof MicError ? e.message : "Không xử lý được đoạn ghi âm.");
    }
  }

  async function exportZip() {
    const files: { name: string; data: Uint8Array }[] = [];
    const samples = [];
    for (const p of prompts) {
      const t = takes[p.id];
      if (!t) continue;
      const qid = `${speaker}-${session.current}-${p.id}`;
      const data = new Uint8Array(await t.wav.arrayBuffer());
      files.push({ name: `raw/${qid}.wav`, data });
      samples.push({
        qid, audio_path: `raw/${qid}.wav`, sha256: await sha256Hex(data),
        // Câu mẫu; người duyệt nghe lại và sửa nếu người nói đọc khác.
        reference_text: p.text,
        speaker_id: speaker, region, device, environment: env, split, tags: p.tags,
        consent: { status: "granted", evidence: evidence.trim() },
        transcript_review: null,
      });
    }
    const manifest = { manifest_version: "1.0.0", samples };
    files.unshift({ name: "manifest.json", data: new TextEncoder().encode(JSON.stringify(manifest, null, 1)) });
    const name = `voice-${speaker}-${session.current}.zip`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(makeZip(files));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
    setExported(name);
  }

  const done = Object.keys(takes).length;
  return (
    <div className="page collect-page">
      <h1>Thu âm cho bộ đánh giá giọng nói</h1>
      <Notice tone="warn">
        Công cụ nội bộ. Chỉ thu khi người nói đã ký đồng ý; nhập mã hồ sơ đồng ý, không nhập tên, số điện thoại hay
        email. Âm thanh chỉ nằm trong trình duyệt này cho đến khi bạn tải file zip.
      </Notice>

      <fieldset className="collect-form" disabled={!!active}>
        <legend>Thông tin phiên</legend>
        <label>Mã người nói<input value={speaker} onChange={(e) => setSpeaker(e.target.value.trim().toLowerCase())}
                                   placeholder="vd. s012" /></label>
        <label>Vùng giọng (người nói tự khai)
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label>Mã thiết bị<input value={device} onChange={(e) => setDevice(e.target.value.trim().toLowerCase())}
                                  placeholder="vd. iphone-13" /></label>
        <label>Môi trường
          <select value={env} onChange={(e) => setEnv(e.target.value)}>
            {ENVS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label>Split (do nhóm dữ liệu phân cho người nói này)
          <select value={split} onChange={(e) => setSplit(e.target.value)} disabled={done > 0}>
            <option value="">— chọn —</option>
            <option value="train">train</option>
            <option value="dev">dev</option>
            <option value="test">test</option>
          </select>
        </label>
        <label>Mã hồ sơ đồng ý<input value={evidence} onChange={(e) => setEvidence(e.target.value)}
                                      placeholder="vd. consent-2026-10-012" /></label>
        <label className="check">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>Người nói đã đồng ý cho dùng bản ghi để đánh giá model</span>
        </label>
        {!ready && <p className="muted small">Mã người nói/thiết bị: chữ thường, số, gạch nối. Cần đủ thông tin và đồng ý
          trước khi ghi.</p>}
        {done > 0 && <p className="muted small">Đã có bản ghi nên không đổi split được; mỗi split dùng bộ câu riêng.</p>}
      </fieldset>

      {error && <div className="notice notice-warn" role="alert">{error}</div>}

      {!split && <p className="muted">Chọn split để hiện bộ câu mẫu của split đó.</p>}
      <ol className="prompt-list">
        {prompts.map((p) => {
          const t = takes[p.id];
          const live = active === p.id;
          return (
            <li key={p.id} className={live ? "prompt-live" : ""}>
              <p className="prompt-text">“{p.text}”</p>
              <div className="prompt-actions">
                {live ? (
                  <button className="btn btn-primary" onClick={() => void stop()}>Dừng</button>
                ) : (
                  <button className="btn" disabled={!ready || !!active} onClick={() => void start(p.id)}
                          aria-label={`${t ? "Ghi lại" : "Ghi"} câu ${p.id}`}>
                    {t ? "Ghi lại" : "🎤 Ghi"}
                  </button>
                )}
                {t && !live && (
                  <>
                    <audio controls src={t.url} aria-label={`Nghe lại câu ${p.id}`} />
                    <span className="muted small">{t.seconds.toFixed(1)} giây</span>
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="collect-export">
        <p>Đã ghi {done}/{prompts.length} câu.</p>
        <button className="btn btn-primary" disabled={!ready || !done || !!active} onClick={() => void exportZip()}>
          Tải file zip của phiên
        </button>
        {exported && (
          <p className="muted small" role="status">
            Đã tạo {exported}. Gửi file cho nhóm dữ liệu để nhập bằng scripts/benchmark/import_voice_session.py.
          </p>
        )}
      </div>
    </div>
  );
}
