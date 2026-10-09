import { useEffect, useState } from "react";
import { api, ApiError, type ProductSummary } from "../api";
import { ErrorBox, Loading, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { useFavorites } from "../favorites";
import { href } from "../router";

type Entry = { id: string; name: string; count: number; extra?: string };

function EntryList({ title, load, param, empty }: {
  title: string;
  load: () => Promise<Entry[]>;
  param: string;
  empty: string;
}) {
  const [items, setItems] = useState<Entry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    load().then(setItems).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [load]);
  return (
    <div className="page">
      <h1>{title}</h1>
      {error && <ErrorBox message={error} />}
      {!error && !items && <Loading />}
      {items && items.length === 0 && <Notice>{empty}</Notice>}
      {items && items.length > 0 && (
        <ul className="entry-list">
          {items.map((x) => (
            <li key={x.id}>
              <a href={href("/search", { [param]: x.id })}>
                <b>{x.name}</b>
                {x.extra && <span className="muted small"> {x.extra}</span>}
                <small className="muted">{x.count} sản phẩm</small>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
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

export const BrandsPage = () => (
  <EntryList title="Thương hiệu" load={loadBrands} param="brand" empty="Chưa có thương hiệu nào trong catalog." />
);
export const PlacesPage = () => (
  <EntryList title="Làng nghề" load={loadPlaces} param="place" empty="Chưa có làng nghề nào trong catalog." />
);

export function FavoritesPage() {
  const fav = useFavorites();
  const [items, setItems] = useState<ProductSummary[] | null>(null);
  const key = fav.ids.join(",");
  useEffect(() => {
    // Sản phẩm đã gỡ khỏi catalog thì bỏ qua.
    Promise.all(fav.ids.map((id) => api.product(id).catch(() => null))).then((r) =>
      setItems(r.filter((x): x is NonNullable<typeof x> => x !== null)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return (
    <div className="page">
      <h1>Yêu thích</h1>
      <p className="muted small">Lưu trên thiết bị này, không cần tài khoản.</p>
      {!items && <Loading />}
      {items && items.length === 0 && <Notice>Chưa có sản phẩm yêu thích.</Notice>}
      {items && items.length > 0 && <ProductGrid items={items} />}
    </div>
  );
}
