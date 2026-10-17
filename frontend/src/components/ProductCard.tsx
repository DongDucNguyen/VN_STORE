import { useRef, useState } from "react";
import type { ProductSummary } from "../api";
import { useFavorites } from "../favorites";
import { formatPrice } from "../format";
import { useSheen } from "../hooks/useSheen";
import { prefetchProduct } from "../motion/productPrefetch";
import { markHeroSource } from "../motion/transitions";
import { href } from "../router";
import { OriginBadges } from "./common";
import { ProductImage } from "./ProductImage";
import { Icon } from "./ui/Icon";
import { toast } from "./ui/Toaster";

export function ProductCard({ p, index = 0 }: { p: ProductSummary; index?: number }) {
  const fav = useFavorites();
  const liked = fav.has(p.id);
  const [burst, setBurst] = useState(0);
  const imgWrap = useRef<HTMLDivElement>(null);
  const sheen = useSheen<HTMLDivElement>();
  const prefetch = () => prefetchProduct(p.id);

  return (
    <article className="card" style={{ "--i": Math.min(index % 12, 7) } as React.CSSProperties}>
      <a
        className="card-link"
        href={href(`/p/${p.id}`)}
        onPointerEnter={prefetch}
        onFocus={prefetch}
        onTouchStart={prefetch}
        onClick={(e) => {
          // Chỉ bấm thường (không mở tab mới) mới cho ảnh bay sang trang chi tiết.
          if (e.button === 0 && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) {
            markHeroSource(imgWrap.current?.querySelector("img") ?? null);
          }
        }}
      >
        <div className="card-img" ref={(el) => { imgWrap.current = el; sheen.ref(el); }} {...sheen.handlers}>
          {p.image ? (
            <ProductImage key={p.image.url} src={p.image.url} alt={p.image.alt_vi} />
          ) : (
            <div className="img-missing">Chưa có ảnh</div>
          )}
          <span className="card-peek" aria-hidden="true">Xem chi tiết <Icon name="arrow" size={16} /></span>
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
        onClick={() => {
          fav.toggle(p.id);
          if (!liked) setBurst((b) => b + 1);
          toast(liked
            ? { text: "Đã bỏ khỏi Yêu thích" }
            : { text: "Đã lưu vào Yêu thích trên thiết bị này", action: { label: "Xem", href: "#/favorites" } });
        }}
      >
        <span className={`fav-heart ${burst > 0 ? "is-bounce" : ""}`} key={`h${burst}`}>
          <Icon name="heart" filled={liked} size={20} />
        </span>
        {burst > 0 && (
          <span className="petal-burst" key={`p${burst}`} aria-hidden="true">
            <i /><i /><i /><i /><i /><i />
          </span>
        )}
      </button>
    </article>
  );
}

export function ProductGrid({ items, busy = false }: { items: ProductSummary[]; busy?: boolean }) {
  return (
    <div className="grid" aria-busy={busy || undefined} data-reveal-group="">
      {items.map((p, i) => (
        <ProductCard key={p.id} p={p} index={i} />
      ))}
    </div>
  );
}
