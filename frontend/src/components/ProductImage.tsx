import { useLayoutEffect, useRef, useState } from "react";

/** Ảnh catalog: luôn contain (không cắt quai, miệng bình, mép khăn); lỗi thì hiện thông báo chữ.
 *  Ảnh hiện dần khi tải xong; ảnh đã có trong bộ nhớ đệm hiện ngay, không nháy. */
export function ProductImage({ src, alt, eager = false }: { src: string; alt: string; eager?: boolean }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const ref = useRef<HTMLImageElement>(null);
  useLayoutEffect(() => {
    const img = ref.current;
    if (img?.complete && img.naturalWidth > 0) setLoadedSrc(src);
  }, [src]);
  return failedSrc === src ? (
    <div className="img-missing">Ảnh tạm thời không tải được</div>
  ) : (
    <img ref={ref} className={`img-fade ${loadedSrc === src ? "is-loaded" : ""}`} src={src} alt={alt}
      loading={eager ? "eager" : "lazy"} decoding="async" onLoad={() => setLoadedSrc(src)} onError={() => setFailedSrc(src)} />
  );
}
