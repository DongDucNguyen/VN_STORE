import { useEffect, useState } from "react";
import { api, type Health } from "../api";
import { clearMeasurements, measurementCount, recording, setRecording, snapshotMeasurements } from "../measurements";

export function DiagnosticsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");
  const [active, setActive] = useState(recording);
  const [count, setCount] = useState(measurementCount);
  useEffect(() => { api.health().then(setHealth).catch((e) => setError(String(e))); }, []);
  function download() {
    const blob = new Blob([JSON.stringify(snapshotMeasurements(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "vnstore-browser-timings.json"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="page">
    <h1>Chẩn đoán demo</h1>
    <p>Trang dành cho người kiểm thử. Trạng thái model sẵn sàng không có nghĩa model đã được chọn qua benchmark.</p>
    {error && <p role="alert">{error}</p>}
    <p>Catalog: {health?.catalog?.version ?? "—"} · {health?.catalog?.products_visible ?? 0} sản phẩm hiển thị</p>
    <ul>{(["voice", "image"] as const).map((kind) => <li key={kind}>
      {kind}: {health?.search?.[kind] ?? "—"} · {health?.search?.models?.[kind]?.model_id ?? "chưa cấu hình"}
      {health?.search?.models?.[kind]?.reason && ` · ${health.search.models[kind].reason}`}
    </li>)}</ul>
    <h2>Đo độ trễ trên trình duyệt</h2>
    <p>Chỉ bật trong phiên đo. Lưu tối đa 200 lượt thành công trong bộ nhớ tab; tải lại trang sẽ xóa.
      Không lưu câu tìm, bản chép lời, ảnh, âm thanh hoặc danh tính sản phẩm; không gửi số đo về máy chủ.</p>
    <p>Voice tính từ bấm dừng, ảnh từ bấm tìm, keyword từ lúc trang bắt đầu gửi yêu cầu, đến khi kết quả được vẽ;
      không tính thời gian nói hoặc tải ảnh sản phẩm. Phân bố chỉ gồm lượt thành công; lỗi và lượt hủy/bị thay trước
      khi hiện kết quả được đếm riêng theo loại tìm kiếm (chỉ số đếm) và phải báo cùng số đo.
      Đo trên fixture chỉ kiểm tra luồng. Ghi riêng máy, mạng, cold/warm và số lượt khi lập báo cáo.</p>
    <p role="status">{active ? "Đang ghi số đo" : "Đã dừng ghi"} · {count.samples} lượt
      {count.failed > 0 && ` · ${count.failed} lỗi/hủy`}</p>
    <div className="voice-actions">
      <button className="btn" onClick={() => { setRecording(!active); setActive(!active); }}>
        {active ? "Dừng đo" : "Bắt đầu đo"}</button>
      <button className="btn" onClick={download} disabled={!count.samples && !count.failed}>Xuất số đo JSON</button>
      <button className="btn" onClick={() => { clearMeasurements(); setCount(measurementCount()); }}>Xóa số đo</button>
    </div>
    <p><a href="#/">Tìm bằng chữ hoặc giọng nói</a> · <a href="#/image">Tìm bằng ảnh</a></p>
  </div>;
}
