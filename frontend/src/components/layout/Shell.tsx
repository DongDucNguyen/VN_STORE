import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { openAssistant } from "../../assistant/useAssistant";
import { ART } from "../../content/editorialAssets";
import { useDialogFocus } from "../../hooks/useDialogFocus";
import { type MotionChoice, type ThemeChoice, usePreferences } from "../../hooks/useMotionPreference";
import { usePresence } from "../../hooks/usePresence";
import { crossfade } from "../../motion/transitions";
import { BambooDivider, LotusMark } from "../brand/Motifs";
import { Icon } from "../ui/Icon";

export type RouteKind = "home" | "explore" | "task" | "internal";

const NAV = [
  { href: "#/search", label: "Khám phá", match: (p: string) => p === "/search" || p === "/image" },
  { href: "#/places", label: "Làng nghề", match: (p: string) => p === "/places" },
  { href: "#/brands", label: "Thương hiệu", match: (p: string) => p === "/brands" },
] as const;

function FavCount({ n }: { n: number }) {
  return n > 0 ? <span className="nav-count"> ({n})</span> : null;
}

export function AppHeader({ path, favCount, kind }: { path: string; favCount: number; kind: RouteKind }) {
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const sheet = usePresence(menu, 220);
  useDialogFocus(menu, menuRef, () => setMenu(false), true);
  useEffect(() => setMenu(false), [path]);
  useEffect(() => {
    if (menu) menuRef.current?.querySelector<HTMLElement>("a, button")?.focus();
  }, [menu]);
  const current = (match: boolean) => (match ? "page" : undefined);

  // “Nét tre”: một vạch mực trượt tới mục đang rê chuột/đang focus, rồi trở về mục của trang hiện tại.
  const navRef = useRef<HTMLElement>(null);
  const [ink, setInk] = useState({ x: 0, w: 0, on: false });
  const inkTo = useCallback((el: HTMLElement | null) => {
    setInk(el ? { x: el.offsetLeft, w: el.offsetWidth, on: true } : (s) => ({ ...s, on: false }));
  }, []);
  const inkHome = useCallback(
    () => inkTo(navRef.current?.querySelector<HTMLElement>('[aria-current="page"]') ?? null), [inkTo]);
  useLayoutEffect(inkHome, [path, favCount, inkHome]);
  useEffect(() => {
    document.fonts?.ready.then(inkHome).catch(() => {});
    window.addEventListener("resize", inkHome);
    return () => window.removeEventListener("resize", inkHome);
  }, [inkHome]);
  const inkHandlers = {
    onPointerEnter: (e: React.PointerEvent<HTMLElement>) => inkTo(e.currentTarget),
    onFocus: (e: React.FocusEvent<HTMLElement>) => inkTo(e.currentTarget),
  };

  return (
    <header className={`app-header ${kind === "internal" ? "is-internal" : ""}`}>
      <div className="container header-inner">
        <a href="#/" className="wordmark" aria-current={current(path === "/")}>VNStore</a>
        {kind === "internal" && <span className="header-kicker">Công cụ dữ liệu</span>}
        <nav className="primary-nav" aria-label="Điều hướng chính" ref={navRef} onPointerLeave={inkHome} onBlur={inkHome}>
          {NAV.map((n) => (
            <a key={n.href} href={n.href} aria-current={current(n.match(path))} {...inkHandlers}>{n.label}</a>
          ))}
          <a href="#/favorites" aria-current={current(path === "/favorites")} {...inkHandlers}>Yêu thích<FavCount n={favCount} /></a>
          <span className={`nav-ink ${ink.on ? "is-on" : ""}`} aria-hidden="true"
            style={{ transform: `translateX(${ink.x}px) scaleX(${ink.w / 100})` }} />
        </nav>
        <div className="header-tools">
          {path !== "/search" && (
            <a className="icon-link" href="#/search" aria-label="Tìm kiếm"><Icon name="search" size={22} /></a>
          )}
          <button type="button" className="icon-link menu-toggle" aria-label="Mở menu" aria-expanded={menu}
            aria-controls="site-menu" onClick={() => setMenu(true)}>
            <Icon name="menu" size={22} />
          </button>
        </div>
      </div>
      {kind === "internal" && <BambooDivider className="header-rule" />}
      {sheet.mounted && (
        <>
          <div className={`sheet-backdrop ${sheet.closing ? "is-closing" : ""}`} onClick={() => setMenu(false)} aria-hidden="true" />
          <div className={`site-menu ${sheet.closing ? "is-closing" : ""}`} id="site-menu" role="dialog" aria-modal="true"
            aria-label="Menu" ref={menuRef} inert={sheet.closing || undefined}>
            <div className="sheet-head">
              <span className="wordmark">VNStore</span>
              <button type="button" className="icon-link" aria-label="Đóng menu" onClick={() => setMenu(false)}>
                <Icon name="close" size={22} />
              </button>
            </div>
            <nav aria-label="Menu" className="menu-links">
              <a href="#/search" aria-current={current(path === "/search")}>Khám phá sản phẩm</a>
              <a href="#/image" aria-current={current(path === "/image")}>Tìm bằng ảnh</a>
              <a href="#/places" aria-current={current(path === "/places")}>Làng nghề</a>
              <a href="#/brands" aria-current={current(path === "/brands")}>Thương hiệu</a>
              <a href="#/assistant/memory" aria-current={current(path === "/assistant/memory")}>Trợ lý ghi nhớ gì</a>
            </nav>
            <DisplayPrefs />
          </div>
        </>
      )}
    </header>
  );
}

export function MobileNav({ path, favCount }: { path: string; favCount: number }) {
  const current = (match: boolean) => (match ? "page" : undefined);
  return (
    <nav className="mobile-nav" aria-label="Điều hướng nhanh">
      <a href="#/" aria-current={current(path === "/")}><Icon name="home" size={22} /><span>Khám phá</span></a>
      <a href="#/search" aria-current={current(path === "/search" || path === "/image")}>
        <Icon name="search" size={22} /><span>Tìm kiếm</span>
      </a>
      <a href="#/favorites" aria-current={current(path === "/favorites")}>
        <Icon name="heart" size={22} /><span>Yêu thích<FavCount n={favCount} /></span>
      </a>
      <button type="button" className="mobile-nav-assistant" aria-label="Mở trợ lý mua sắm" onClick={() => openAssistant()}>
        <LotusMark size={24} /><span>Trợ lý</span>
      </button>
    </nav>
  );
}

export function DisplayPrefs({ className = "" }: { className?: string }) {
  const p = usePreferences();
  return (
    <div className={`display-prefs ${className}`}>
      <label>
        <span>Giao diện</span>
        <select value={p.theme} onChange={(e) => {
          const v = e.target.value as ThemeChoice;
          crossfade(() => p.setTheme(v));
        }}>
          <option value="system">Theo hệ thống</option>
          <option value="light">Sáng</option>
          <option value="dark">Tối</option>
        </select>
      </label>
      <label>
        <span>Chuyển động</span>
        <select value={p.systemReduce ? "reduce" : p.motion} disabled={p.systemReduce}
          onChange={(e) => p.setMotion(e.target.value as MotionChoice)}>
          <option value="system">Theo hệ thống</option>
          <option value="reduce">Giảm</option>
        </select>
      </label>
      {p.systemReduce && <p className="small muted">Thiết bị đang yêu cầu giảm chuyển động.</p>}
      {p.saveFailed && <p className="small warn-text" role="status">Trình duyệt không lưu được lựa chọn; áp dụng cho lần xem này.</p>}
    </div>
  );
}

export function LandscapeFooter({ kind, catalogVersion }: { kind: RouteKind; catalogVersion?: string }) {
  if (kind === "internal") {
    return (
      <footer className="site-footer is-colophon">
        <div className="container">
          <BambooDivider className="footer-rule" />
          <p className="small muted">VNStore · công cụ nội bộ · Catalog {catalogVersion ?? "—"}</p>
        </div>
      </footer>
    );
  }
  const compact = kind === "task";
  return (
    <footer className={`site-footer ${compact ? "is-compact" : ""}`}>
      <div className="container footer-top">
        <div className="footer-brand">
          <a href="#/" className="wordmark">VNStore</a>
          <p>Những món đồ Việt, kể bằng chất liệu và nguồn gốc có căn cứ.</p>
        </div>
        <nav aria-label="Liên kết chân trang" className="footer-links">
          <a href="#/search">Khám phá</a>
          <a href="#/places">Làng nghề</a>
          <a href="#/brands">Thương hiệu</a>
          <a href="#/favorites">Yêu thích</a>
          <a href="#/assistant/memory">Trợ lý ghi nhớ gì</a>
        </nav>
        <div className="footer-note">
          <p>Nhãn nguồn gốc lấy từ catalog đã kiểm tra, không suy ra từ hình ảnh. Tranh tre, sen, nón trên trang là minh họa.</p>
          <p className="colophon">Catalog {catalogVersion ?? "—"} · bản demo</p>
          <DisplayPrefs className="footer-prefs" />
        </div>
      </div>
      <div className="footer-scene" aria-hidden="true">
        <picture>
          <source media="(max-width: 767px)" srcSet={ART.footerLandscapeSm.src} />
          <img src={ART.footerLandscape.src} width={ART.footerLandscape.width} height={ART.footerLandscape.height}
            alt="" loading="lazy" decoding="async" />
        </picture>
      </div>
    </footer>
  );
}
