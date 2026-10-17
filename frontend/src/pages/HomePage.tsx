import { useEffect, useState } from "react";
import { api, ApiError, type CategoryNode, type ProductSummary } from "../api";
import { ArtSection, EditorialPhoto, MarginArtwork } from "../components/brand/Art";
import { ChapterNo, NonLaLines, WaterRipple } from "../components/brand/Motifs";
import { ErrorBox, GridSkeleton, Notice } from "../components/common";
import { ProductGrid } from "../components/ProductCard";
import { SearchBar } from "../components/SearchBar";
import { Icon } from "../components/ui/Icon";
import { ART, CATEGORY_ART } from "../content/editorialAssets";
import { href } from "../router";

const EXAMPLES = ["bình hoa dưới 5 triệu", "socola Bến Tre", "túi lục bình có quai", "áo nhuộm chàm", "giỏ mây không lấy tre"];

type Place = { id: string; name: string; count: number };

const errText = (e: unknown) => (e instanceof ApiError ? e.message : String(e));

export function HomePage() {
  // Mỗi khối tải độc lập: lỗi danh mục không làm mất danh sách sản phẩm và ngược lại.
  const [cats, setCats] = useState<CategoryNode[] | null>(null);
  const [catError, setCatError] = useState<string | null>(null);
  const [items, setItems] = useState<ProductSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [itemError, setItemError] = useState<string | null>(null);
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [retryCats, setRetryCats] = useState(0);
  const [retryItems, setRetryItems] = useState(0);

  useEffect(() => {
    let alive = true;
    setCatError(null);
    api.categories().then((c) => alive && setCats(c)).catch((e) => alive && setCatError(errText(e)));
    return () => { alive = false; };
  }, [retryCats]);

  useEffect(() => {
    let alive = true;
    setItemError(null);
    api.products({ limit: "12" })
      .then((p) => { if (alive) { setItems(p.results); setTotal(p.total); } })
      .catch((e) => alive && setItemError(errText(e)));
    return () => { alive = false; };
  }, [retryItems]);

  useEffect(() => {
    let alive = true;
    api.places()
      .then((r) => alive && setPlaces([...r].sort((a, b) => b.count - a.count).slice(0, 4)))
      .catch(() => alive && setPlaces([]));
    return () => { alive = false; };
  }, []);

  return (
    <div className="home">
      <Opening />
      <CategoriesChapter cats={cats} error={catError} onRetry={() => setRetryCats((r) => r + 1)} />
      <LotusInterlude />
      <ProductsChapter items={items} total={total} error={itemError} onRetry={() => setRetryItems((r) => r + 1)} />
      <CraftChapter places={places} />
    </div>
  );
}

/** Mở — chữ lớn, search, bóng tre ở mép phải, một tĩnh vật gốm nhỏ thấp bên phải. */
function Opening() {
  return (
    <ArtSection className="opening" reveal art={<>
      <MarginArtwork asset={ART.bambooShadow} className="opening-shadow" eager />
      <MarginArtwork asset={ART.bambooBranch} className="opening-branch nv-bamboo" eager />
      <MarginArtwork asset={ART.ceramic} className="opening-ceramic" eager />
    </>}>
      <div className="container opening-inner">
        <p className="eyebrow"><span className="editorial-mark" aria-hidden="true" />Đồ Việt · Người Việt · Cuộc sống đẹp hơn</p>
        <h1 className="display">
          <span className="display-mask"><span className="display-line">Nếp Việt</span></span>{" "}
          <span className="display-mask display-sub"><span className="display-line">Trong từng món đồ</span></span>
        </h1>
        <span className="short-rule" aria-hidden="true" />
        <p className="lede">
          Khám phá món đồ Việt theo chất liệu, làng nghề và giá. Mỗi nhãn nguồn gốc đều đi kèm căn cứ.
        </p>
        <SearchBar size="lg" />
        <div className="chips opening-examples">
          <span className="chips-label">Thử tìm:</span>
          {EXAMPLES.map((e) => (
            <a key={e} className="chip chip-suggest" href={href("/search", { q: e })}>
              {e}
            </a>
          ))}
        </div>
      </div>
    </ArtSection>
  );
}

/** 01 — danh mục: ba cửa sổ ảnh lệch cao độ + hai liên kết chữ; nón lá ló ở mép trái. */
function CategoriesChapter({ cats, error, onRetry }: { cats: CategoryNode[] | null; error: string | null; onRetry: () => void }) {
  const withArt = cats?.filter((c) => CATEGORY_ART[c.id]) ?? [];
  const windows = withArt.slice(0, 3);
  const rest = cats?.filter((c) => !windows.includes(c)) ?? [];
  return (
    <ArtSection className="chapter chapter-categories" aria-labelledby="ch-cat" reveal
      art={<MarginArtwork asset={ART.nonLa} className="chapter-nonla" />}>
      <div className="container chapter-grid">
        <header className="chapter-head">
          <ChapterNo n="01" />
          <h2 id="ch-cat" className="chapter-title">Những điều mộc mạc</h2>
          <p className="chapter-lede">
            Từ đất nung, sợi mây, tấm vải đến hộp sơn — chọn một chất liệu để bắt đầu.
          </p>
          <NonLaLines className="chapter-ribs" />
        </header>
        <div className="cat-gallery">
          {error && <ErrorBox message={`Chưa tải được danh mục. ${error}`} onRetry={onRetry} />}
          {!error && !cats && <p className="state-line" role="status"><span className="spinner" aria-hidden /> Đang tải danh mục…</p>}
          {cats && cats.length === 0 && <p className="muted">Catalog chưa có danh mục nào.</p>}
          {windows.length > 0 && (
            <div className="cat-windows">
              {windows.map((c) => {
                const art = CATEGORY_ART[c.id];
                return (
                  <a key={c.id} className="cat cat-window" href={href("/search", { cat: c.id })} aria-label={`${c.name_vi}, ${c.count} sản phẩm`}>
                    <span className="cat-figure">
                      <img src={art.image.src} width={art.image.width} height={art.image.height} alt="" loading="lazy" decoding="async" />
                    </span>
                    <span className="cat-name">{art.short}<Icon name="arrow" size={18} /></span>
                    <small className="cat-count">{c.count} sản phẩm</small>
                  </a>
                );
              })}
            </div>
          )}
          {rest.length > 0 && (
            <div className="cat-links">
              {rest.map((c) => (
                <a key={c.id} className="cat cat-link" href={href("/search", { cat: c.id })} aria-label={`${c.name_vi}, ${c.count} sản phẩm`}>
                  <span className="cat-name">{CATEGORY_ART[c.id]?.short ?? c.name_vi}</span>
                  <small className="cat-count">{c.count}</small>
                  <Icon name="arrow" size={18} />
                </a>
              ))}
            </div>
          )}
          <p className="art-credit">Ảnh danh mục là minh họa, không phải ảnh sản phẩm đang có trong catalog.</p>
        </div>
      </div>
    </ArtSection>
  );
}

/** 02 — khoảng nghỉ giữa trang: nền xanh rừng, cảnh đầm sen tĩnh. Không phải bộ sưu tập riêng. */
function LotusInterlude() {
  return (
    <ArtSection className="chapter chapter-lotus" aria-labelledby="ch-lotus" reveal>
      <div className="lotus-scene" aria-hidden="true">
        <picture>
          <source media="(max-width: 767px)" srcSet={ART.lotusMidpageMobile.src} />
          <source media="(max-width: 1279px)" srcSet={ART.lotusMidpageMd.src} />
          <img src={ART.lotusMidpage.src} width={ART.lotusMidpage.width} height={ART.lotusMidpage.height} alt=""
            loading="lazy" decoding="async" />
        </picture>
      </div>
      <div className="container lotus-copy">
        <ChapterNo n="02" />
        <h2 id="ch-lotus" className="chapter-title">Một khoảng an yên</h2>
        <p>
          Giữa nhịp sống vội, những món đồ làm bằng tay vẫn giữ một nhịp chậm — như mặt đầm sen buổi sớm.
        </p>
        <a className="text-link on-dark" href="#/search">Khám phá sản phẩm <Icon name="arrow" size={18} /></a>
        <WaterRipple className="lotus-ripple" />
      </div>
    </ArtSection>
  );
}

/** 03 — sản phẩm thật từ API; dải nan đan ngoài lưới bên phải, nét sen ở lề trái. */
function ProductsChapter({ items, total, error, onRetry }: {
  items: ProductSummary[] | null; total: number; error: string | null; onRetry: () => void;
}) {
  return (
    <ArtSection className="chapter chapter-products" aria-labelledby="ch-products" art={<>
      <MarginArtwork asset={ART.weaveMacro} className="products-weave" />
      <MarginArtwork asset={ART.weaveStrip} className="products-weave-strip" />
      <MarginArtwork asset={ART.lotusBotanical01} className="products-lotus" />
    </>}>
      <div className="container container-narrow">
        <header className="chapter-head chapter-head-wide">
          <ChapterNo n="03" />
          <h2 id="ch-products" className="chapter-title">Đồ Việt, gần mình</h2>
          <p className="chapter-lede">Những món đồ thân thuộc, dễ đưa vào cuộc sống hằng ngày.</p>
        </header>
        {error && <ErrorBox message={`Chưa tải được sản phẩm. ${error}`} onRetry={onRetry} />}
        {!error && !items && <GridSkeleton count={8} />}
        {items && (total === 0 ? (
          <Notice>
            Catalog chưa có sản phẩm được duyệt. Xem hướng dẫn nhập liệu trong <code>docs/huong-dan-nhap-lieu.md</code>.
          </Notice>
        ) : (
          <>
            <ProductGrid items={items} />
            {total > items.length && (
              <p className="chapter-more">
                <a className="btn" href={href("/search")}>
                  Xem tất cả {total} sản phẩm <Icon name="arrow" size={18} />
                </a>
              </p>
            )}
          </>
        ))}
      </div>
    </ArtSection>
  );
}

/** 04 — theo dấu bàn tay: ảnh minh họa có nhãn, dẫn sang làng nghề với tên/số lượng thật. */
function CraftChapter({ places }: { places: Place[] | null }) {
  return (
    <ArtSection className="chapter chapter-craft" aria-labelledby="ch-craft" reveal
      art={<MarginArtwork asset={ART.textileEdge} className="craft-textile" />}>
      <div className="craft-grid">
        <EditorialPhoto asset={ART.craftHands} className="craft-hands"
          caption="Minh họa bằng AI về thao tác đan — không phải ảnh tư liệu của một làng nghề cụ thể." />
        <div className="craft-copy">
          <ChapterNo n="04" />
          <h2 id="ch-craft" className="chapter-title">Theo dấu bàn tay</h2>
          <p>
            Mỗi món đồ là kết tinh của thời gian, kiên nhẫn và đôi bàn tay người thợ. Xem sản phẩm theo làng nghề và
            nơi sản xuất đã có trong catalog.
          </p>
          {places && places.length > 0 && (
            <ul className="craft-places">
              {places.map((p) => (
                <li key={p.id}>
                  <a href={href("/search", { place: p.id })}>
                    <span>{p.name}</span><small>{p.count} sản phẩm</small>
                  </a>
                </li>
              ))}
            </ul>
          )}
          <a className="text-link" href="#/places">Khám phá làng nghề <Icon name="arrow" size={18} /></a>
        </div>
        <EditorialPhoto asset={ART.craftWorkbench} className="craft-bench" caption="Góc bàn nghề — minh họa." />
      </div>
    </ArtSection>
  );
}
