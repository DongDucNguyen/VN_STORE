import { useEffect, useState } from "react";
import { api, ApiError, modalityProblem } from "../api";
import { Notice } from "../components/common";
import { makeZip, readZip, sha256Hex, ZipError } from "../collect/zip";

// Công cụ nội bộ duyệt bản chép lời của một phiên thu âm (benchmarks/voice/README.md). Người duyệt nghe
// từng clip, sửa reference_text cho đúng điều người nói đã nói, rồi xác nhận; trang chỉ ghi
// transcript_review cho clip được xác nhận, với tên người duyệt do người đó tự nhập.
// Zip xuất ra cùng định dạng với zip thu âm: nhập mới bằng import_voice_session.py, hoặc áp vào manifest
// đã nhập bằng apply_voice_review.py.

interface Sample {
  qid: string;
  audio_path: string;
  sha256: string;
  reference_text: string | null;
  speaker_id: string;
  split: string;
  tags?: string[];
  transcript_review: { reviewed_by: string; reviewed_at: string } | null;
  [key: string]: unknown;
}

interface Edit {
  text: string;
  silent: boolean;
  confirmed: boolean;
}

interface Session {
  name: string;
  manifest: { manifest_version: string; samples: Sample[] };
  files: { name: string; data: Uint8Array }[];
  urls: Record<string, string>;
}

const MAX_TEXT = 2000;

async function loadSession(file: File): Promise<Session> {
  const files = await readZip(await file.arrayBuffer());
  const byName = new Map(files.map((f) => [f.name, f.data]));
  const raw = byName.get("manifest.json");
  if (!raw) throw new ZipError("Zip thiếu manifest.json — hãy chọn file zip xuất từ trang thu âm.");
  let manifest: Session["manifest"];
  try {
    manifest = JSON.parse(new TextDecoder().decode(raw));
  } catch {
    throw new ZipError("manifest.json không phải JSON hợp lệ.");
  }
  if (manifest?.manifest_version !== "1.0.0" || !Array.isArray(manifest.samples) || !manifest.samples.length)
    throw new ZipError("manifest.json không đúng phiên bản 1.0.0 hoặc không có clip.");
  const urls: Record<string, string> = {};
  for (const s of manifest.samples) {
    const data = byName.get(s.audio_path);
    if (!data) throw new ZipError(`${s.qid}: thiếu file ${s.audio_path}.`);
    if ((await sha256Hex(data)) !== s.sha256) throw new ZipError(`${s.qid}: SHA-256 không khớp file âm thanh.`);
    urls[s.qid] = URL.createObjectURL(new Blob([data as BlobPart], { type: "audio/wav" }));
  }
  return { name: file.name, manifest, files, urls };
}

export function ReviewVoicePage() {
  const [session, setSession] = useState<Session | null>(null);
  const [edits, setEdits] = useState<Record<string, Edit>>({});
  const [reviewer, setReviewer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [asrProblem, setAsrProblem] = useState<string | null>("");
  const [hints, setHints] = useState<Record<string, string>>({});
  const [exported, setExported] = useState<string | null>(null);

  useEffect(() => () => Object.values(session?.urls ?? {}).forEach((u) => URL.revokeObjectURL(u)), [session]);
  useEffect(() => {
    void modalityProblem("voice").then(setAsrProblem);
  }, []);

  async function open(file: File | undefined) {
    if (!file) return;
    setError(null);
    setExported(null);
    try {
      const s = await loadSession(file);
      setSession(s);
      setHints({});
      setEdits(Object.fromEntries(s.manifest.samples.map((x) => [x.qid, {
        text: x.reference_text ?? "", silent: x.reference_text === null, confirmed: false,
      }])));
    } catch (e) {
      setSession(null);
      setError(e instanceof ZipError ? e.message : "Không đọc được file zip.");
    }
  }

  function patch(qid: string, change: Partial<Edit>) {
    setExported(null);
    // Sửa nội dung thì phải xác nhận lại sau khi nghe.
    setEdits((all) => ({ ...all, [qid]: { ...all[qid], confirmed: false, ...change } }));
  }

  async function hint(s: Sample) {
    const data = session?.files.find((f) => f.name === s.audio_path)?.data;
    if (!data) return;
    setHints((h) => ({ ...h, [s.qid]: "Đang chạy ASR…" }));
    try {
      const r = await api.searchVoice(new Blob([data as BlobPart], { type: "audio/wav" }));
      setHints((h) => ({ ...h, [s.qid]: r.transcript?.text || "(ASR không trả chữ)" }));
    } catch (e) {
      setHints((h) => ({ ...h, [s.qid]: e instanceof ApiError ? `Không có gợi ý: ${e.message}` : "Không có gợi ý." }));
    }
  }

  const problems = session ? session.manifest.samples.flatMap((s) => {
    const e = edits[s.qid];
    if (!e?.confirmed) return [];
    if (!e.silent && !e.text.trim()) return [`${s.qid}: bản chép lời trống (đánh dấu im lặng nếu không có lời)`];
    if (e.text.trim().length > MAX_TEXT) return [`${s.qid}: bản chép lời dài quá ${MAX_TEXT} ký tự`];
    return [];
  }) : [];
  const confirmed = Object.values(edits).filter((e) => e.confirmed).length;
  const canExport = !!session && reviewer.trim().length > 0 && confirmed > 0 && problems.length === 0;

  function exportZip() {
    if (!session) return;
    const now = new Date().toISOString();
    const samples = session.manifest.samples.map((s) => {
      const e = edits[s.qid];
      if (!e.confirmed) return s; // giữ nguyên clip chưa xác nhận
      return {
        ...s,
        reference_text: e.silent ? null : e.text.trim().normalize("NFC"),
        transcript_review: { reviewed_by: reviewer.trim(), reviewed_at: now },
      };
    });
    const manifest = { ...session.manifest, samples };
    const files = [
      { name: "manifest.json", data: new TextEncoder().encode(JSON.stringify(manifest, null, 1)) },
      ...session.files.filter((f) => f.name !== "manifest.json"),
    ];
    const base = session.name.replace(/\.zip$/i, "").replace(/-reviewed-\d{8}t\d{6}$/, "");
    const name = `${base}-reviewed-${now.slice(0, 19).replace(/[-:]/g, "").toLowerCase()}.zip`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(makeZip(files));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
    setExported(name);
  }

  const samples = session?.manifest.samples ?? [];
  return (
    <div className="page collect-page">
      <h1>Duyệt bản chép lời giọng nói</h1>
      <Notice tone="warn">
        Công cụ nội bộ. Nghe từng clip và sửa câu cho đúng <strong>điều người nói thực sự nói</strong> (giữ dấu, viết số
        như lời nói: “ba trăm nghìn”). Chỉ xác nhận clip bạn đã tự nghe. Âm thanh chỉ được gửi tới máy chủ khi bạn bấm
        “Gợi ý từ ASR”.
      </Notice>

      <fieldset className="collect-form">
        <legend>Phiên cần duyệt</legend>
        <label>File zip của phiên
          <input type="file" accept=".zip,application/zip" onChange={(e) => void open(e.target.files?.[0])} />
        </label>
        <label>Người duyệt (tên hoặc mã của bạn)
          <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="vd. r-lan" />
        </label>
      </fieldset>

      {error && <div className="notice notice-warn" role="alert">{error}</div>}

      {session && (
        <p className="muted small" role="status">
          {session.name}: {samples.length} clip · người nói {[...new Set(samples.map((s) => s.speaker_id))].join(", ")}
          {" "}· split {[...new Set(samples.map((s) => s.split))].join(", ")}
          {" "}· đã duyệt trước đó {samples.filter((s) => s.transcript_review).length}
        </p>
      )}

      <ol className="prompt-list">
        {samples.map((s) => {
          const e = edits[s.qid];
          if (!e) return null;
          return (
            <li key={s.qid} className={e.confirmed ? "review-done" : ""}>
              <p className="muted small">
                {s.qid}{s.tags?.length ? ` · ${s.tags.join(", ")}` : ""}
                {s.transcript_review && ` · đã duyệt bởi ${s.transcript_review.reviewed_by}`}
              </p>
              {s.reference_text !== null && <p className="prompt-text">Câu gốc: “{s.reference_text}”</p>}
              <div className="prompt-actions">
                <audio controls src={session!.urls[s.qid]} aria-label={`Nghe clip ${s.qid}`} />
                {asrProblem === null && (
                  <button className="btn" onClick={() => void hint(s)} aria-label={`Gợi ý từ ASR cho ${s.qid}`}>
                    Gợi ý từ ASR
                  </button>
                )}
              </div>
              {hints[s.qid] && <p className="small review-hint">ASR (chỉ tham khảo, không tự điền): {hints[s.qid]}</p>}
              <label className="review-text">Bản chép lời
                <textarea rows={2} value={e.text} disabled={e.silent} aria-label={`Bản chép lời ${s.qid}`}
                          onChange={(ev) => patch(s.qid, { text: ev.target.value })} />
              </label>
              <div className="prompt-actions">
                <label className="check">
                  <input type="checkbox" checked={e.silent} onChange={(ev) => patch(s.qid, { silent: ev.target.checked })} />
                  <span>Im lặng / chỉ tiếng ồn</span>
                </label>
                <label className="check">
                  <input type="checkbox" checked={e.confirmed} aria-label={`Đã nghe và xác nhận ${s.qid}`}
                         onChange={(ev) => setEdits((all) => ({ ...all, [s.qid]: { ...e, confirmed: ev.target.checked } }))} />
                  <span>Đã nghe và xác nhận</span>
                </label>
              </div>
            </li>
          );
        })}
      </ol>

      {session && (
        <div className="collect-export">
          <p>Đã xác nhận {confirmed}/{samples.length} clip. Clip chưa xác nhận giữ nguyên trong zip, chưa có transcript_review.</p>
          {problems.map((p) => <p key={p} className="small notice notice-warn">{p}</p>)}
          <button className="btn btn-primary" disabled={!canExport} onClick={exportZip}>Tải zip đã duyệt</button>
          {!reviewer.trim() && <p className="muted small">Nhập người duyệt để tải zip.</p>}
          {exported && (
            <p className="muted small" role="status">
              Đã tạo {exported}. Phiên chưa nhập: dùng import_voice_session.py; đã nhập: dùng apply_voice_review.py.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
