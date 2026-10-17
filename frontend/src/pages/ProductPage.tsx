import { Fragment, useEffect, useRef, useState } from "react";
import { api, ApiError, type ProductDetail, type ProductSummary } from "../api";
import { ArtSection, MarginArtwork } from "../components/brand/Art";
import { BambooLines, LotusMark } from "../components/brand/Motifs";
import { ErrorBox, Loading, OriginBadges } from "../components/common";
import { Icon } from "../components/ui/Icon";
import { ART } from "../content/editorialAssets";
import { ProductGrid } from "../components/ProductCard";
import { ProductReviews } from "../components/ProductReviews";
import { openAssistant } from "../assistant/useAssistant";
import { useFavorites } from "../favorites";
import { formatDate, formatPrice, formatVnd } from "../format";
import { href } from "../router";
import { prefersReducedMotion } from "../hooks/useMotionPreference";
import { loadProduct } from "../motion/productPrefetch";
import { signalPageReady } from "../motion/transitions";

const DIM_LABELS: Record<string, string> = {
  length_mm: "Dài (mm)", width_mm: "Rộng (mm)", height_mm: "Cao (mm)", diameter_mm: "Đường kính (mm)",
  volume_ml: "Dung tích (ml)", weight_g: "Khối lượng (g)",
};
const AVAIL: Record<string, string> = { in_stock: "Còn hàng", out_of_stock: "Hết hàng", unknown: "Chưa rõ tình trạng" };

function claimValue(v: boolean | "unknown"): string {
  return v === true ? "Có" : v === false ? "Không" : "Chưa rõ";
}

export function ProductPage({ id }: { id: string }) {
  const [p, setP] = useState<ProductDetail | null>(null);
  const [similar, setSimilar] = useState<ProductSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [img, setImg] = useState(0);
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());
  const fav = useFavorites();

  useEffect(() => {
    let alive = true;
    setP(null);
    setSimilar([]);
    setError(null);
    setImg(0);
    setFailedImages(new Set());
    loadProduct(id)
      .then((r) => {
        if (!alive) return;
        setP(r);
        if (!r.images.length) signalPageReady();
      })
      .catch((e) => {
        if (!alive) return;
        setError(e instanceof ApiError ? e.message : String(e));
        signalPageReady();
      });
    api
      .similar(id)
      .then((r) => alive && setSimilar(r.results))
      .catch(() => alive && setSimilar([]));
    return () => {
      alive = false;
    };
  }, [id]);

  if (error) return <div className="page container"><ErrorBox message={error} /></div>;
  if (!p) return <div className="page container"><Loading label="Đang tải sản phẩm…" /></div>;

  const sourceById = Object.fromEntries(p.sources.map((s) => [s.id, s]));
  const dims = Object.entries(p.dimensions).filter(([k, v]) => k in DIM_LABELS && typeof v === "number");
  const availableImages = p.images.filter((im) => !failedImages.has(im.url));
  const selected = p.images[img];
  const current = availableImages.find((im) => im.id === selected?.id) ?? availableImages[0];
  const imageFailed = (url: string) => setFailedImages((old) => new Set([...old, url]));

  const liked = fav.has(p.id);
  const anchors = [
    p.description_vi ? { id: "p-intro", label: "Giới thiệu" } : null,
    { id: "p-attrs", label: "Thuộc tính" },
    { id: "p-variants", label: "Biến thể" },
    { id: "p-origin", label: "Nguồn gốc" },
    { id: "p-reviews", label: "Đánh giá" },
  ].filter((x): x is { id: string; label: string } => x !== null);
  // Router dùng hash nên neo mục cuộn bằng script, không đổi URL.
  const jump = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ block: "start", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    el.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
  };

  return (
    <div className="page product-page">
      <ArtSection className="product-hero" art={<BambooLines className="product-bamboo" />}>
        <div className="container">
          <nav className="crumbs" aria-label="Danh mục">
            <a href="#/">Trang chủ</a>
            {p.category_path.map((c) => (
              <span key={c.id}>
                {" "}<span aria-hidden="true">/</span> <a href={href("/search", { cat: c.id })}>{c.name_vi}</a>
              </span>
            ))}
          </nav>

          <div className="product-top">
            <div className="gallery">
              <ZoomFrame>
                {current ? (
                  <img key={current.url} src={current.url} alt={current.alt_vi} fetchPriority="high"
                    onLoad={signalPageReady} onError={() => { imageFailed(current.url); signalPageReady(); }} />
                ) : (
                  <div className="img-missing">
                    {p.images.length ? <div><p>Ảnh tạm thời không tải được</p><button className="btn" onClick={() => {
                      setFailedImages(new Set()); setImg(0);
                    }}>Tải lại ảnh</button></div> : "Chưa có ảnh"}
                  </div>
                )}
              </ZoomFrame>
              {availableImages.length > 1 && (
                <div className="thumbs" role="group" aria-label="Ảnh sản phẩm">
                  {availableImages.map((im) => (
                    <button key={im.id} className={im.id === current?.id ? "on" : ""} aria-pressed={im.id === current?.id}
                      onClick={() => setImg(p.images.findIndex((candidate) => candidate.id === im.id))} aria-label={im.alt_vi}>
                      <img src={im.url} alt="" loading="lazy" onError={() => imageFailed(im.url)} />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="product-info">
              <h1 className="product-title">{p.name_vi}<span className="editorial-mark" aria-hidden="true" /></h1>
              <p className="product-makers">
                {p.brand && <>Thương hiệu: <a href={href("/search", { brand: p.brand.id })}>{p.brand.name}</a></>}
                {p.brand && p.maker && " · "}
                {p.maker && <>Nhà sản xuất: {p.maker.name}</>}
                {p.craft_village && (
                  <> · Làng nghề: <a href={href("/search", { place: p.craft_village.id })}>{p.craft_village.name}</a></>
                )}
              </p>
              <div className="price-block">
                <p className={`price ${p.price.min_vnd == null ? "price-unknown" : ""}`}>{formatPrice(p.price)}</p>
                <p className="muted small">
                  {p.price.observed_at ? <>Giá catalog ghi nhận ngày {formatDate(p.price.observed_at)}</> : "Giá tham khảo từ catalog"}
                </p>
              </div>
              <OriginBadges badges={p.origin_badges} />
              {p.short_description_vi && <p className="product-short">{p.short_description_vi}</p>}
              <div className="product-actions">
                <button className="btn btn-primary btn-lg" onClick={() => openAssistant({ productId: p.id, text: "Sản phẩm này có phù hợp với mình không?" })}>
                  <Icon name="chat" /> Hỏi trợ lý về sản phẩm này
                </button>
                <button className={`btn btn-lg fav-btn ${liked ? "is-on" : ""}`} aria-pressed={liked} onClick={() => fav.toggle(p.id)}>
                  <Icon name="heart" filled={liked} /> {liked ? "Đã yêu thích" : "Yêu thích"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </ArtSection>

      <nav className="section-anchors" aria-label="Mục trong trang">
        <div className="container">
          {anchors.map((a) => (
            <button key={a.id} type="button" className="anchor-link" onClick={() => jump(a.id)}>{a.label}</button>
          ))}
        </div>
      </nav>

      <div className="container product-sections">
        {p.description_vi && (
          <section id="p-intro" className="product-section">
            <h2 tabIndex={-1}>Giới thiệu</h2>
            <p className="prose">{p.description_vi}</p>
          </section>
        )}

        <ArtSection className="product-section" id="p-attrs"
          art={<MarginArtwork asset={ART.textileEdge} className="attrs-textile" />}>
          <h2 tabIndex={-1}>Thuộc tính</h2>
          <dl className="attrs">
            {p.materials.length > 0 && (<><dt>Chất liệu</dt><dd>{p.materials.join(", ")}</dd></>)}
            {p.colors.length > 0 && (<><dt>Màu</dt><dd>{p.colors.join(", ")}</dd></>)}
            {p.craft_techniques.length > 0 && (<><dt>Kỹ thuật</dt><dd>{p.craft_techniques.join(", ")}</dd></>)}
            {p.motifs.length > 0 && (<><dt>Hoa văn</dt><dd>{p.motifs.join(", ")}</dd></>)}
            {p.intended_uses.length > 0 && (<><dt>Công dụng</dt><dd>{p.intended_uses.join(", ")}</dd></>)}
            {dims.map(([k, v]) => (<Fragment key={k}><dt>{DIM_LABELS[k]}</dt><dd>{String(v)}</dd></Fragment>))}
          </dl>
        </ArtSection>

        <section id="p-variants" className="product-section">
          <h2 tabIndex={-1}>Biến thể</h2>
          <p className="muted small">Các mẫu và giá được ghi nhận trong catalog — dùng để tham khảo, không phải đặt hàng.</p>
          <div className="table-wrap" role="region" aria-label="Bảng biến thể" tabIndex={0}>
            <table>
              <thead>
                <tr><th>SKU</th><th>Mẫu</th><th>Giá</th><th>Ngày ghi nhận</th><th>Tình trạng</th></tr>
              </thead>
              <tbody>
                {p.variants.map((v) => (
                  <tr key={v.sku}>
                    <td><code>{v.sku}</code></td>
                    <td>{v.name_vi || Object.values(v.attributes ?? {}).join(", ") || "—"}</td>
                    <td className="num">
                      {v.price_vnd == null ? "Liên hệ" : formatVnd(v.price_vnd)}
                      {v.original_price_vnd && v.price_vnd && v.original_price_vnd > v.price_vnd && (
                        <s className="muted small"> {formatVnd(v.original_price_vnd)}</s>
                      )}
                    </td>
                    <td>{formatDate(v.observed_at)}</td>
                    <td>{AVAIL[v.availability] ?? v.availability}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <ArtSection className="product-section origin-section" id="p-origin"
          art={<MarginArtwork asset={ART.lotusBotanical02} className="origin-lotus" />}>
          <h2 tabIndex={-1}>Nguồn gốc và căn cứ<span className="editorial-mark" aria-hidden="true" /></h2>
          <p className="muted small origin-explain">
            Mỗi nhận định đi kèm nguồn. “Nhà sản xuất công bố” nghĩa là thông tin do bên bán/sản xuất đưa ra;
            “Đã đối chiếu nguồn” là đã kiểm tra tài liệu nguồn, không phải xác thực độc lập hàng hóa.
          </p>
          <div className="table-wrap origin-table" role="region" aria-label="Bảng nguồn gốc" tabIndex={0}>
            <table>
              <thead>
                <tr><th>Tiêu chí</th><th>Giá trị</th><th>Mức xác minh</th><th>Ngày kiểm tra</th><th>Nguồn</th></tr>
              </thead>
              <tbody>
                {p.origin_claims.map((c, i) => (
                  <tr key={i}>
                    <td>
                      {c.label}
                      {c.places.length > 0 && <div className="muted small">{c.places.map((x) => x.name_as_sourced).join(", ")}</div>}
                      {c.detail_vi && <div className="muted small">{c.detail_vi}</div>}
                    </td>
                    <td><span className={`claim claim-${c.value === true ? "yes" : c.value === false ? "no" : "unknown"}`}>{claimValue(c.value)}</span></td>
                    <td>{c.status_label}</td>
                    <td>{formatDate(c.checked_at)}</td>
                    <td>
                      {c.source_ids.length === 0 ? "—" : c.source_ids.map((sid) => {
                        const s = sourceById[sid];
                        return s?.url ? (
                          <a key={sid} href={s.url} target="_blank" rel="noopener noreferrer">{s.publisher}</a>
                        ) : (
                          <span key={sid}>{s?.publisher ?? sid}</span>
                        );
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="sources-title">Nguồn tham khảo</h3>
          <ul className="sources">
            {p.sources.map((s) => (
              <li key={s.id}>
                <Icon name="source" size={16} />
                <span>
                  {s.url ? <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title || s.url}</a> : s.title || s.id}
                  <span className="muted small"> — {s.publisher}, truy cập {formatDate(s.retrieved_at)}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="muted small">
            Cập nhật {formatDate(p.updated_at)} · Biên tập viên kiểm tra {formatDate(p.reviewed_at)}
          </p>
        </ArtSection>

        <div id="p-reviews" className="product-section">
          <ProductReviews productId={p.id} />
        </div>

        {similar.length > 0 && (
          <section className="product-section similar">
            <h2><LotusMark size={22} className="heading-mark" /> Sản phẩm tương tự</h2>
            <ProductGrid items={similar} />
          </section>
        )}
      </div>
    </div>
  );
}

/** Khung ảnh chính: rê chuột (con trỏ chính xác) để phóng to theo đúng điểm đang xem — xem rõ nan, men, sợi vải. */
function ZoomFrame({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const frame = useRef(0);
  const canZoom = () => typeof matchMedia === "function" && matchMedia("(hover: hover) and (pointer: fine)").matches
    && !prefersReducedMotion();
  return (
    <div
      ref={ref}
      className="gallery-main"
      onPointerEnter={() => { if (canZoom()) ref.current?.classList.add("is-zoom"); }}
      onPointerLeave={() => ref.current?.classList.remove("is-zoom")}
      onPointerMove={(e) => {
        const el = ref.current;
        if (!el || !el.classList.contains("is-zoom")) return;
        const r = el.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width) * 100;
        const y = ((e.clientY - r.top) / r.height) * 100;
        cancelAnimationFrame(frame.current);
        frame.current = requestAnimationFrame(() => {
          el.style.setProperty("--zx", `${x}%`);
          el.style.setProperty("--zy", `${y}%`);
        });
      }}
    >
      {children}
    </div>
  );
}
