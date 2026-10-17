import { useEffect, useRef, useState } from "react";
import { prefersReducedMotion } from "./useMotionPreference";

/** Bật cờ "đang chạy" đúng một lần khi phần tử vào viewport (design.md §7.4). Không setState theo frame;
 *  bỏ qua khi người dùng giảm chuyển động. Nội dung không phụ thuộc cờ này để hiển thị. */
export function useRevealOnce<T extends Element>(enabled = true) {
  const ref = useRef<T>(null);
  const [playing, setPlaying] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!enabled || !el || typeof IntersectionObserver === "undefined" || prefersReducedMotion()) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting) && !document.hidden) {
        setPlaying(true);
        io.disconnect();
      }
    }, { threshold: 0.25 });
    io.observe(el);
    return () => io.disconnect();
  }, [enabled]);
  return [ref, playing] as const;
}
