// Chuyển trang “Qua hiên” bằng View Transitions API (Chrome/Edge/Safari mới). Trình duyệt không hỗ trợ hoặc
// người dùng giảm chuyển động thì cập nhật ngay, không animation. Không bao giờ chặn thao tác quá ~260ms.
import { flushSync } from "react-dom";
import { prefersReducedMotion } from "../hooks/useMotionPreference";

type VT = { ready: Promise<void>; finished: Promise<void>; updateCallbackDone: Promise<void> };
type DocVT = Document & { startViewTransition?: (cb: () => Promise<void> | void) => VT };

const READY_EVENT = "vnstore:page-ready";
const MAX_WAIT_MS = 260;

export const supportsViewTransitions = () =>
  typeof document !== "undefined" && typeof (document as DocVT).startViewTransition === "function";

/** Trang mới báo đã có nội dung chính (ví dụ ảnh sản phẩm) để ảnh chung có thể bay sang đúng chỗ. */
export function signalPageReady() {
  window.dispatchEvent(new Event(READY_EVENT));
}

// Lưu ý: trong lúc callback của View Transition chưa xong, trình duyệt tạm dừng render — kể cả
// requestAnimationFrame. Vì vậy không chờ khung hình ở đây; chỉ chờ tín hiệu “sẵn sàng” có giới hạn thời gian.
function waitForPage(expectsReady: boolean): Promise<void> {
  if (!expectsReady) return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => {
      clearTimeout(t);
      window.removeEventListener(READY_EVENT, done);
      resolve();
    };
    const t = setTimeout(done, MAX_WAIT_MS);
    window.addEventListener(READY_EVENT, done);
  });
}

/** Đổi giao diện sáng/tối bằng một lớp hòa màu ngắn thay vì nháy. Không hỗ trợ hoặc giảm chuyển động: đổi ngay.
 *  `update` phải đổi DOM đồng bộ (chạy trong flushSync). */
export function crossfade(update: () => void) {
  const doc = document as DocVT;
  if (!supportsViewTransitions() || prefersReducedMotion() || document.hidden || pendingHero) {
    update();
    return;
  }
  const root = document.documentElement;
  root.dataset.vt = "theme";
  const vt = doc.startViewTransition!(() => flushSync(update));
  const end = () => {
    if (root.dataset.vt === "theme") delete root.dataset.vt;
  };
  vt.ready.catch(() => {});
  vt.updateCallbackDone.catch(() => {});
  vt.finished.then(end, end);
}

let pendingHero = false;

/** Gọi khi bấm một thẻ sản phẩm: ảnh của thẻ sẽ bay sang vị trí ảnh chính ở trang chi tiết. */
export function markHeroSource(img: HTMLElement | null) {
  if (!img || !supportsViewTransitions() || prefersReducedMotion()) return;
  document.querySelectorAll<HTMLElement>("[data-vt-hero]").forEach((el) => {
    el.style.removeProperty("view-transition-name");
    delete el.dataset.vtHero;
  });
  img.style.setProperty("view-transition-name", "product-hero");
  img.dataset.vtHero = "";
  document.documentElement.dataset.vt = "from-card";
  pendingHero = true;
}

function clearHero() {
  pendingHero = false;
  delete document.documentElement.dataset.vt;
  document.querySelectorAll<HTMLElement>("[data-vt-hero]").forEach((el) => {
    el.style.removeProperty("view-transition-name");
    delete el.dataset.vtHero;
  });
}

/** Đổi trang. Lưu ý: trong lúc View Transition chạy, trình duyệt dồn mọi thao tác chuột/chạm vào <html>, nên chỉ
 *  dùng nó cho khoảnh khắc ảnh thẻ bay sang trang chi tiết (ngay sau cú bấm), và hủy ngay khi người dùng chạm tiếp.
 *  Các lần đổi trang khác: cập nhật tức thì, trang mới trồi lên bằng CSS (.route-view) — không chặn thao tác.
 *  `update` phải cập nhật state đồng bộ (chạy trong flushSync). */
export function transitionPage(update: () => void, toProduct: boolean) {
  const doc = document as DocVT;
  const hero = pendingHero && toProduct;
  if (!hero || !supportsViewTransitions() || prefersReducedMotion() || document.hidden) {
    clearHero();
    update();
    return;
  }
  const root = document.documentElement;
  const vt = doc.startViewTransition!(async () => {
    root.dataset.vt = "to-product";
    flushSync(update);
    await waitForPage(true);
  });
  const skip = () => (vt as VT & { skipTransition?: () => void }).skipTransition?.();
  document.addEventListener("pointerdown", skip, { capture: true, once: true });
  const end = () => {
    document.removeEventListener("pointerdown", skip, { capture: true });
    clearHero();
  };
  // Chuyển cảnh bị bỏ qua (bấm liên tiếp, trùng tên…) không được thành lỗi trên trang.
  vt.ready.catch(() => {});
  vt.updateCallbackDone.catch(() => {});
  vt.finished.then(end, end);
}
