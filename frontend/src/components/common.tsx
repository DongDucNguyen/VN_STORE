import type { ReactNode } from "react";
import type { Badge } from "../api";
import { LotusMark } from "./brand/Motifs";
import { Icon } from "./ui/Icon";

export function Loading({ label = "Đang tải…" }: { label?: string }) {
  return (
    <div className="state state-loading" role="status" aria-live="polite">
      <span className="spinner" aria-hidden /> {label}
    </div>
  );
}

/** Khung chờ đúng kích thước lưới thẻ; một vệt lụa sáng lướt chậm (tắt khi giảm chuyển động). Trạng thái chữ luôn có. */
export function GridSkeleton({ count = 8, label = "Đang tải sản phẩm…" }: { count?: number; label?: string }) {
  return (
    <div className="skeleton-wrap">
      <p className="state-line" role="status"><span className="spinner" aria-hidden /> {label}</p>
      <div className="grid" aria-hidden="true">
        {Array.from({ length: count }, (_, i) => (
          <div key={i} className="skeleton-card" style={{ "--i": i % 4 } as React.CSSProperties}><div className="sk-img" /><div className="sk-line" /><div className="sk-line short" /></div>
        ))}
      </div>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <p><Icon name="alert" /> {message}</p>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          <Icon name="refresh" /> Thử lại
        </button>
      )}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  return (
    <div className={`notice notice-${tone}`}>
      <Icon name={tone === "warn" ? "alert" : "info"} size={18} className="notice-icon" />
      <div>{children}</div>
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <LotusMark size={56} className="empty-art" />
      <p className="empty-title">{title}</p>
      {children && <div className="muted">{children}</div>}
      {action && <div className="empty-action">{action}</div>}
    </div>
  );
}

/** Nhãn nguồn gốc bằng chữ, mức căn cứ đọc được không cần tooltip; không dùng màu như dấu chứng nhận. */
export function OriginBadges({ badges, compact = false }: { badges: Badge[]; compact?: boolean }) {
  if (!badges.length) return null;
  const shown = compact ? badges.slice(0, 2) : badges;
  const more = badges.length - shown.length;
  return (
    <ul className={`badges ${compact ? "badges-compact" : ""}`} aria-label="Căn cứ nguồn gốc">
      {shown.map((b) => (
        <li key={b.claim_type} className="badge" title={`${b.label} — ${b.status_label}`}>
          {b.label}
          {!compact && <span className="badge-status"> · {b.status_label}</span>}
        </li>
      ))}
      {more > 0 && <li className="badge badge-more">+{more}<span className="sr-only"> nhãn khác</span></li>}
    </ul>
  );
}
