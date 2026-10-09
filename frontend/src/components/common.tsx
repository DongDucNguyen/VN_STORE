import type { Badge } from "../api";

export function Loading({ label = "Đang tải…" }: { label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state state-error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Thử lại
        </button>
      )}
    </div>
  );
}

export function Notice({ children, tone = "info" }: { children: React.ReactNode; tone?: "info" | "warn" }) {
  return <div className={`notice notice-${tone}`}>{children}</div>;
}

export function OriginBadges({ badges, compact = false }: { badges: Badge[]; compact?: boolean }) {
  if (!badges.length) return null;
  return (
    <ul className={`badges ${compact ? "badges-compact" : ""}`} aria-label="Căn cứ nguồn gốc">
      {badges.map((b) => (
        <li key={b.claim_type} className="badge" title={`${b.label} — ${b.status_label}`}>
          {b.label}
        </li>
      ))}
    </ul>
  );
}
