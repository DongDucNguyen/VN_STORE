import type { Price } from "./api";

const vnd = new Intl.NumberFormat("vi-VN");

export function formatVnd(v: number): string {
  return `${vnd.format(v)}đ`;
}

/** Giá chưa biết hiển thị "Liên hệ", không bao giờ hiển thị 0. */
export function formatPrice(p: Price): string {
  if (p.min_vnd == null) return "Liên hệ";
  if (p.max_vnd != null && p.max_vnd !== p.min_vnd) return `${formatVnd(p.min_vnd)} – ${formatVnd(p.max_vnd)}`;
  return formatVnd(p.min_vnd);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("vi-VN");
}
