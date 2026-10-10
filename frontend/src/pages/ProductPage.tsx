import { Fragment, useEffect, useState } from "react";
import { api, ApiError, type ProductDetail, type ProductSummary } from "../api";
import { ErrorBox, Loading, OriginBadges } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { useFavorites } from "../favorites";
import { formatDate, formatPrice, formatVnd } from "../format";
import { href } from "../router";

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
    api
      .product(id)
      .then((r) => alive && setP(r))
      .catch((e) => alive && setError(e instanceof ApiError ? e.message : String(e)));
    api
      .similar(id)
      .then((r) => alive && setSimilar(r.results))
      .catch(() => alive && setSimilar([]));
    return () => {
      alive = false;
    };
  }, [id]);

  if (error) return <div className="page"><ErrorBox message={error} /></div>;
  if (!p) return <div className="page"><Loading /></div>;

  const sourceById = Object.fromEntries(p.sources.map((s) => [s.id, s]));
  const dims = Object.entries(p.dimensions).filter(([k, v]) => k in DIM_LABELS && typeof v === "number");
  const availableImages = p.images.filter((im) => !failedImages.has(im.url));
  const selected = p.images[img];
  const current = availableImages.find((im) => im.id === selected?.id) ?? availableImages[0];
  const imageFailed = (url: string) => setFailedImages((old) => new Set([...old, url]));

  return (
    <div className="page product-page">
      <nav className="crumbs" aria-label="Danh mục">
        <a href="#/">Trang chủ</a>
        {p.category_path.map((c) => (
          <span key={c.id}>
            {" "}› <a href={href("/search", { cat: c.id })}>{c.name_vi}</a>
          </span>
        ))}
      </nav>

      <div className="product-top">
        <div className="gallery">
          <div className="gallery-main">
            {current ? (
              <img key={current.url} src={current.url} alt={current.alt_vi} onError={() => imageFailed(current.url)} />
            ) : (
              <div className="img-missing">
                {p.images.length ? <div><p>Ảnh tạm thời không tải được</p><button className="btn" onClick={() => {
                  setFailedImages(new Set()); setImg(0);
                }}>Tải lại ảnh</button></div> : "Chưa có ảnh"}
              </div>
            )}
          </div>
          {availableImages.length > 1 && (
            <div className="thumbs">
              {availableImages.map((im) => (
                <button key={im.id} className={im.id === current?.id ? "on" : ""}
                  onClick={() => setImg(p.images.findIndex((candidate) => candidate.id === im.id))} aria-label={im.alt_vi}>
                  <img src={im.url} alt="" onError={() => imageFailed(im.url)} />
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="product-info">
          <h1>{p.name_vi}</h1>
          <p className="muted">
            {p.brand && <>Thương hiệu: <a href={href("/search", { brand: p.brand.id })}>{p.brand.name}</a></>}
            {p.brand && p.maker && " · "}
            {p.maker && <>Nhà sản xuất: {p.maker.name}</>}
            {p.craft_village && (
              <> · Làng nghề: <a href={href("/search", { place: p.craft_village.id })}>{p.craft_village.name}</a></>
            )}
          </p>
          <p className={`price ${p.price.min_vnd == null ? "price-unknown" : ""}`}>{formatPrice(p.price)}</p>
          {p.price.observed_at && <p className="muted small">Giá ghi nhận ngày {formatDate(p.price.observed_at)}</p>}
          <OriginBadges badges={p.origin_badges} />
          <p>{p.short_description_vi}</p>
          <button className={`btn ${fav.has(p.id) ? "btn-primary" : ""}`} onClick={() => fav.toggle(p.id)}>
            {fav.has(p.id) ? "♥ Đã yêu thích" : "♡ Yêu thích"}
          </button>
        </div>
      </div>

      {p.description_vi && (
        <section>
          <h2>Giới thiệu</h2>
          <p>{p.description_vi}</p>
        </section>
      )}

      <section>
        <h2>Thuộc tính</h2>
        <dl className="attrs">
          {p.materials.length > 0 && (<><dt>Chất liệu</dt><dd>{p.materials.join(", ")}</dd></>)}
          {p.colors.length > 0 && (<><dt>Màu</dt><dd>{p.colors.join(", ")}</dd></>)}
          {p.craft_techniques.length > 0 && (<><dt>Kỹ thuật</dt><dd>{p.craft_techniques.join(", ")}</dd></>)}
          {p.motifs.length > 0 && (<><dt>Hoa văn</dt><dd>{p.motifs.join(", ")}</dd></>)}
          {p.intended_uses.length > 0 && (<><dt>Công dụng</dt><dd>{p.intended_uses.join(", ")}</dd></>)}
          {dims.map(([k, v]) => (<Fragment key={k}><dt>{DIM_LABELS[k]}</dt><dd>{String(v)}</dd></Fragment>))}
        </dl>
      </section>

      <section>
        <h2>Biến thể</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>SKU</th><th>Mẫu</th><th>Giá</th><th>Ngày ghi nhận</th><th>Tình trạng</th></tr>
            </thead>
            <tbody>
              {p.variants.map((v) => (
                <tr key={v.sku}>
                  <td><code>{v.sku}</code></td>
                  <td>{v.name_vi || Object.values(v.attributes ?? {}).join(", ") || "—"}</td>
                  <td>
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

      <section>
        <h2>Nguồn gốc và căn cứ</h2>
        <p className="muted small">
          Mỗi nhận định đi kèm nguồn. “Nhà sản xuất công bố” nghĩa là thông tin do bên bán/sản xuất đưa ra;
          “Đã đối chiếu nguồn” là đã kiểm tra tài liệu nguồn, không phải xác thực độc lập hàng hóa.
        </p>
        <div className="table-wrap">
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
                  <td>{claimValue(c.value)}</td>
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
      </section>

      <section>
        <h2>Nguồn tham khảo</h2>
        <ul className="sources">
          {p.sources.map((s) => (
            <li key={s.id}>
              {s.url ? <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title || s.url}</a> : s.title || s.id}
              <span className="muted small"> — {s.publisher}, truy cập {formatDate(s.retrieved_at)}</span>
            </li>
          ))}
        </ul>
        <p className="muted small">
          Cập nhật {formatDate(p.updated_at)} · Biên tập viên kiểm tra {formatDate(p.reviewed_at)}
        </p>
      </section>

      {similar.length > 0 && (
        <section>
          <h2>Sản phẩm tương tự</h2>
          <ProductGrid items={similar} />
        </section>
      )}
    </div>
  );
}
