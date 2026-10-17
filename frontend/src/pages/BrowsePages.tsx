import { useEffect, useState } from "react";
import { api, ApiError, type ProductSummary } from "../api";
import { ArtSection, EditorialPhoto, MarginArtwork } from "../components/brand/Art";
import { BambooDivider, LotusMark, NonLaLines, WaterRipple } from "../components/brand/Motifs";
import { EmptyState, ErrorBox, GridSkeleton, Loading, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { Icon } from "../components/ui/Icon";
import { ART } from "../content/editorialAssets";
import { useFavorites } from "../favorites";
import { href } from "../router";

type Entry = { id: string; name: string; count: number; extra?: string };

function useEntries(load: () => Promise<Entry[]>) {
  const [items, setItems] = useState<Entry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setError(null);
    load().then((r) => alive && setItems(r)).catch((e) => alive && setError(e instanceof ApiError ? e.message : String(e)));
    return () => { alive = false; };
  }, [load, retry]);
  return { items, error, retry: () => setRetry((r) => r + 1) };
}

/** Thẻ tên/số lượng thật. Thứ tự DOM giữ nguyên thứ tự đọc; nhịp lệch trục chỉ ở CSS. */
function EntryList({ items, param }: { items: Entry[]; param: string }) {
  return (
    <ul className="entry-list">
      {items.map((x) => (
        <li key={x.id}>
          <a href={href("/search", { [param]: x.id })}>
            <span className="entry-name">{x.name}</span>
            {x.extra && <span className="muted small entry-extra"> {x.extra}</span>}
            <small className="entry-count">{x.count} sản phẩm</small>
            <Icon name="arrow" size={18} className="entry-arrow" />
          </a>
        </li>
      ))}
    </ul>
  );
}

const loadBrands = () => api.brands().then((r) => r.map((b) => ({ id: b.id, name: b.name, count: b.count })));
const loadPlaces = () =>
  api.places().then((r) =>
    r.map((p) => ({
      id: p.id,
      name: p.name,
      count: p.count,
      extra: p.name_as_sourced !== p.name ? `(${p.name_as_sourced})` : undefined,
    })));

export function PlacesPage() {
  const { items, error, retry } = useEntries(loadPlaces);
  return (
    <div className="page browse-page places-page">
      <ArtSection className="editorial-masthead" art={<MarginArtwork asset={ART.weaveMacro} className="places-weave" />}>
        <div className="container places-intro">
          <div>
            <p className="eyebrow"><span className="editorial-mark" aria-hidden="true" />Theo dấu bàn tay</p>
            <h1 className="editorial-title">Làng nghề</h1>
            <p className="lede">
              Những nơi làm ra các món đồ trong catalog. Chọn một làng nghề hoặc nơi sản xuất để xem sản phẩm đã ghi
              nhận từ đó.
            </p>
          </div>
          <EditorialPhoto asset={ART.craftWorkbench} className="places-photo"
            caption="Minh họa bằng AI — không phải ảnh của một làng nghề trong danh sách." />
        </div>
      </ArtSection>
      <div className="container">
        <BambooDivider className="section-bamboo" />
        {error && <ErrorBox message={error} onRetry={retry} />}
        {!error && !items && <Loading />}
        {items && items.length === 0 && <EmptyState title="Chưa có làng nghề nào trong catalog." />}
        {items && items.length > 0 && <EntryList items={items} param="place" />}
      </div>
      <div className="closing-scene" aria-hidden="true"><WaterRipple /></div>
    </div>
  );
}

export function BrandsPage() {
  const { items, error, retry } = useEntries(loadBrands);
  return (
    <div className="page browse-page brands-page">
      <ArtSection className="editorial-masthead" art={<MarginArtwork asset={ART.lotusBotanical01} className="brands-lotus" />}>
        <div className="container">
          <p className="eyebrow"><span className="editorial-mark" aria-hidden="true" />Những cái tên làm nên món đồ</p>
          <h1 className="editorial-title">Thương hiệu</h1>
          <p className="lede">Thương hiệu và nhà sản xuất có sản phẩm trong catalog VNStore, kèm số sản phẩm đã ghi nhận.</p>
        </div>
      </ArtSection>
      <div className="container">
        {error && <ErrorBox message={error} onRetry={retry} />}
        {!error && !items && <Loading />}
        {items && items.length === 0 && <EmptyState title="Chưa có thương hiệu nào trong catalog." />}
        {items && items.length > 0 && <EntryList items={items} param="brand" />}
        <NonLaLines className="closing-ribs" />
      </div>
    </div>
  );
}

type FavState = { items: ProductSummary[]; removed: number; failed: number };

export function FavoritesPage() {
  const fav = useFavorites();
  const [state, setState] = useState<FavState | null>(null);
  const [retry, setRetry] = useState(0);
  const key = fav.ids.join(",");
  useEffect(() => {
    let alive = true;
    // Phân biệt món đã gỡ khỏi catalog (404) với lỗi kết nối; không biến lỗi mạng thành danh sách trống.
    Promise.all(fav.ids.map((id) => api.product(id).then(
      (p) => ({ p, kind: "ok" as const }),
      (e) => ({ p: null, kind: e instanceof ApiError && e.status === 404 ? "removed" as const : "failed" as const }),
    ))).then((r) => {
      if (!alive) return;
      setState({
        items: r.flatMap((x) => (x.p ? [x.p] : [])),
        removed: r.filter((x) => x.kind === "removed").length,
        failed: r.filter((x) => x.kind === "failed").length,
      });
    });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, retry]);
  return (
    <div className="page browse-page favorites-page">
      <ArtSection className="editorial-masthead compact" art={<LotusMark size={120} className="fav-lotus" />}>
        <div className="container">
          <h1 className="editorial-title">Những món bạn yêu thích</h1>
          <p className="muted">Lưu trên thiết bị này, không cần tài khoản.</p>
        </div>
      </ArtSection>
      <div className="container">
        {!state && fav.ids.length > 0 && <GridSkeleton count={Math.min(fav.ids.length, 8)} label="Đang tải món yêu thích…" />}
        {state?.failed ? (
          <div className="notice notice-warn" role="alert">
            <Icon name="alert" size={18} className="notice-icon" />
            <div>Chưa tải được {state.failed} món do lỗi kết nối. Danh sách yêu thích vẫn còn trên thiết bị.{" "}
              <button className="link" onClick={() => setRetry((r) => r + 1)}>Thử lại</button></div>
          </div>
        ) : null}
        {state && state.removed > 0 && (
          <Notice>{state.removed} món đã được gỡ khỏi catalog nên không còn hiển thị.</Notice>
        )}
        {(fav.ids.length === 0 || (state && state.items.length === 0 && !state.failed)) && (
          <EmptyState title="Chưa có sản phẩm yêu thích."
            action={<a className="btn btn-primary" href="#/search">Khám phá sản phẩm</a>}>
            Bấm biểu tượng trái tim trên một món đồ để giữ lại đây.
          </EmptyState>
        )}
        {state && state.items.length > 0 && fav.ids.length > 0 && <ProductGrid items={state.items} />}
      </div>
    </div>
  );
}
