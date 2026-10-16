"""Trợ lý tư vấn sản phẩm (docs/ke-hoach-tro-ly-ai.md).

Luồng một lượt: hiểu yêu cầu (LLM, JSON) → tìm trên catalog bằng SearchEngine với bộ lọc cứng lấy từ lời khách →
viết câu trả lời (LLM, JSON) → kiểm và dựng lại từ snapshot (grounding). Mọi dữ kiện sản phẩm hiển thị lấy từ catalog
hoặc kho đánh giá; LLM chỉ chọn sản phẩm và diễn đạt lý do. Lịch sử và bộ nhớ khách lưu trong SQLite, theo mức đồng ý.
"""
