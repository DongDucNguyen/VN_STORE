import { useEffect, useRef, useState } from "react";
import { api, type Health } from "./api";
import { AssistantPanel } from "./components/AssistantPanel";
import { BambooLines } from "./components/brand/Motifs";
import { AppHeader, LandscapeFooter, MobileNav, type RouteKind } from "./components/layout/Shell";
import { Icon } from "./components/ui/Icon";
import { Toaster } from "./components/ui/Toaster";
import { useMotionEffects } from "./hooks/useMotionEffects";
import { useFavorites } from "./favorites";
import { BrandsPage, FavoritesPage, PlacesPage } from "./pages/BrowsePages";
import { AssistantMemoryPage } from "./pages/AssistantMemoryPage";
import { CollectImagePage } from "./pages/CollectImagePage";
import { CollectVoicePage } from "./pages/CollectVoicePage";
import { HomePage } from "./pages/HomePage";
import { ImageSearchPage } from "./pages/ImageSearchPage";
import { ProductPage } from "./pages/ProductPage";
import { ReviewVoicePage } from "./pages/ReviewVoicePage";
import { SearchPage } from "./pages/SearchPage";
import { DiagnosticsPage } from "./pages/DiagnosticsPage";
import { type Route, useRoute } from "./router";

const INTERNAL = new Set(["/collect/voice", "/collect/image", "/review/voice", "/diagnostics"]);
const TASK = new Set(["/search", "/image", "/assistant/memory"]);
const TITLES: Record<string, string> = {
  "/": "VNStore — Nếp Việt trong từng món đồ",
  "/search": "Tìm kiếm — VNStore",
  "/image": "Tìm bằng ảnh — VNStore",
  "/places": "Làng nghề — VNStore",
  "/brands": "Thương hiệu — VNStore",
  "/favorites": "Yêu thích — VNStore",
  "/assistant/memory": "Trợ lý ghi nhớ gì — VNStore",
  "/collect/voice": "Thu âm — Công cụ dữ liệu VNStore",
  "/collect/image": "Thu ảnh — Công cụ dữ liệu VNStore",
  "/review/voice": "Duyệt bản chép lời — Công cụ dữ liệu VNStore",
  "/diagnostics": "Chẩn đoán — VNStore",
};

function routeKind(path: string): RouteKind {
  if (path === "/") return "home";
  if (INTERNAL.has(path)) return "internal";
  if (TASK.has(path) || path.startsWith("/p/")) return "task";
  return "explore";
}

function Page({ route }: { route: Route }) {
  const m = route.path.match(/^\/p\/([^/]+)$/);
  if (m) return <ProductPage id={decodeURIComponent(m[1])} />;
  switch (route.path) {
    case "/diagnostics":
      return <DiagnosticsPage />;
    case "/search":
      return <SearchPage route={route} />;
    case "/image":
      return <ImageSearchPage />;
    case "/collect/voice":
      return <CollectVoicePage />;
    case "/collect/image":
      return <CollectImagePage />;
    case "/review/voice":
      return <ReviewVoicePage />;
    case "/brands":
      return <BrandsPage />;
    case "/places":
      return <PlacesPage />;
    case "/favorites":
      return <FavoritesPage />;
    case "/assistant/memory":
      return <AssistantMemoryPage />;
    case "/":
      return <HomePage />;
    default:
      return <NotFound />;
  }
}

function NotFound() {
  return (
    <div className="page container not-found">
      <BambooLines className="not-found-art" />
      <h1>Không tìm thấy trang.</h1>
      <p className="muted">Đường dẫn này không có trong VNStore. Bạn có thể quay về trang chủ hoặc tìm một món đồ.</p>
      <p className="actions">
        <a className="btn btn-primary" href="#/">Về trang chủ</a>
        <a className="btn" href="#/search"><Icon name="search" /> Khám phá sản phẩm</a>
      </p>
    </div>
  );
}

export default function App() {
  const route = useRoute();
  const fav = useFavorites();
  const [health, setHealth] = useState<Health | null>(null);
  const mainRef = useRef<HTMLElement>(null);
  const firstPath = useRef(route.path);
  useMotionEffects();
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);
  const fixture = health?.catalog?.version.startsWith("fixture");
  const kind = routeKind(route.path);

  useEffect(() => {
    document.title = TITLES[route.path] ?? (route.path.startsWith("/p/") ? "Sản phẩm — VNStore" : "VNStore");
    // Đổi trang: đưa focus vào vùng nội dung chính để trình đọc màn hình bắt đầu từ trang mới.
    if (route.path !== firstPath.current) {
      firstPath.current = route.path;
      mainRef.current?.focus({ preventScroll: true });
    }
  }, [route.path]);

  return (
    <div className={`app route-${kind}`}>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); mainRef.current?.focus(); }}>
        Bỏ qua tới nội dung chính
      </a>
      <AppHeader path={route.path} favCount={fav.ids.length} kind={kind} />
      {fixture && (
        <div className="banner" role="note">
          <Icon name="alert" size={18} /> Đang chạy với dữ liệu FIXTURE (giả) để kiểm thử — không phải sản phẩm thật.
        </div>
      )}
      {health?.catalog?.include_drafts && (
        <div className="banner" role="note">
          <Icon name="alert" size={18} /> Chế độ phát triển: đang hiển thị cả sản phẩm draft.
        </div>
      )}
      <main id="main" ref={mainRef} tabIndex={-1}>
        <div className="route-view" key={route.path}>
          <Page route={route} />
        </div>
      </main>
      <LandscapeFooter kind={kind} catalogVersion={health?.catalog?.version} />
      {kind !== "internal" && <MobileNav path={route.path} favCount={fav.ids.length} />}
      <AssistantPanel hideLauncher={kind === "internal"} />
      {kind !== "internal" && <Toaster />}
    </div>
  );
}
