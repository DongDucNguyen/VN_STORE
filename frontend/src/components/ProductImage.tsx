import { useState } from "react";

export function ProductImage({ src, alt }: { src: string; alt: string }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  return failedSrc === src ? (
    <div className="img-missing">Ảnh tạm thời không tải được</div>
  ) : (
    <img src={src} alt={alt} loading="lazy" onError={() => setFailedSrc(src)} />
  );
}
