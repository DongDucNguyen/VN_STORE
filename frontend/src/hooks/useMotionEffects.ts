// Hiệu ứng chuyển động toàn cục (design.md §7.4): reveal theo chương khi cuộn, header khi cuộn, gợn lan tại
// điểm bấm. Nội dung chỉ bị ẩn chờ reveal khi JS đã chạy (<html class="motion-ready">) và người dùng không
// giảm chuyển động; phần đang nằm trong màn hình lúc trang hiện ra thì hiện ngay.
import { useEffect } from "react";
import { supportsViewTransitions } from "../motion/transitions";
import { prefersReducedMotion } from "./useMotionPreference";

/** Khối được reveal khi cuộn tới. Lưới sản phẩm dùng data-reveal-group (thẻ hiện so le theo --i). */
const REVEAL = [
  ".chapter-head", ".cat-windows", ".cat-links", ".lotus-copy", ".craft-copy", ".craft-hands", ".craft-bench",
  ".editorial-masthead .container", ".entry-list", ".product-section", ".material-band-copy", ".material-band-art",
  ".empty-state", ".image-guide", ".footer-top", ".chapter-more", ".load-more",
].join(",");

const RIPPLE = ".btn, .chip-suggest, .chip-clear, .anchor-link, .mobile-nav a, .mobile-nav button, .field-btn, .cat-link";

function inView(el: Element) {
  const r = el.getBoundingClientRect();
  return r.top < window.innerHeight * 0.96 && r.bottom > 0;
}

export function useMotionEffects() {
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("has-vt", supportsViewTransitions());
    // Mốc theo mép trên của khối thay vì tỷ lệ diện tích: khối cao hơn vài màn hình vẫn hiện khi cuộn tới.
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        e.target.classList.add("is-in");
        io.unobserve(e.target);
      }
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0 });

    const scan = () => {
      const reduce = prefersReducedMotion();
      root.classList.toggle("motion-ready", !reduce);
      document.querySelectorAll<HTMLElement>(`${REVEAL},[data-reveal-group]`).forEach((el) => {
        if (el.dataset.revealSeen) return;
        el.dataset.revealSeen = "";
        if (!el.matches("[data-reveal-group]")) el.setAttribute("data-reveal", "");
        // Đang trong màn hình (đầu trang, sau chuyển trang) thì hiện luôn; chuyển cảnh trang đã lo phần vào.
        if (reduce || inView(el)) el.classList.add("is-in");
        else io.observe(el);
      });
    };
    scan();
    // Gộp quét theo khung hình (SSE của trợ lý đổi DOM liên tục). Phần tử chưa quét vẫn hiển thị bình thường.
    let queued = 0;
    const mo = new MutationObserver(() => {
      if (!queued) queued = requestAnimationFrame(() => { queued = 0; scan(); });
    });
    mo.observe(document.getElementById("root") ?? document.body, { childList: true, subtree: true });

    // Header: thêm bóng khi đã cuộn khỏi đầu trang.
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        root.classList.toggle("is-scrolled", window.scrollY > 8);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    // Đổi lựa chọn chuyển động giữa phiên (trên thiết bị hoặc hệ điều hành) có hiệu lực ngay.
    const syncPref = () => {
      const reduce = prefersReducedMotion();
      root.classList.toggle("motion-ready", !reduce);
      if (reduce) document.querySelectorAll("[data-reveal]:not(.is-in),[data-reveal-group]:not(.is-in)")
        .forEach((el) => el.classList.add("is-in"));
    };
    const mq = matchMedia("(prefers-reduced-motion: reduce)");
    mq.addEventListener("change", syncPref);
    window.addEventListener("vnstore:prefs-changed", syncPref);

    // Gợn mặt sen tại đúng điểm bấm.
    const onDown = (e: PointerEvent) => {
      if (prefersReducedMotion()) return;
      const el = (e.target as Element | null)?.closest<HTMLElement>(RIPPLE);
      if (!el || (el as HTMLButtonElement).disabled) return;
      const r = el.getBoundingClientRect();
      el.style.setProperty("--rx", `${e.clientX - r.left}px`);
      el.style.setProperty("--ry", `${e.clientY - r.top}px`);
      el.style.setProperty("--rs", `${Math.max(r.width, r.height) * 2.2}px`);
      el.classList.remove("is-rippling");
      void el.offsetWidth;
      el.classList.add("is-rippling");
      window.setTimeout(() => el.classList.remove("is-rippling"), 620);
    };
    document.addEventListener("pointerdown", onDown, { passive: true });

    return () => {
      io.disconnect();
      mo.disconnect();
      cancelAnimationFrame(queued);
      window.removeEventListener("scroll", onScroll);
      mq.removeEventListener("change", syncPref);
      window.removeEventListener("vnstore:prefs-changed", syncPref);
      document.removeEventListener("pointerdown", onDown);
    };
  }, []);
}
