import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Notice } from "../components/common";
import { makeZip, sha256Hex } from "../collect/zip";
import { ACCEPT_ATTR, decodeImage, ImageInputError } from "../media";

// Công cụ nội bộ thu ảnh query độc lập cho benchmark ảnh (benchmarks/image/README.md).
// Ảnh được mã hóa lại JPEG q95 để bỏ EXIF/GPS; source_asset_sha256 giữ hash bytes ảnh gốc.
// judgment và independence_review để null: người duyệt chấm/đối chiếu sau khi nhập.

const ID = /^[a-z0-9][a-z0-9_-]{0,59}$/;
const MAX_SIDE = 2048;

interface Shot {
  qid: string;
  task: "exact" | "similar" | "image_text";
  text: string;
  family: string;
  sourceAssetId: string;
  sourceSha: string;
  jpeg: Blob;
  url: string;
}

function stamp(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}t${p(d.getHours())}${p(d.getMinutes())}`;
}

async function reencode(file: File): Promise<Blob> {
  const bmp = await decodeImage(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * scale);
  canvas.height = Math.round(bmp.height * scale);
  const g = canvas.getContext("2d")!;
  g.fillStyle = "#fff";
  g.fillRect(0, 0, canvas.width, canvas.height);
  g.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  bmp.close();
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.95));
  if (!blob) throw new ImageInputError("Không mã hóa được ảnh.");
  return blob;
}

export function CollectImagePage() {
  const [collector, setCollector] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [split, setSplit] = useState("");
  const [rights, setRights] = useState("");
  const [evidence, setEvidence] = useState("");
  const [family, setFamily] = useState("");
  const [task, setTask] = useState<Shot["task"]>("exact");
  const [text, setText] = useState("");
  const [shots, setShots] = useState<Shot[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [products, setProducts] = useState<{ id: string; name_vi: string }[]>([]);
  const [exported, setExported] = useState<string | null>(null);
  const [stampId] = useState(stamp);
  const counter = useRef(0); // không dùng shots.length: bỏ ảnh rồi thêm sẽ trùng qid

  useEffect(() => {
    // Gợi ý họ sản phẩm từ catalog nếu backend đang chạy; không có cũng nhập tay được.
    api.products({ limit: "100" }).then((r) => setProducts(r.results)).catch(() => setProducts([]));
  }, []);

  const sessionOk = ID.test(collector) && ID.test(sessionId) && !!split && !!rights && evidence.trim().length > 0;
  const shotOk = sessionOk && ID.test(family) && (task !== "image_text" || text.trim().length > 0);

  async function add(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      const original = new Uint8Array(await file.arrayBuffer());
      const sourceSha = await sha256Hex(original);
      if (shots.some((s) => s.sourceSha === sourceSha && s.task === task && s.text === text.trim())) {
        throw new ImageInputError("Ảnh này đã được thêm với cùng tác vụ.");
      }
      const jpeg = await reencode(file);
      const n = String(++counter.current).padStart(3, "0");
      setShots((xs) => [...xs, {
        qid: `${collector}-${stampId}-${n}`, task, text: text.trim(), family,
        // Cùng ảnh gốc dùng lại (ví dụ thêm yêu cầu chữ) thì giữ cùng source_asset_id.
        sourceAssetId: xs.find((s) => s.sourceSha === sourceSha)?.sourceAssetId ?? `${collector}-${stampId}-src${n}`,
        sourceSha, jpeg, url: URL.createObjectURL(jpeg),
      }]);
    } catch (e) {
      setError(e instanceof ImageInputError ? e.message : "Không đọc được ảnh.");
    }
  }

  function remove(qid: string) {
    setShots((xs) => xs.filter((s) => {
      if (s.qid === qid) URL.revokeObjectURL(s.url);
      return s.qid !== qid;
    }));
  }

  async function exportZip() {
    const files: { name: string; data: Uint8Array }[] = [];
    const samples = [];
    for (const s of shots) {
      const data = new Uint8Array(await s.jpeg.arrayBuffer());
      const name = `raw/${s.qid}.jpg`;
      files.push({ name, data });
      samples.push({
        qid: s.qid, task: s.task, text_vi: s.task === "image_text" ? s.text : null, split,
        family_id: s.family, capture_session_id: sessionId, source_asset_id: s.sourceAssetId,
        source_asset_sha256: s.sourceSha, image_path: name, sha256: await sha256Hex(data), source_url: null,
        usage_rights: { status: rights, evidence: evidence.trim() },
        independence_review: null, judgment: null,
      });
    }
    files.unshift({ name: "samples.json", data: new TextEncoder().encode(JSON.stringify({ samples }, null, 1)) });
    const name = `image-${collector}-${stampId}.zip`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(makeZip(files));
    a.download = name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
    setExported(name);
  }

  return (
    <div className="page collect-page">
      <h1>Thu ảnh query cho bộ đánh giá ảnh</h1>
      <Notice tone="warn">
        Công cụ nội bộ. Chụp món đồ thật, không chụp lại ảnh trên website/gallery. Tránh mặt người, biển số và thông
        tin riêng trong khung hình. Ảnh được mã hóa lại để bỏ EXIF/GPS và chỉ rời trình duyệt khi bạn tải file zip.
      </Notice>

      <fieldset className="collect-form">
        <legend>Thông tin phiên</legend>
        <label>Mã người chụp<input value={collector} onChange={(e) => setCollector(e.target.value.trim().toLowerCase())}
                                    placeholder="vd. c03" /></label>
        <label>Mã phiên chụp (nơi/thời điểm)<input value={sessionId}
          onChange={(e) => setSessionId(e.target.value.trim().toLowerCase())} placeholder="vd. c03-cho-ben-thanh-1" /></label>
        <label>Split (do nhóm dữ liệu phân)
          <select value={split} onChange={(e) => setSplit(e.target.value)}>
            <option value="">— chọn —</option>
            <option value="train">train</option><option value="dev">dev</option><option value="test">test</option>
          </select>
        </label>
        <label>Quyền sử dụng ảnh
          <select value={rights} onChange={(e) => setRights(e.target.value)}>
            <option value="">— chọn —</option>
            <option value="owned">Tự chụp (owned)</option>
            <option value="permission_granted">Được cho phép (permission_granted)</option>
            <option value="licensed">Có giấy phép (licensed)</option>
          </select>
        </label>
        <label>Mã bằng chứng quyền<input value={evidence} onChange={(e) => setEvidence(e.target.value)}
                                        placeholder="vd. rights-2026-10-c03" /></label>
      </fieldset>

      <fieldset className="collect-form" disabled={!sessionOk}>
        <legend>Ảnh tiếp theo</legend>
        <label>Họ sản phẩm (family_id)
          <input list="families" value={family} onChange={(e) => setFamily(e.target.value.trim().toLowerCase())}
                 placeholder="mã sản phẩm catalog hoặc mã họ ngoài catalog" />
          <datalist id="families">
            {products.map((p) => <option key={p.id} value={p.id}>{p.name_vi}</option>)}
          </datalist>
        </label>
        <label>Tác vụ
          <select value={task} onChange={(e) => setTask(e.target.value as Shot["task"])}>
            <option value="exact">exact — đúng món có trong catalog</option>
            <option value="similar">similar — món tương tự / ngoài catalog</option>
            <option value="image_text">image_text — ảnh + yêu cầu chữ</option>
          </select>
        </label>
        {task === "image_text" && (
          <label>Yêu cầu bằng chữ<input value={text} maxLength={300} onChange={(e) => setText(e.target.value)}
                                         placeholder="vd. giống mẫu này nhưng có quai, dưới 400k" /></label>
        )}
        <div className="image-pick">
          <label className={`btn ${shotOk ? "" : "btn-disabled"}`}>
            📷 Chụp / chọn ảnh
            <input type="file" accept={ACCEPT_ATTR} capture="environment" hidden disabled={!shotOk}
                   onChange={(e) => { void add(e.target.files?.[0]); e.target.value = ""; }} />
          </label>
        </div>
      </fieldset>

      {error && <div className="notice notice-warn" role="alert">{error}</div>}

      <ol className="prompt-list">
        {shots.map((s) => (
          <li key={s.qid} className="shot">
            <img src={s.url} alt={`Ảnh ${s.qid}`} />
            <div>
              <p className="small"><b>{s.qid}</b> · {s.task} · {s.family}{s.text && <> · “{s.text}”</>}</p>
              <button className="link" onClick={() => remove(s.qid)}>Bỏ ảnh {s.qid}</button>
            </div>
          </li>
        ))}
      </ol>

      <div className="collect-export">
        <p>Đã thêm {shots.length} ảnh.</p>
        <button className="btn btn-primary" disabled={!sessionOk || !shots.length} onClick={() => void exportZip()}>
          Tải file zip của phiên
        </button>
        {exported && (
          <p className="muted small" role="status">
            Đã tạo {exported}. Gửi cho nhóm dữ liệu để nhập bằng scripts/benchmark/import_image_session.py.
          </p>
        )}
      </div>
    </div>
  );
}
