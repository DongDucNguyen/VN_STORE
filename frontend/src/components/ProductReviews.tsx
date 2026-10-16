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
    try {
      const r = await assistantApi.addReview(productId, { rating, body_vi: body.trim() });
      setSent(r.message);
      setBody("");
      if (r.status === "approved") setData(await assistantApi.reviews(productId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không gửi được đánh giá.");
    }
  }

  return (
    <section>
      <h2>Đánh giá của khách hàng</h2>
      {failed && <p className="muted">Chưa tải được đánh giá.</p>}
      {data && data.count === 0 && <p className="muted">{data.note_vi}</p>}
      {data && data.count > 0 && (
        <>
          <p>★ {data.average?.toFixed(1).replace(".", ",")} / 5 từ {data.count} đánh giá. <span className="muted small">{data.note_vi}</span></p>
          <ul className="reviews">
            {data.excerpts.map((x) => (
              <li key={x.review_id}>
                <span>{"★".repeat(x.rating ?? 0)}</span> {x.text}
                <span className="muted small"> — {x.created_at}{x.verified_purchase ? ", đã mua" : ", chưa xác minh mua hàng"}
                  {x.source_url && <> · <a href={x.source_url} target="_blank" rel="noopener noreferrer">nguồn</a></>}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <details className="review-form">
        <summary>Viết đánh giá</summary>
        {sent ? <p className="notice notice-info">{sent}</p> : (
          <form onSubmit={submit}>
            <label className="check">Số sao
              <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
                {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} ★</option>)}
              </select>
            </label>
            <textarea rows={3} minLength={10} maxLength={2000} required value={body} onChange={(e) => setBody(e.target.value)}
              placeholder="Chia sẻ trải nghiệm thật của bạn với sản phẩm (ít nhất 10 ký tự)" aria-label="Nội dung đánh giá" />
            {error && <p className="small state-error">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={body.trim().length < 10}>Gửi đánh giá</button>
          </form>
        )}
      </details>
    </section>
  );
}
