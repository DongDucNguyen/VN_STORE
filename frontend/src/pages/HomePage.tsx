import { useEffect, useState } from "react";
import { api, ApiError, type CategoryNode, type ProductSummary } from "../api";
import { ErrorBox, Loading, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { SearchBar } from "../components/SearchBar";
import { href } from "../router";

const EXAMPLES = ["bình hoa dưới 5 triệu", "socola Bến Tre", "túi lục bình có quai", "áo nhuộm chàm", "giỏ mây không lấy tre"];

export function HomePage() {
  const [cats, setCats] = useState<CategoryNode[] | null>(null);
  const [items, setItems] = useState<ProductSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setError(null);
    Promise.all([api.categories(), api.products({ limit: "12" })])
      .then(([c, p]) => {
        setCats(c);
        setItems(p.results);
        setTotal(p.total);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, [retry]);

  return (
    <div className="page home">
      <section className="hero">
        <h1>Khám phá sản phẩm Việt</h1>
        <p>Tìm theo chất liệu, làng nghề, giá — mỗi nhãn nguồn gốc đều có căn cứ.</p>
        <SearchBar autoFocus />
        <div className="chips">
          <span className="chips-label">Thử:</span>
          {EXAMPLES.map((e) => (
            <a key={e} className="chip chip-suggest" href={href("/search", { q: e })}>
              {e}
            </a>
          ))}
        </div>
      </section>

      {error && <ErrorBox message={error} onRetry={() => setRetry((r) => r + 1)} />}
      {!error && !cats && <Loading />}

      {cats && (
        <section>
          <h2>Danh mục</h2>
          <div className="cat-grid">
            {cats.map((c) => (
              <a key={c.id} className="cat" href={href("/search", { cat: c.id })}>
                <b>{c.name_vi}</b>
                <small className="muted">{c.count} sản phẩm</small>
              </a>
            ))}
          </div>
        </section>
      )}

      {items && (
        <section>
          <h2>Sản phẩm</h2>
          {total === 0 ? (
            <Notice>
              Catalog chưa có sản phẩm được duyệt. Xem hướng dẫn nhập liệu trong <code>docs/huong-dan-nhap-lieu.md</code>.
            </Notice>
          ) : (
            <>
              <ProductGrid items={items} />
              {total > items.length && (
                <a className="btn btn-block" href={href("/search")}>
                  Xem tất cả {total} sản phẩm
                </a>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
