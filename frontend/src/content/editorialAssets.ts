// Manifest ảnh biên tập/trang trí (design.md §8). File nằm trong public/brand, sinh bởi
// scripts/design/build_brand_assets.py từ bộ master assets/design-elements/nep-viet-v2.
// Tất cả là minh họa tạo bằng AI: không phải ảnh sản phẩm, ảnh tư liệu làng nghề hay chứng cứ nguồn gốc.

export type Placement =
  | "opening-margin" | "chapter-edge" | "midpage-scene" | "content-gutter" | "footer-scene" | "editorial-story"
  | "category-card";

export interface EditorialAsset {
  src: string;
  width: number;
  height: number;
  /** "" cho ảnh trang trí; ảnh biên tập ghi rõ là minh họa. */
  alt: string;
  role: "decoration" | "illustrative-editorial";
  placement: Placement;
  rights: string;
}

const AI = "Minh họa tạo bằng AI cho VNStore; không phải ảnh tư liệu hay ảnh sản phẩm trong catalog";

const asset = (file: string, width: number, height: number, placement: Placement, alt = ""): EditorialAsset => ({
  src: `/brand/${file}.webp`, width, height, alt, placement, rights: AI,
  role: alt ? "illustrative-editorial" : "decoration",
});

export const ART = {
  bambooBranch: asset("bamboo-branch", 480, 720, "opening-margin"),
  bambooShadow: asset("bamboo-shadow", 820, 547, "opening-margin"),
  ceramic: asset("ceramic-still-life", 340, 363, "opening-margin"),
  nonLa: asset("non-la", 720, 480, "chapter-edge"),
  textileEdge: asset("textile-edge", 360, 540, "chapter-edge"),
  lotusBotanical01: asset("lotus-botanical-01", 360, 540, "content-gutter"),
  lotusBotanical02: asset("lotus-botanical-02", 560, 373, "content-gutter"),
  weaveMacro: asset("weave-macro", 300, 450, "content-gutter"),
  weaveStrip: asset("weave-strip", 900, 243, "content-gutter"),
  lotusMidpage: asset("lotus-midpage", 2172, 724, "midpage-scene"),
  lotusMidpageMd: asset("lotus-midpage-md", 1280, 427, "midpage-scene"),
  lotusMidpageMobile: asset("lotus-midpage-mobile", 820, 1025, "midpage-scene"),
  footerLandscape: asset("footer-landscape", 2172, 724, "footer-scene"),
  footerLandscapeSm: asset("footer-landscape-sm", 1100, 367, "footer-scene"),
  craftHands: asset("craft-hands", 1100, 825, "editorial-story", "Đôi bàn tay đang đan nan tre — minh họa AI"),
  craftWorkbench: asset("craft-workbench", 760, 570, "editorial-story", "Góc bàn làm nghề với dụng cụ và nan đan — minh họa AI"),
} as const;

/** Ảnh minh họa cho năm danh mục gốc, theo id ổn định của catalog. Danh mục khác dùng thẻ chữ. */
export const CATEGORY_ART: Record<string, { short: string; image: EditorialAsset }> = {
  "gom-su": { short: "Gốm sứ", image: asset("category-ceramics", 640, 640, "category-card", "Bộ ấm chén gốm — minh họa AI") },
  "may-tre-coi": { short: "Mây tre đan", image: asset("category-weaving", 640, 640, "category-card", "Túi và khay đan — minh họa AI") },
  "det-may": { short: "Dệt may", image: asset("category-textiles", 640, 640, "category-card", "Vải lụa gấp — minh họa AI") },
  "go-son-mai": { short: "Gỗ & sơn mài", image: asset("category-wood-lacquer", 640, 640, "category-card", "Hộp và bát sơn mài — minh họa AI") },
  "thuc-pham": { short: "Đặc sản", image: asset("category-specialties", 640, 640, "category-card", "Đặc sản đóng gói — minh họa AI") },
};
