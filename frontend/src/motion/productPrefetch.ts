// Tải trước chi tiết sản phẩm khi người dùng rê chuột/chạm vào thẻ, để chuyển cảnh sang trang chi tiết liền mạch.
// Bộ nhớ ngắn hạn trong tab; lỗi không được giữ lại, lần sau tải lại bình thường.
import { api, type ProductDetail } from "../api";

const TTL_MS = 60_000;
const cache = new Map<string, { at: number; promise: Promise<ProductDetail> }>();

export function loadProduct(id: string): Promise<ProductDetail> {
  const hit = cache.get(id);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.promise;
  const promise = api.product(id);
  cache.set(id, { at: Date.now(), promise });
  promise.catch(() => cache.delete(id));
  return promise;
}

export function prefetchProduct(id: string) {
  loadProduct(id).catch(() => {});
}
