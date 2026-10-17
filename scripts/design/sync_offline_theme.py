"""Nhúng theme Nếp Việt vào bốn template duyệt offline (design.md §5.12).

Theme lấy từ scripts/design/offline_theme.css (nguồn duy nhất) và được chèn nội tuyến giữa hai marker
`/* nep-viet-theme:start */` … `/* nep-viet-theme:end */` ở cuối khối <style> đầu tiên, để packet sinh ra
vẫn mở offline. Chạy lại sau khi sửa theme:

    python scripts/design/sync_offline_theme.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = Path(__file__).with_name("offline_theme.css")
START, END = "/* nep-viet-theme:start */", "/* nep-viet-theme:end */"

# Phần riêng: ba template dùng màu nút cố định; trang crop dùng biến riêng (--accent, --card…).
GREEN_BUTTONS = (
    "button{background:var(--nv-primary);border-color:var(--nv-primary);color:var(--nv-on-primary)}"
    "button:hover{background:var(--nv-primary-hover)}"
    "button.tab,button.secondary{background:var(--nv-surface);color:var(--nv-primary);border-color:var(--nv-control)}"
    "button.tab[aria-pressed=true]{background:var(--nv-primary);color:var(--nv-on-primary)}"
    "article.graded,.card.done{border-color:var(--nv-primary);background:color-mix(in srgb,var(--nv-soft) 55%,var(--nv-surface))}"
)
CROP_VARS = (
    ":root{--bg:var(--nv-bg);--card:var(--nv-surface);--text:var(--nv-text);--muted:var(--nv-muted);--line:var(--nv-line);"
    "--accent:var(--nv-primary);--warn:var(--nv-warning);--bad:var(--nv-danger)}"
    "button.primary{color:var(--nv-on-primary)}.instr{border-left-color:var(--nv-straw)}"
)
TEMPLATES = {
    "scripts/benchmark/review_template.html": GREEN_BUTTONS,
    "scripts/benchmark/image_review_template.html": GREEN_BUTTONS,
    "scripts/benchmark/family_review_template.html": GREEN_BUTTONS,
    "scripts/benchmark/crop_review_template.html": CROP_VARS,
}


def main() -> None:
    theme = THEME.read_text(encoding="utf-8").strip()
    for rel, extra in TEMPLATES.items():
        path = ROOT / rel
        html = path.read_text(encoding="utf-8")
        block = f"{START}\n{theme}\n{extra}\n{END}"
        if START in html:
            html = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, html, count=1, flags=re.S)
        else:
            i = html.index("</style>")
            html = html[:i] + "\n" + block + "\n" + html[i:]
        path.write_text(html, encoding="utf-8", newline="")
        print("updated", rel)


if __name__ == "__main__":
    main()
