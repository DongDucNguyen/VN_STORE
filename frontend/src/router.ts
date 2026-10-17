// Router dựa trên hash, đủ cho demo: #/ , #/search?q=..., #/image, #/p/:id, #/brands, #/places, #/favorites
import { useEffect, useState } from "react";
import { transitionPage } from "./motion/transitions";

export interface Route {
  path: string;
  params: URLSearchParams;
}

function parse(): Route {
  const raw = window.location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { path, params: new URLSearchParams(query) };
}

const NAVIGATE_EVENT = "vnstore:navigate";

export function useRoute(): Route {
  const [route, setRoute] = useState(parse);
  useEffect(() => {
    let lastPath = parse().path;
    const onChange = () => {
      const next = parse();
      // Chỉ đổi bộ lọc: cập nhật đồng bộ, không cuộn, không chuyển cảnh.
      if (next.path === lastPath) {
        setRoute(next);
        return;
      }
      lastPath = next.path;
      // Đổi trang: chuyển cảnh “Qua hiên”; luôn đọc URL hiện tại để lượt bấm sau cùng thắng.
      transitionPage(() => {
        setRoute(parse());
        window.scrollTo(0, 0);
      }, next.path.startsWith("/p/"));
    };
    window.addEventListener("hashchange", onChange);
    window.addEventListener(NAVIGATE_EVENT, onChange);
    return () => {
      window.removeEventListener("hashchange", onChange);
      window.removeEventListener(NAVIGATE_EVENT, onChange);
    };
  }, []);
  return route;
}

export function href(path: string, params?: Record<string, string | string[] | null | undefined>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v == null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => qs.append(k, x));
    else qs.set(k, v);
  }
  const s = qs.toString();
  return `#${path}${s ? `?${s}` : ""}`;
}

/** Đổi route đồng bộ (pushState + sự kiện riêng) để giao diện cập nhật ngay trong cùng lượt xử lý,
 *  tránh checkbox/ô nhập bị nhảy về trạng thái cũ trong lúc chờ hashchange bất đồng bộ. */
export function navigate(path: string, params?: Record<string, string | string[] | null | undefined>) {
  const target = href(path, params);
  if (target === window.location.hash) return;
  window.history.pushState(null, "", target);
  window.dispatchEvent(new Event(NAVIGATE_EVENT));
}
