"""Chạy toàn bộ kiểm thử tự động của VNStore bằng một lệnh.

    .venv/Scripts/python scripts/run_all_tests.py            # tất cả
    .venv/Scripts/python scripts/run_all_tests.py --skip-e2e # bỏ test trình duyệt

Các bước: validate catalog thật + fixture → fixture khớp generator → pytest backend
→ test giải mã ảnh (Pillow, chỉ khi có .venv-ml; không có thì BỎ QUA)
→ typecheck + build frontend → Playwright E2E (desktop + mobile, dữ liệu fixture).
Mã thoát khác 0 nếu có bước thất bại.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
NPX = shutil.which("npx") or "npx"
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "catalog.fixture.json"
# Môi trường ML riêng (backend/requirements-ml.txt) có Pillow; .venv của API thì không.
ML_PY = ROOT / ".venv-ml" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def check_fixture_in_sync() -> int:
    """Fixture đã commit phải đúng bằng đầu ra của make_fixture.py (không sửa tay)."""
    sys.path.insert(0, str(FIXTURE.parent))
    import make_fixture  # noqa: PLC0415

    expected = make_fixture.build()
    actual = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if expected != actual:
        print("catalog.fixture.json lệch với make_fixture.py — chạy lại make_fixture.py")
        return 1
    print("catalog.fixture.json khớp make_fixture.py")
    return 0


STEPS: list[tuple[str, list[str] | None, Path, bool]] = [
    # (tên, lệnh hoặc None = hàm Python, thư mục, là E2E)
    ("Validate database.json", [PY, "scripts/validate_catalog/validate.py", "--no-report"], ROOT, False),
    ("Validate fixture", [PY, "scripts/validate_catalog/validate.py", "--no-report",
                          "--catalog", str(FIXTURE)], ROOT, False),
    ("Fixture khớp generator", None, ROOT, False),
    ("Backend pytest", [PY, "-m", "pytest", "-q"], ROOT / "backend", False),
    ("Giải mã ảnh (Pillow, .venv-ml)", [str(ML_PY), "-X", "utf8", "-m", "unittest", "discover", "-s",
                                         "scripts/benchmark/tests", "-p", "test_image_pixels.py"], ROOT, False),
    ("Frontend typecheck", [NPX, "tsc", "-b"], ROOT / "frontend", False),
    ("Frontend build", [NPX, "vite", "build", "--outDir", str(ROOT / "artifacts" / "build"), "--emptyOutDir"],
     ROOT / "frontend", False),
    ("E2E Playwright", [NPX, "playwright", "test", "--reporter=line"], ROOT / "frontend", True),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-e2e", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    results = []
    for name, cmd, cwd, e2e in STEPS:
        if (e2e and args.skip_e2e) or (cmd and cmd[0] == str(ML_PY) and not ML_PY.exists()):
            results.append((name, "BỎ QUA", 0.0))
            continue
        print(f"\n=== {name} ===", flush=True)
        t = time.perf_counter()
        code = check_fixture_in_sync() if cmd is None else subprocess.run(cmd, cwd=cwd).returncode
        results.append((name, "ĐẠT" if code == 0 else f"LỖI ({code})", time.perf_counter() - t))

    print("\n=== Tổng kết ===")
    for name, status, secs in results:
        print(f"{status:<10} {secs:6.1f}s  {name}")
    failed = [r for r in results if r[1].startswith("LỖI")]
    print(f"\n{'TẤT CẢ ĐẠT' if not failed else f'{len(failed)} BƯỚC LỖI'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
