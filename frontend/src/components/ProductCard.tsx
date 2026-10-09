import type { ProductSummary } from "../api";
import { useFavorites } from "../favorites";
import { formatPrice } from "../format";
import { href } from "../router";
import { OriginBadges } from "./common";

export function ProductCard({ p }: { p: ProductSummary }) {
  const fav = useFavorites();
  const liked = fav.has(p.id);
  return (
    <article className="card">
      <a className="card-link" href={href(`/p/${p.id}`)}>
        <div className="card-img">
          {p.image ? (
            <img src={p.image.url} alt={p.image.alt_vi} loading="lazy" />
          ) : (
            <div className="img-missing">Chưa có ảnh</div>
          )}
        </div>
        <div className="card-body">
          <h3 className="card-title">{p.name_vi}</h3>
          <p className="card-meta">
            {p.brand?.name ?? p.maker?.name ?? "Chưa rõ thương hiệu"}
            {p.craft_village && <> · {p.craft_village.name}</>}
          </p>
          <p className={`card-price ${p.price.min_vnd == null ? "price-unknown" : ""}`}>{formatPrice(p.price)}</p>
          <OriginBadges badges={p.origin_badges} compact />
        </div>
      </a>
      <button
        className={`fav ${liked ? "fav-on" : ""}`}
        aria-pressed={liked}
        aria-label={liked ? "Bỏ yêu thích" : "Yêu thích"}
        onClick={() => fav.toggle(p.id)}
      >
        {liked ? "♥" : "♡"}
      </button>
    </article>
  );
}

export function ProductGrid({ items }: { items: ProductSummary[] }) {
  return (
    <div className="grid">
      {items.map((p) => (
        <ProductCard key={p.id} p={p} />
      ))}
    </div>
  );
}
