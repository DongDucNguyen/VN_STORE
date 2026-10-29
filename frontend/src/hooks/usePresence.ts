import { useEffect, useState } from "react";
import { prefersReducedMotion } from "./useMotionPreference";

/** Giữ phần tử thêm `ms` sau khi đóng để chạy hiệu ứng rời đi (`closing`). Mở lại giữa chừng thì hủy đóng.
 *  Giảm chuyển động: gỡ ngay. Nghiệp vụ (focus, khóa cuộn) vẫn bám theo `open`, không chờ hiệu ứng. */
export function usePresence(open: boolean, ms: number) {
  const [mounted, setMounted] = useState(open);
  useEffect(() => {
    if (open) {
      setMounted(true);
      return;
    }
    if (prefersReducedMotion()) {
      setMounted(false);
      return;
    }
    const t = setTimeout(() => setMounted(false), ms);
    return () => clearTimeout(t);
  }, [open, ms]);
  return { mounted: open || mounted, closing: !open && mounted };
}
