import { useState } from "react";

/** Ảnh catalog: luôn contain (không cắt quai, miệng bình, mép khăn); lỗi thì hiện thông báo chữ. */
export function ProductImage({ src, alt, eager = false }: { src: string; alt: string; eager?: boolean }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  return failedSrc === src ? (
    <div className="img-missing">Ảnh tạm thời không tải được</div>
  ) : (
    <img src={src} alt={alt} loading={eager ? "eager" : "lazy"} decoding="async" onError={() => setFailedSrc(src)} />
  );
}
