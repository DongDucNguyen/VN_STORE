import { useEffect, useState } from "react";
import { api, type Health } from "./api";
import { useFavorites } from "./favorites";
import { BrandsPage, FavoritesPage, PlacesPage } from "./pages/BrowsePages";
import { HomePage } from "./pages/HomePage";
import { ProductPage } from "./pages/ProductPage";
import { SearchPage } from "./pages/SearchPage";
import { useRoute } from "./router";

function Page() {
  const route = useRoute();
  const m = route.path.match(/^\/p\/([^/]+)$/);
  if (m) return <ProductPage id={decodeURIComponent(m[1])} />;
  switch (route.path) {
    case "/search":
      return <SearchPage route={route} />;
    case "/brands":
      return <BrandsPage />;
    case "/places":
      return <PlacesPage />;
    case "/favorites":
      return <FavoritesPage />;
    case "/":
      return <HomePage />;
    default:
      return (
        <div className="page state">
          <p>Không tìm thấy trang.</p>
          <a className="btn" href="#/">Về trang chủ</a>
        </div>
      );
  }
}

export default function App() {
  const fav = useFavorites();
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);
  const fixture = health?.catalog?.version.startsWith("fixture");

  return (
    <>
      <header className="topbar">
        <a href="#/" className="logo">VNStore</a>
        <nav>
          <a href="#/places">Làng nghề</a>
          <a href="#/brands">Thương hiệu</a>
          <a href="#/favorites">Yêu thích{fav.ids.length > 0 && ` (${fav.ids.length})`}</a>
        </nav>
      </header>
      {fixture && (
        <div className="banner" role="note">
          Đang chạy với dữ liệu FIXTURE (giả) để kiểm thử — không phải sản phẩm thật.
        </div>
      )}
      {health?.catalog?.include_drafts && (
        <div className="banner" role="note">Chế độ phát triển: đang hiển thị cả sản phẩm draft.</div>
      )}
      <main>
        <Page />
      </main>
      <footer className="footer muted small">
        VNStore demo · Catalog {health?.catalog?.version ?? "—"} · Nhãn nguồn gốc lấy từ catalog đã kiểm tra, không suy
        ra từ hình ảnh.
      </footer>
    </>
  );
}
