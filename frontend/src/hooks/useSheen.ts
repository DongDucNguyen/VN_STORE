import { useRef } from "react";

/** Vệt sáng mềm theo con trỏ trên ảnh (chỉ chuột/bút, gộp theo khung hình). CSS đọc --mx/--my. */
export function useSheen<T extends HTMLElement>() {
  const el = useRef<T | null>(null);
  const frame = useRef(0);
  return {
    ref: (node: T | null) => { el.current = node; },
    handlers: {
      onPointerMove: (e: React.PointerEvent<T>) => {
        if (e.pointerType === "touch" || !el.current) return;
        const r = el.current.getBoundingClientRect();
        const x = e.clientX - r.left;
        const y = e.clientY - r.top;
        cancelAnimationFrame(frame.current);
        frame.current = requestAnimationFrame(() => {
          el.current?.style.setProperty("--mx", `${x}px`);
          el.current?.style.setProperty("--my", `${y}px`);
        });
      },
    },
  };
}
