import { useEffect, useRef, useState } from "react";
import { api, ApiError, emptyFilters, type Filters, hasFilters, modalityProblem, type SearchResponse } from "../api";
import { ArtSection } from "../components/brand/Art";
import { BambooLines, LotusMark, WeaveDivider } from "../components/brand/Motifs";
import { EmptyState, ErrorBox, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { SearchBar } from "../components/SearchBar";
import { Icon } from "../components/ui/Icon";
import { ACCEPT_ATTR, type Crop, decodeImage, ImageInputError, prepareImage } from "../media";
import { FilterPanel } from "./SearchPage";
import { afterResultPaint, beginMeasure, endMeasure, type Measure } from "../measurements";

const MIN_CROP = 0.05;

export function ImageSearchPage() {
  const [problem, setProblem] = useState<string | null>(null);
  const [bmp, setBmp] = useState<ImageBitmap | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [crop, setCrop] = useState<Crop | null>(null);
  const [text, setText] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  // Bộ lọc người dùng chọn sau khi có kết quả; đổi bộ lọc thì gửi lại đúng ảnh đã chuẩn bị (không cắt/mã hóa lại).
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const lastBlob = useRef<Blob | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(() => window.innerWidth > 800);
  const generation = useRef(0);
  const request = useRef<AbortController | null>(null);
  const [measure, setMeasure] = useState<Measure>();

  function invalidate() {
    generation.current++;
    request.current?.abort();
    setLoading(false);
    setData(null);
    setError(null);
    lastBlob.current = null;
  }
  useEffect(() => () => { generation.current++; request.current?.abort(); }, []);
  useEffect(() => {
    if (data && !loading && !error) return afterResultPaint(measure, data);
  }, [data, loading, error, measure]);

  useEffect(() => {
    let alive = true;
    modalityProblem("image").then((p) => alive && setProblem(p));
    return () => {
      alive = false;
    };
  }, []);

  // Ảnh chỉ nằm trong bộ nhớ trang; giải phóng khi đổi ảnh hoặc rời trang.
  useEffect(() => () => preview ? URL.revokeObjectURL(preview) : undefined, [preview]);
  useEffect(() => () => bmp?.close(), [bmp]);

  async function pick(file: File | undefined) {
    if (!file) return;
    invalidate();
    const id = generation.current;
    setBmp(null);
    setPreview(null);
    setInputError(null);
    setData(null);
    setError(null);
    setCrop(null);
    setFilters(emptyFilters());
    lastBlob.current = null;
    try {
      const decoded = await decodeImage(file);
      if (id !== generation.current) { decoded.close(); return; }
      setBmp(decoded);
      setPreview(URL.createObjectURL(file));
    } catch (e) {
      if (id !== generation.current) return;
      setBmp(null);
      setPreview(null);
      setInputError(e instanceof ImageInputError ? e.message : "Không đọc được ảnh.");
    }
  }

  async function search(prepare: () => Promise<Blob>, f: Filters, reuse = false) {
    const id = ++generation.current;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const timing = beginMeasure("image");
    setLoading(true);
    setError(null);
    setInputError(null);
    const superseded = () => {
      if (id === generation.current) return false;
      endMeasure(timing, "cancelled");
      return true;
    };
    try {
      const blob = await prepare();
      if (superseded()) return;
      lastBlob.current = blob;
      const response = await api.searchImage(blob, text.trim(), f, controller.signal, reuse);
      if (superseded()) return;
      setData(response);
      setMeasure(timing);
    } catch (err) {
      if (superseded()) return;
      endMeasure(timing, "error");
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      if (id === generation.current) setLoading(false);
    }
  }

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    if (!bmp) return;
    await search(() => prepareImage(bmp, crop), filters);
  }

  function update(mut: (f: Filters) => void) {
    const next = structuredClone(filters);
    mut(next);
    setFilters(next);
    const prepared = lastBlob.current;
    if (prepared) void search(() => Promise.resolve(prepared), next, true);
  }

  function toggle(key: keyof Filters, value: string) {
    update((f) => {
      const arr = f[key] as string[];
      (f[key] as string[]) = arr.includes(value) ? arr.filter((x) => x !== value) : [...arr, value];
    });
  }

  return (
    <div className="page image-page">
      <ArtSection className="task-masthead" art={<BambooLines className="masthead-bamboo masthead-bamboo-left" />}>
        <div className="container">
          <SearchBar />
          <h1 className="task-title">Tìm bằng ảnh<span className="editorial-mark" aria-hidden="true" /></h1>
          <p className="task-lede">
            Chụp hoặc chọn ảnh món đồ, khoanh vùng có vật cần tìm rồi thêm yêu cầu nếu muốn. Kết quả là các mẫu tương
            tự trong catalog — không phải xác nhận đúng sản phẩm hay nguồn gốc.
          </p>
        </div>
      </ArtSection>

      <div className="container">
        {problem && <Notice tone="warn">{problem}{" "}
          <button className="link" onClick={() => void modalityProblem("image", true).then(setProblem)}>Kiểm tra lại</button>
        </Notice>}

        <div className="image-workspace">
          <div className="image-input">
            <div
              className={`image-drop ${preview ? "has-image" : ""}`}
              onDragOver={(e) => { e.preventDefault(); }}
              onDrop={(e) => { e.preventDefault(); void pick(e.dataTransfer.files?.[0]); }}
            >
              <div className="image-pick">
                <label className="btn btn-primary file-btn">
                  <Icon name="camera" /> Chụp ảnh
                  <input type="file" accept={ACCEPT_ATTR} capture="environment" className="file-input"
                         onChange={(e) => void pick(e.target.files?.[0])} />
                </label>
                <label className="btn file-btn">
                  <Icon name="image" /> Chọn ảnh từ máy
                  <input type="file" accept={ACCEPT_ATTR} className="file-input" onChange={(e) => void pick(e.target.files?.[0])} />
                </label>
              </div>
              {!preview && <p className="muted small drop-hint">Hoặc kéo thả ảnh vào đây. JPEG, PNG hoặc WebP.</p>}
            </div>
            {inputError && (
              <div className="notice notice-warn" role="alert">
                <Icon name="alert" size={18} className="notice-icon" /><div>{inputError}</div>
              </div>
            )}

            {preview && (
              <>
                <CropBox key={preview} src={preview} crop={crop} onChange={(c) => { invalidate(); setCrop(c); }} />
                <p className="crop-status muted small" aria-live="polite">
                  {crop ? (
                    <>
                      Đã chọn vùng.{" "}
                      <button className="link" onClick={() => { invalidate(); setCrop(null); }}>
                        Bỏ vùng chọn (dùng cả ảnh)
                      </button>
                    </>
                  ) : (
                    "Đang dùng cả ảnh. Kéo trên ảnh để chọn vùng, hoặc đưa focus vào ảnh và dùng phím mũi tên."
                  )}
                </p>
                <form className="image-query" onSubmit={run}>
                  <label className="field-label" htmlFor="image-extra">Yêu cầu thêm (không bắt buộc)</label>
                  <div className="image-query-row">
                    <input
                      id="image-extra"
                      type="text"
                      className="text-input"
                      value={text}
                      maxLength={300}
                      aria-label="Yêu cầu thêm"
                      placeholder="Ví dụ: có quai, dưới 400k…"
                      onChange={(e) => { invalidate(); setText(e.target.value); }}
                    />
                    <button className="btn btn-primary" disabled={loading || !!problem}>
                      Tìm mẫu tương tự
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>

          <aside className="image-guide" aria-label="Hướng dẫn">
            <ol className="guide-steps">
              <li><b>Chọn hoặc chụp ảnh</b> món đồ, đủ sáng và rõ hình.</li>
              <li><b>Khoanh vùng</b> quanh vật cần tìm nếu ảnh có nhiều thứ.</li>
              <li><b>Thêm yêu cầu</b> như chất liệu, có quai, khoảng giá.</li>
              <li><b>Xem mẫu tương tự</b> và lọc thêm theo danh mục, chất liệu.</li>
            </ol>
            <p className="small muted guide-privacy">
              <Icon name="info" size={16} /> Ảnh được thu nhỏ và bỏ thông tin vị trí trước khi gửi; máy chủ không lưu ảnh.
            </p>
          </aside>
        </div>

        <WeaveDivider className="section-weave" />

        <div className={data ? "search-layout" : undefined}>
          {data && (
            <aside className="search-aside">
              <details className="filters" open={filtersOpen}
                       onToggle={(e) => setFiltersOpen((e.currentTarget as HTMLDetailsElement).open)}>
                <summary><Icon name="filter" /> Bộ lọc<span className="editorial-mark" aria-hidden="true" /></summary>
                <FilterPanel key={JSON.stringify(filters)} data={data} filters={filters} toggle={toggle} update={update} />
              </details>
            </aside>
          )}
          <section className="results" aria-label="Mẫu tương tự" aria-busy={loading}>
            {loading && (
              <div className="state state-loading">
                <p role="status"><span className="spinner" aria-hidden /> Đang tìm mẫu tương tự…</p>
                <button className="btn" onClick={invalidate}>Hủy tìm ảnh</button>
              </div>
            )}
            {error && <ErrorBox message={error} onRetry={() => void run()} />}
            {data && !loading && !error && (
              <ImageResults data={data} onClear={hasFilters(filters) ? () => update((f) => Object.assign(f, emptyFilters()))
                                                                     : undefined} />
            )}
            {!data && !loading && !error && (
              <div className="image-empty">
                <LotusMark size={40} />
                <p className="muted small">Kết quả sẽ hiện ở đây sau khi bạn chọn ảnh và bấm “Tìm mẫu tương tự”.</p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function ImageResults({ data, onClear }: { data: SearchResponse; onClear?: () => void }) {
  return (
    <>
      <section className="interpret" aria-label="Cách hệ thống hiểu truy vấn">
        <div className="chips">
          <span className="chip chip-static">Theo ảnh</span>
          {data.interpreted_query.keywords && (
            <span className="chip chip-static">
              Từ khóa: <b>{data.interpreted_query.keywords}</b>
            </span>
          )}
          {data.applied_filters.map((a) => (
            <span key={a.key} className="chip chip-hard">
              {a.label}
            </span>
          ))}
          {onClear && (
            <button className="chip chip-clear" onClick={onClear}>
              Xóa bộ lọc
            </button>
          )}
        </div>
        {data.warnings.map((w) => (
          <Notice key={w} tone="warn">
            {w}
          </Notice>
        ))}
      </section>
      <div className="results-head">
        <h2 className="section-title">Mẫu tương tự</h2>
        <p className="results-count" role="status">{data.total} kết quả</p>
      </div>
      {data.total === 0 ? (
        <EmptyState title="Không có mẫu tương tự thỏa yêu cầu.">
          {data.relaxations.length > 0 && (
            <ul className="relax">
              {data.relaxations.map((r) => (
                <li key={r.key}>
                  “{r.label}” đang hạn chế kết quả (bỏ đi → {r.count} kết quả)
                </li>
              ))}
            </ul>
          )}
        </EmptyState>
      ) : (
        <ProductGrid items={data.results} />
      )}
    </>
  );
}

const KEY_STEP = 0.02;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** Kéo để chọn vùng chữ nhật trên ảnh xem trước; toạ độ lưu theo tỉ lệ 0..1. Bàn phím: mũi tên dịch vùng,
 *  Shift + mũi tên đổi kích thước. Vùng bám con trỏ trực tiếp, không easing. */
function CropBox({ src, crop, onChange }: { src: string; crop: Crop | null; onChange: (c: Crop | null) => void }) {
  const img = useRef<HTMLImageElement>(null);
  const start = useRef<{ x: number; y: number } | null>(null);
  const [draft, setDraft] = useState<Crop | null>(null);

  function point(e: React.PointerEvent) {
    const r = img.current!.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
      y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
    };
  }
  function rect(a: { x: number; y: number }, b: { x: number; y: number }): Crop {
    return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) };
  }

  function onKeyDown(e: React.KeyboardEvent) {
    const dirs: Record<string, [number, number]> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    const d = dirs[e.key];
    if (!d) return;
    e.preventDefault();
    const c = crop ?? { x: 0.2, y: 0.2, w: 0.6, h: 0.6 };
    if (!crop) return onChange(c);
    if (e.shiftKey) {
      const w = Math.max(MIN_CROP, Math.min(1 - c.x, c.w + d[0] * KEY_STEP));
      const h = Math.max(MIN_CROP, Math.min(1 - c.y, c.h + d[1] * KEY_STEP));
      onChange({ ...c, w, h });
    } else {
      onChange({ ...c, x: clamp01(Math.min(1 - c.w, c.x + d[0] * KEY_STEP)), y: clamp01(Math.min(1 - c.h, c.y + d[1] * KEY_STEP)) });
    }
  }

  const shown = draft ?? crop;
  const pct = (v: number) => Math.round(v * 100);
  return (
    <div
      className="crop-box"
      data-testid="crop-box"
      tabIndex={0}
      role="group"
      aria-label="Vùng chọn trên ảnh. Phím mũi tên để tạo hoặc dịch vùng, Shift cùng mũi tên để đổi kích thước."
      aria-describedby="crop-readout"
      onKeyDown={onKeyDown}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = point(e);
        setDraft(null);
      }}
      onPointerMove={(e) => start.current && setDraft(rect(start.current, point(e)))}
      onPointerUp={(e) => {
        if (!start.current) return;
        const c = rect(start.current, point(e));
        start.current = null;
        setDraft(null);
        // Chạm/nhấp nhẹ không đổi vùng đang chọn.
        if (c.w >= MIN_CROP && c.h >= MIN_CROP) onChange(c);
      }}
      onPointerCancel={() => {
        start.current = null;
        setDraft(null);
      }}
    >
      <img ref={img} src={src} alt="Ảnh bạn chọn để tìm" draggable={false} />
      {shown && (
        <div
          className="crop-rect"
          aria-hidden
          style={{ left: `${shown.x * 100}%`, top: `${shown.y * 100}%`,
                   width: `${shown.w * 100}%`, height: `${shown.h * 100}%` }}
        >
          <i /><i /><i /><i />
        </div>
      )}
      <span id="crop-readout" className="sr-only">
        {crop ? `Vùng chọn: từ ${pct(crop.x)}% ngang, ${pct(crop.y)}% dọc; rộng ${pct(crop.w)}%, cao ${pct(crop.h)}%.` : "Chưa chọn vùng."}
      </span>
    </div>
  );
}
