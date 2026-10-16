import { useEffect, useState } from "react";
import { ApiError, assistantApi, type AssistantMe, type ConsentLevel } from "../api";
import { ErrorBox, Loading } from "../components/common";
import { formatDate } from "../format";

/** Khách xem/sửa/xóa những gì trợ lý lưu, đổi mức đồng ý, xuất hoặc xóa toàn bộ dữ liệu. */
export function AssistantMemoryPage() {
  const [me, setMe] = useState<AssistantMe | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: number; label: string } | null>(null);
  const [exported, setExported] = useState<string | null>(null);
  const [confirmAll, setConfirmAll] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = () => {
    setError(null);
    assistantApi.me().then(setMe).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  };
  useEffect(load, []);

  const act = async (f: () => Promise<unknown>, msg?: string) => {
    try { await f(); if (msg) setNotice(msg); load(); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
  };

  if (error) return <div className="page"><ErrorBox message={error} onRetry={load} /></div>;
  if (!me) return <div className="page"><Loading /></div>;

  return (
    <div className="page memory-page">
      <h1>Trợ lý ghi nhớ gì về bạn</h1>
      {notice && <p className="notice notice-info" role="status">{notice}</p>}
      <section>
        <h2>Lưu dữ liệu</h2>
        {(["none", "history", "memory"] as ConsentLevel[]).map((l) => (
          <label key={l} className="check">
            <input type="radio" name="consent" checked={me.consent_level === l}
              onChange={() => act(() => assistantApi.setConsent(l), "Đã cập nhật lựa chọn.")} />
            <span>{me.consent_options[l]}</span>
          </label>
        ))}
        <p className="small muted">Hạ mức lưu sẽ xóa ngay phần dữ liệu vượt mức mới.</p>
      </section>

      <section>
        <h2>Sở thích đã ghi nhớ</h2>
        {me.facts.length === 0 ? <p className="muted">Chưa ghi nhớ gì.</p> : (
          <ul className="facts">
            {me.facts.map((f) => (
              <li key={f.id}>
                <span className="muted">{f.kind_label}:</span>{" "}
                {editing?.id === f.id ? (
                  <form className="inline-form" onSubmit={(e) => { e.preventDefault();
                    act(() => assistantApi.editFact(f.id, editing.label)); setEditing(null); }}>
                    <input value={editing.label} maxLength={120} aria-label="Sửa mục ghi nhớ"
                      onChange={(e) => setEditing({ id: f.id, label: e.target.value })} />
                    <button className="btn" type="submit">Lưu</button>
                    <button className="link" type="button" onClick={() => setEditing(null)}>Hủy</button>
                  </form>
                ) : (
                  <>
                    <strong>{f.label_vi}</strong>
                    <span className="small muted"> · ghi nhận {formatDate(f.last_confirmed_at)}
                      {f.expires_at && <>, tự xóa sau {formatDate(f.expires_at)}</>}</span>{" "}
                    <button className="link" onClick={() => setEditing({ id: f.id, label: f.label_vi })}>Sửa</button>{" "}
                    <button className="link" onClick={() => act(() => assistantApi.deleteFact(f.id))}>Xóa</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Các cuộc trò chuyện đã lưu</h2>
        {me.sessions.length === 0 ? <p className="muted">Không có cuộc trò chuyện nào được lưu.</p> : (
          <ul className="facts">
            {me.sessions.map((s) => (
              <li key={s.id}>
                <strong>{formatDate(s.started_at)}</strong> — {s.summary_vi || s.first_message || "(trống)"}{" "}
                <button className="link" onClick={() => act(() => assistantApi.deleteSession(s.id))}>Xóa</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2>Dữ liệu của bạn</h2>
        <p>
          <button className="btn" onClick={() => assistantApi.exportMe().then((d) => setExported(JSON.stringify(d, null, 2)))
            .catch(() => setError("Không xuất được dữ liệu."))}>Xem toàn bộ dữ liệu (JSON)</button>{" "}
          {!confirmAll ? (
            <button className="btn" onClick={() => setConfirmAll(true)}>Xóa mọi thứ trợ lý biết về tôi</button>
          ) : (
            <span className="confirm">
              Xóa vĩnh viễn lịch sử trò chuyện và sở thích? Đánh giá sản phẩm bạn đã gửi được giữ lại ở dạng
              ẩn danh, không còn liên kết với bạn.{" "}
              <button className="btn btn-primary" onClick={() => { setConfirmAll(false);
                act(() => assistantApi.deleteMe(), "Đã xóa toàn bộ dữ liệu của bạn."); }}>Xóa vĩnh viễn</button>{" "}
              <button className="link" onClick={() => setConfirmAll(false)}>Hủy</button>
            </span>
          )}
        </p>
        {exported && <pre className="export">{exported}</pre>}
      </section>
    </div>
  );
}
