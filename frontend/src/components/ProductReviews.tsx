import { useEffect, useState } from "react";
import { ApiError, assistantApi, type ReviewSummary } from "../api";

/** Đánh giá đã duyệt của sản phẩm + form gửi đánh giá (hiển thị sau khi được duyệt). Không có thì nói không có. */
export function ProductReviews({ productId }: { productId: string }) {
  const [data, setData] = useState<ReviewSummary | null>(null);
  const [failed, setFailed] = useState(false);
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let alive = true;
    setData(null);
    setFailed(false);
    setSent(null);
    assistantApi.reviews(productId).then((r) => alive && setData(r)).catch(() => alive && setFailed(true));
    return () => { alive = false; };
  }, [productId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      const r = await assistantApi.addReview(productId, { rating, body_vi: body.trim() });
      setSent(r.message);
      setBody("");
      if (r.status === "approved") setData(await assistantApi.reviews(productId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không gửi được đánh giá.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="reviews-section">
      <h2 tabIndex={-1}>Đánh giá của khách hàng</h2>
      {!data && !failed && <p className="state-line" role="status"><span className="spinner" aria-hidden /> Đang tải đánh giá…</p>}
      {failed && <p className="muted">Chưa tải được đánh giá.</p>}
      {data && data.count === 0 && <p className="muted">{data.note_vi}</p>}
      {data && data.count > 0 && (
        <>
          <p className="review-summary">
            <span className="stars" aria-hidden="true">★</span> <b>{data.average?.toFixed(1).replace(".", ",")}</b> / 5 từ {data.count} đánh giá.{" "}
            <span className="muted small">{data.note_vi}</span>
          </p>
          <ul className="reviews">
            {data.excerpts.map((x) => (
              <li key={x.review_id}>
                <span className="stars" aria-label={`${x.rating ?? 0} trên 5 sao`}>{"★".repeat(x.rating ?? 0)}</span>
                <p>{x.text}</p>
                <span className="muted small">{x.created_at}{x.verified_purchase ? ", đã mua" : ", chưa xác minh mua hàng"}
                  {x.source_url && <> · <a href={x.source_url} target="_blank" rel="noopener noreferrer">nguồn</a></>}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <details className="review-form">
        <summary>Viết đánh giá</summary>
        {sent ? <p className="notice notice-info" role="status">{sent}</p> : (
          <form onSubmit={submit}>
            <label className="field-inline">Số sao
              <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
                {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} ★</option>)}
              </select>
            </label>
            <textarea rows={3} minLength={10} maxLength={2000} required value={body} onChange={(e) => setBody(e.target.value)}
              placeholder="Chia sẻ trải nghiệm thật của bạn với sản phẩm (ít nhất 10 ký tự)" aria-label="Nội dung đánh giá" />
            {error && <p className="field-error" role="alert">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={body.trim().length < 10 || sending}>
              {sending ? "Đang gửi…" : "Gửi đánh giá"}
            </button>
            <p className="muted small">Đánh giá được hiển thị sau khi duyệt.</p>
          </form>
        )}
      </details>
    </section>
  );
}
