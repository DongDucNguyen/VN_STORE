import { useEffect, useState } from "react";
import { api, ApiError, emptyFilters, hasFilters, type Filters, type SearchResponse } from "../api";
import { voiceResult } from "../voiceResult";
import { afterResultPaint, beginMeasure, endMeasure, type Measure } from "../measurements";
import { ArtSection, MarginArtwork } from "../components/brand/Art";
import { BambooLines, NonLaLines } from "../components/brand/Motifs";
import { EmptyState, ErrorBox, GridSkeleton, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { SearchBar } from "../components/SearchBar";
import { Icon } from "../components/ui/Icon";
import { ART } from "../content/editorialAssets";
import { formatVnd } from "../format";
import { navigate, type Route } from "../router";

const PAGE = 24;

// Tham số URL ↔ bộ lọc người dùng chọn.
const PARAM: Record<string, keyof Filters> = {
  cat: "category_ids", brand: "brand_ids", place: "place_ids", mat: "materials", color: "colors", claim: "claim_types",
};
const HINT_PARAM: Record<string, { param: string; key: "id" | "value" }> = {
  category: { param: "cat", key: "id" },
  place: { param: "place", key: "id" },
  brand: { param: "brand", key: "id" },
  material: { param: "mat", key: "value" },
  color: { param: "color", key: "value" },
};

// Gỡ bộ lọc người dùng theo key ràng buộc backend trả về trong relaxations.
const RELAX_CLEAR: Record<string, (f: Filters) => void> = {
  category: (f) => (f.category_ids = []),
  brand: (f) => (f.brand_ids = []),
  place: (f) => (f.place_ids = []),
  materials: (f) => (f.materials = []),
  colors: (f) => (f.colors = []),
  claim_types: (f) => (f.claim_types = []),
  price_user: (f) => {
    f.price_min = null;
    f.price_max = null;
  },
};

function filtersFrom(params: URLSearchParams): Filters {
  const f = emptyFilters();
  for (const [p, key] of Object.entries(PARAM)) (f[key] as string[]) = params.getAll(p);
  const num = (v: string | null) => (v && /^\d+$/.test(v) ? Number(v) : null);
  f.price_min = num(params.get("pmin"));
  f.price_max = num(params.get("pmax"));
  return f;
}

function toParams(q: string, f: Filters): Record<string, string | string[] | null> {
  const out: Record<string, string | string[] | null> = { q: q || null };
  for (const [p, key] of Object.entries(PARAM)) out[p] = f[key] as string[];
  out.pmin = f.price_min != null ? String(f.price_min) : null;
  out.pmax = f.price_max != null ? String(f.price_max) : null;
  return out;
}

export function SearchPage({ route }: { route: Route }) {
  const q = route.params.get("q") ?? "";
  const filters = filtersFrom(route.params);
  const key = route.params.toString();
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(PAGE);
  const [retry, setRetry] = useState(0);
  const [measure, setMeasure] = useState<Measure>();
  // Màn hình rộng mở sẵn bộ lọc; giữ nguyên lựa chọn đóng/mở của người dùng khi đổi bộ lọc.
  const [filtersOpen, setFiltersOpen] = useState(() => window.innerWidth > 800);

  useEffect(() => setLimit(PAGE), [key]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    const voice = route.params.get("via") === "voice" && !hasFilters(filters) && limit === PAGE && retry === 0
      ? voiceResult(route.params.get("voice_id"), q) : null;
    if (voice) {
      setMeasure(voice.measure);
      setData(voice.response);
      setLoading(false);
      return;
    }
    const timing = beginMeasure("keyword");
    // Hủy yêu cầu cũ khi đổi truy vấn/bộ lọc để máy chủ không xử lý tiếp. Không ghi "cancelled" vào số đo:
    // StrictMode chạy effect hai lần ở môi trường dev sẽ tạo lượt hủy giả.
    const controller = new AbortController();
    api
      .search(q, filters, limit, 0, controller.signal)
      .then((r) => { if (alive) { setData(r); setMeasure(timing); } })
      .catch((e) => {
        if (!alive) return;
        endMeasure(timing, "error");
        setError(e instanceof ApiError ? e.message : String(e));
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, limit, retry]);

  useEffect(() => {
    if (data && !loading && !error) return afterResultPaint(measure, data);
  }, [data, loading, error, measure]);

  function update(mut: (f: Filters) => void) {
    const f = filtersFrom(route.params);
    mut(f);
    navigate("/search", toParams(q, f));
  }

  function toggle(key: keyof Filters, value: string) {
    update((f) => {
      const arr = f[key] as string[];
      (f[key] as string[]) = arr.includes(value) ? arr.filter((x) => x !== value) : [...arr, value];
    });
  }

  const iq = data?.interpreted_query;
  const userFilters = data?.applied_filters.filter((a) => a.source === "user") ?? [];
  const queryFilters = data?.applied_filters.filter((a) => a.source === "query") ?? [];

  return (
    <div className="page search-page">
      <ArtSection className="task-masthead" art={<BambooLines className="masthead-bamboo" />}>
        <div className="container">
          <h1 className="task-title">Tìm một món hợp ý<span className="editorial-mark" aria-hidden="true" /></h1>
          <SearchBar initial={q} />
          {route.params.get("via") === "voice" && q && (
            <Notice>
              Đã chép lời từ giọng nói: “{q}”. Bạn có thể sửa câu vừa nói trong ô tìm rồi bấm Tìm, hoặc bấm nút micro
              để nói lại.
              {data?.transcript?.raw_text && <div>Bản chép lời gốc: “{data.transcript.raw_text}”</div>}
            </Notice>
          )}
        </div>
      </ArtSection>

      <ArtSection className="search-body" art={<MarginArtwork asset={ART.lotusBotanical02} className="search-lotus" />}>
        <div className="container">
          {data && iq && (q || userFilters.length > 0) && (
            <section className="interpret" aria-label="Cách hệ thống hiểu truy vấn">
              <h2 className="sr-only">Cách hiểu truy vấn</h2>
              <p className="interpret-lead">
                Bạn đang tìm{q ? <> “<b>{q}</b>”</> : " theo bộ lọc"}
              </p>
              <div className="chips">
                {iq.keywords && (
                  <span className="chip chip-static">
                    Từ khóa: <b>{iq.keywords}</b>
                  </span>
                )}
                {queryFilters.map((a) => (
                  <span key={a.key} className="chip chip-hard chip-query" title="Ràng buộc bạn nêu trong câu tìm">
                    {a.label}
                  </span>
                ))}
                {userFilters.map((a) => (
                  <span key={a.key} className="chip chip-hard chip-user" title="Bộ lọc bạn chọn">
                    {a.label}
                  </span>
                ))}
                {userFilters.length > 0 && (
                  <button className="chip chip-clear" onClick={() => navigate("/search", { q })}>
                    Xóa bộ lọc
                  </button>
                )}
              </div>
              {data.suggested_filters.length > 0 && (
                <div className="chips">
                  <span className="chips-label">Có phải bạn muốn lọc:</span>
                  {data.suggested_filters.map((h) => {
                    const m = HINT_PARAM[h.field];
                    const v = m && (m.key === "id" ? h.id : h.value);
                    if (!m || !v) return null;
                    const already = route.params.getAll(m.param).includes(v);
                    return (
                      <button
                        key={`${h.field}:${v}`}
                        className={`chip chip-suggest ${already ? "chip-on" : ""}`}
                        aria-pressed={already}
                        onClick={() => toggle(PARAM[m.param], v)}
                      >
                        {already ? "✓ " : "+ "}
                        {h.value}
                      </button>
                    );
                  })}
                </div>
              )}
              {/* Sửa lỗi gõ đã có cảnh báo riêng "Hiểu … là …". */}
              {iq.expansions.some((e) => e.relation !== "typo") && (
                <p className="muted small">
                  Tìm thêm cách gọi khác:{" "}
                  {iq.expansions.filter((e) => e.relation !== "typo").map((e) => e.term).join(", ")}
                </p>
              )}
              {data.warnings.map((w) => (
                <Notice key={w} tone="warn">
                  {w}
                </Notice>
              ))}
            </section>
          )}

          <div className="search-layout">
            <aside className="search-aside">
              <details
                className="filters"
                open={filtersOpen}
                onToggle={(e) => setFiltersOpen((e.currentTarget as HTMLDetailsElement).open)}
              >
                <summary><Icon name="filter" /> Bộ lọc<span className="editorial-mark" aria-hidden="true" /></summary>
                {data && <FilterPanel key={key} data={data} filters={filters} toggle={toggle} update={update} />}
              </details>
              <NonLaLines className="aside-ribs" />
            </aside>

            <section className="results" aria-label="Kết quả tìm kiếm" aria-busy={loading}>
              {loading && !data && <GridSkeleton count={6} label="Đang tìm…" />}
              {error && <ErrorBox message={error} onRetry={() => setRetry((r) => r + 1)} />}
              {data && !error && (
                <>
                  <div className="results-head">
                    <p className="results-count" role="status">
                      {data.total} kết quả{q && <> cho “{q}”</>}
                    </p>
                    {loading && (
                      <p className="results-updating" role="status">
                        <span className="spinner" aria-hidden /> Đang cập nhật kết quả…
                      </p>
                    )}
                  </div>
                  {data.total === 0 ? (
                    <EmptyState title="Không tìm thấy sản phẩm phù hợp.">
                      <p>Mình chưa tìm thấy món phù hợp với các điều kiện này.</p>
                      {data.relaxations.length > 0 && (
                        <>
                          <p>Điều kiện đang hạn chế kết quả:</p>
                          <ul className="relax">
                            {data.relaxations.map((r) => {
                              const clear = RELAX_CLEAR[r.key];
                              return (
                                <li key={r.key}>
                                  {clear ? (
                                    <button className="link" onClick={() => update(clear)}>
                                      Bỏ “{r.label}”
                                    </button>
                                  ) : (
                                    <>“{r.label}” (sửa câu tìm để nới)</>
                                  )}{" "}
                                  → {r.count} kết quả
                                </li>
                              );
                            })}
                          </ul>
                        </>
                      )}
                      {q && (
                        <a className="btn" href={`#/search?q=${encodeURIComponent(q)}`}>
                          Tìm lại không kèm bộ lọc
                        </a>
                      )}
                    </EmptyState>
                  ) : (
                    <>
                      <ProductGrid items={data.results} busy={loading} />
                      {data.results.length < data.total && (
                        <p className="load-more">
                          <button className="btn" disabled={loading} onClick={() => setLimit((l) => l + PAGE)}>
                            {loading ? "Đang tải…" : "Xem thêm"} <Icon name="chevron" size={18} />
                          </button>
                        </p>
                      )}
                    </>
                  )}
                </>
              )}
            </section>
          </div>
        </div>
      </ArtSection>

      <MaterialBand />
    </div>
  );
}

/** Dải chất liệu cuối trang tìm kiếm: ảnh nan đan cận cảnh + lối sang làng nghề. */
export function MaterialBand() {
  return (
    <section className="material-band" aria-labelledby="material-band-title">
      <div className="material-band-art" aria-hidden="true">
        <img src={ART.weaveStrip.src} width={ART.weaveStrip.width} height={ART.weaveStrip.height} alt="" loading="lazy"
          decoding="async" />
      </div>
      <div className="material-band-copy">
        <h2 id="material-band-title">Từ những sợi mộc<span className="editorial-mark" aria-hidden="true" /></h2>
        <p>Mỗi sợi đan là một câu chuyện về bàn tay, thời gian và nếp sống. Xem sản phẩm theo nơi làm ra chúng.</p>
        <a className="text-link" href="#/places">Khám phá làng nghề <Icon name="arrow" size={18} /></a>
      </div>
    </section>
  );
}

export function FilterPanel({
  data,
  filters,
  toggle,
  update,
}: {
  data: SearchResponse;
  filters: Filters;
  toggle: (k: keyof Filters, v: string) => void;
  update: (mut: (f: Filters) => void) => void;
}) {
  const f = data.facets;
  const [pmin, setPmin] = useState(filters.price_min?.toString() ?? "");
  const [pmax, setPmax] = useState(filters.price_max?.toString() ?? "");
  const [priceError, setPriceError] = useState<string | null>(null);

  // Giữ các giá trị đang chọn hiển thị dù tập kết quả hiện tại không còn chúng.
  const withSelected = <T extends { count: number }>(items: T[], selected: string[], idOf: (x: T) => string,
                                                     make: (v: string) => T) => {
    const have = new Set(items.map(idOf));
    return [...items, ...selected.filter((s) => !have.has(s)).map(make)];
  };

  const groups: { title: string; key: keyof Filters; items: { id: string; label: string; count: number }[] }[] = [
    {
      title: "Danh mục",
      key: "category_ids",
      items: withSelected(f.categories, filters.category_ids, (x) => x.id, (v) => ({ id: v, name: v, count: 0 })).map(
        (x) => ({ id: x.id, label: x.name, count: x.count })),
    },
    {
      title: "Chất liệu",
      key: "materials",
      items: withSelected(f.materials, filters.materials, (x) => x.value, (v) => ({ value: v, count: 0 })).map(
        (x) => ({ id: x.value, label: x.value, count: x.count })),
    },
    {
      title: "Màu",
      key: "colors",
      items: withSelected(f.colors, filters.colors, (x) => x.value, (v) => ({ value: v, count: 0 })).map(
        (x) => ({ id: x.value, label: x.value, count: x.count })),
    },
    {
      title: "Thương hiệu",
      key: "brand_ids",
      items: withSelected(f.brands, filters.brand_ids, (x) => x.id, (v) => ({ id: v, name: v, count: 0 })).map(
        (x) => ({ id: x.id, label: x.name, count: x.count })),
    },
    {
      title: "Làng nghề / nơi sản xuất",
      key: "place_ids",
      items: withSelected(f.craft_villages, filters.place_ids, (x) => x.id, (v) => ({ id: v, name: v, count: 0 })).map(
        (x) => ({ id: x.id, label: x.name, count: x.count })),
    },
    {
      title: "Căn cứ nguồn gốc",
      key: "claim_types",
      items: withSelected(f.claim_types, filters.claim_types, (x) => x.id, (v) => ({ id: v, name: v, count: 0 })).map(
        (x) => ({ id: x.id, label: x.name, count: x.count })),
    },
  ];

  return (
    <div className="filter-panel">
      <fieldset>
        <legend>Khoảng giá (đ)</legend>
        <form
          className="price-form"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            const lo = /^\d+$/.test(pmin) ? Number(pmin) : null;
            const hi = /^\d+$/.test(pmax) ? Number(pmax) : null;
            if ((pmin && lo == null) || (pmax && hi == null)) {
              setPriceError("Giá chỉ gồm chữ số, ví dụ 300000.");
              return;
            }
            if (lo != null && hi != null && lo > hi) {
              setPriceError("Giá “Từ” đang lớn hơn giá “Đến”.");
              return;
            }
            setPriceError(null);
            update((x) => {
              x.price_min = lo;
              x.price_max = hi;
            });
          }}
        >
          <label className="price-field">
            <span>Từ</span>
            <input inputMode="numeric" placeholder="Từ" value={pmin} aria-invalid={!!priceError}
              onChange={(e) => setPmin(e.target.value.trim())} />
          </label>
          <label className="price-field">
            <span>Đến</span>
            <input inputMode="numeric" placeholder="Đến" value={pmax} aria-invalid={!!priceError}
              onChange={(e) => setPmax(e.target.value.trim())} />
          </label>
          <button className="btn btn-small">Áp dụng</button>
        </form>
        {priceError && <p className="field-error" role="alert">{priceError}</p>}
        {f.price.min_vnd != null && (
          <p className="muted small">
            Trong kết quả: {formatVnd(f.price.min_vnd)} – {formatVnd(f.price.max_vnd ?? f.price.min_vnd)}
            {f.price.unknown > 0 && ` · ${f.price.unknown} chưa có giá`}
          </p>
        )}
      </fieldset>
      {groups
        .filter((g) => g.items.length > 0)
        .map((g) => (
          <fieldset key={g.key}>
            <legend>{g.title}</legend>
            {g.items.map((it) => (
              <label key={it.id} className="check">
                <input
                  type="checkbox"
                  checked={(filters[g.key] as string[]).includes(it.id)}
                  onChange={() => toggle(g.key, it.id)}
                />
                <span>{it.label}</span>
                <small className="muted">{it.count}</small>
              </label>
            ))}
          </fieldset>
        ))}
    </div>
  );
}
