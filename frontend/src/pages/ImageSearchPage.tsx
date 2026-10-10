import { useEffect, useRef, useState } from "react";
import { api, ApiError, emptyFilters, type Filters, hasFilters, modalityProblem, type SearchResponse } from "../api";
import { ErrorBox, Loading, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { SearchBar } from "../components/SearchBar";
import { ACCEPT_ATTR, type Crop, decodeImage, ImageInputError, prepareImage } from "../media";
import { FilterPanel } from "./SearchPage";

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
    setInputError(null);
    setData(null);
    setError(null);
    setCrop(null);
    setFilters(emptyFilters());
    lastBlob.current = null;
    try {
      const decoded = await decodeImage(file);
      setBmp(decoded);
      setPreview(URL.createObjectURL(file));
    } catch (e) {
      setBmp(null);
      setPreview(null);
      setInputError(e instanceof ImageInputError ? e.message : "Không đọc được ảnh.");
    }
  }

  async function search(blob: Blob, f: Filters) {
    setLoading(true);
    setError(null);
    setInputError(null);
    try {
      setData(await api.searchImage(blob, text.trim(), f));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    if (!bmp) return;
    try {
      lastBlob.current = await prepareImage(bmp, crop);
    } catch (err) {
      if (err instanceof ImageInputError) setInputError(err.message);
      else setError(String(err));
      return;
    }
    await search(lastBlob.current, filters);
  }

  function update(mut: (f: Filters) => void) {
    const next = structuredClone(filters);
    mut(next);
    setFilters(next);
    if (lastBlob.current) void search(lastBlob.current, next);
  }

  function toggle(key: keyof Filters, value: string) {
    update((f) => {
      const arr = f[key] as string[];
      (f[key] as string[]) = arr.includes(value) ? arr.filter((x) => x !== value) : [...arr, value];
    });
  }

  return (
    <div className="page image-page">
      <SearchBar />
      <h1>Tìm bằng ảnh</h1>
      <p className="muted small">
        Chụp hoặc chọn ảnh món đồ, kéo trên ảnh để chọn vùng có vật cần tìm. Ảnh được thu nhỏ và bỏ thông tin vị trí
        trước khi gửi; máy chủ không lưu ảnh.
      </p>
      {problem && <Notice tone="warn">{problem}</Notice>}

      <div className="image-pick">
        <label className="btn">
          📷 Chụp ảnh
          <input type="file" accept={ACCEPT_ATTR} capture="environment" hidden
                 onChange={(e) => void pick(e.target.files?.[0])} />
        </label>
        <label className="btn">
          🖼 Chọn ảnh từ máy
          <input type="file" accept={ACCEPT_ATTR} hidden onChange={(e) => void pick(e.target.files?.[0])} />
        </label>
      </div>
      {inputError && (
        <div className="notice notice-warn" role="alert">
          {inputError}
        </div>
      )}

      {preview && (
        <>
          <CropBox src={preview} crop={crop} onChange={setCrop} />
          <p className="muted small" aria-live="polite">
            {crop ? (
              <>
                Đã chọn vùng.{" "}
                <button className="link" onClick={() => setCrop(null)}>
                  Bỏ vùng chọn (dùng cả ảnh)
                </button>
              </>
            ) : (
              "Đang dùng cả ảnh. Kéo trên ảnh để chọn vùng."
            )}
          </p>
          <form className="searchbar-form" onSubmit={run}>
            <input
              type="text"
              className="text-input"
              value={text}
              maxLength={300}
              aria-label="Yêu cầu thêm"
              placeholder="Thêm yêu cầu: có quai, dưới 400k…"
              onChange={(e) => setText(e.target.value)}
            />
            <button className="btn btn-primary" disabled={loading || !!problem}>
              Tìm mẫu tương tự
            </button>
          </form>
        </>
      )}

      <div className={data ? "search-layout" : undefined}>
        {data && (
          <details className="filters" open={filtersOpen}
                   onToggle={(e) => setFiltersOpen((e.currentTarget as HTMLDetailsElement).open)}>
            <summary>Bộ lọc</summary>
            <FilterPanel key={JSON.stringify(filters)} data={data} filters={filters} toggle={toggle} update={update} />
          </details>
        )}
        <section className="results" aria-live="polite">
          {loading && <Loading label="Đang tìm mẫu tương tự…" />}
          {error && <ErrorBox message={error} onRetry={() => void run()} />}
          {data && !loading && !error && (
            <ImageResults data={data} onClear={hasFilters(filters) ? () => update((f) => Object.assign(f, emptyFilters()))
                                                                   : undefined} />
          )}
        </section>
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
      <h2 className="section-title">Mẫu tương tự</h2>
      <p className="muted small">
        {data.total} kết quả · {data.timings_ms.total} ms
      </p>
      {data.total === 0 ? (
        <div className="state">
          <p>Không có mẫu tương tự thỏa yêu cầu.</p>
          {data.relaxations.length > 0 && (
            <ul className="relax">
              {data.relaxations.map((r) => (
                <li key={r.key}>
                  “{r.label}” đang hạn chế kết quả (bỏ đi → {r.count} kết quả)
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <ProductGrid items={data.results} />
      )}
    </>
  );
}

/** Kéo để chọn vùng chữ nhật trên ảnh xem trước; toạ độ lưu theo tỉ lệ 0..1. */
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

  const shown = draft ?? crop;
  return (
    <div
      className="crop-box"
      data-testid="crop-box"
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
        />
      )}
    </div>
  );
}
