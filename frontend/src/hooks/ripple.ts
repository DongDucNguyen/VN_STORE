import { prefersReducedMotion } from "./useMotionPreference";

/** “Gợn mặt sen” từ tâm nút — cho thao tác bàn phím (Enter). Bấm chuột/chạm thì gợn lan từ điểm bấm
 *  (useMotionEffects). Hành động chạy ngay, không chờ animation. */
export function ripple(el: HTMLElement | null) {
  if (!el || prefersReducedMotion() || el.classList.contains("is-rippling")) return;
  const r = el.getBoundingClientRect();
  el.style.setProperty("--rx", `${r.width / 2}px`);
  el.style.setProperty("--ry", `${r.height / 2}px`);
  el.style.setProperty("--rs", `${Math.max(r.width, r.height) * 2.2}px`);
  el.classList.add("is-rippling");
  window.setTimeout(() => el.classList.remove("is-rippling"), 620);
}
