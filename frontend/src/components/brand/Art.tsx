import type { CSSProperties, ReactNode } from "react";
import type { EditorialAsset } from "../../content/editorialAssets";
import { useRevealOnce } from "../../hooks/useRevealOnce";

/** Chương có lớp mỹ thuật riêng: wrapper isolate; chỉ lớp decor bị clip, nội dung giữ nguyên focus/dropdown. */
export function ArtSection({ className = "", art, children, label, reveal = false, ...rest }: {
  className?: string; art?: ReactNode; children: ReactNode; label?: string; reveal?: boolean;
  id?: string; "aria-labelledby"?: string;
}) {
  const [ref, playing] = useRevealOnce<HTMLElement>(reveal);
  return (
    <section ref={ref} className={`art-section ${className} ${playing ? "is-playing" : ""}`} aria-label={label} {...rest}>
      {art && <div className="art-layer" aria-hidden="true">{art}</div>}
      {children}
    </section>
  );
}

/** Ảnh trang trí đặt theo neo của chương. Không nhận chuột, không vào cây truy cập. */
export function MarginArtwork({ asset, className, eager = false, style }: {
  asset: EditorialAsset; className: string; eager?: boolean; style?: CSSProperties;
}) {
  return (
    <img className={`margin-art ${className}`} src={asset.src} width={asset.width} height={asset.height} alt=""
      loading={eager ? "eager" : "lazy"} decoding="async" draggable={false} style={style} />
  );
}

/** Ảnh biên tập có chú thích xác định đây là minh họa. */
export function EditorialPhoto({ asset, caption, className = "", sizes }: {
  asset: EditorialAsset; caption?: string; className?: string; sizes?: string;
}) {
  return (
    <figure className={`editorial-photo ${className}`}>
      <img src={asset.src} width={asset.width} height={asset.height} alt={asset.alt} loading="lazy" decoding="async"
        sizes={sizes} />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}
