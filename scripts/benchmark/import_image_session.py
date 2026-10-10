"""Nhập file zip của một phiên chụp (trang #/collect/image) vào benchmarks/image/.

    .venv/Scripts/python scripts/benchmark/import_image_session.py image-c03-20261010t1700.zip [--dry-run]

Chỉ nhận samples.json + raw/<qid>.(jpg|png|webp), kiểm tra SHA-256 từng file và qid chưa có. Sau đó
chạy audit_image_queries.audit() trên manifest đã gộp (schema, catalog hash, rò split theo
họ/phiên/ảnh gốc, trùng gallery, quyền có bằng chứng). Audit `invalid` thì xóa file vừa ghi và giữ
nguyên manifest. Trạng thái `pending_review` là bình thường: judgment và independence_review do người
duyệt điền sau khi nhập.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_image_queries import audit  # noqa: E402

TARGET = ROOT / "benchmarks" / "image" / "manifest.json"
NAME = re.compile(r"^(samples\.json|raw/[a-z0-9][a-z0-9_-]{0,119}\.(jpg|png|webp))$")
MAX_FILES = 500
MAX_BYTES = 25 * 1024 * 1024  # cùng giới hạn của audit


class SessionError(ValueError):
    pass


def read_session(zip_path: Path) -> tuple[list[dict], dict[str, bytes]]:
    with zipfile.ZipFile(zip_path) as z:
        infos = z.infolist()
        if len(infos) > MAX_FILES:
            raise SessionError(f"Zip có {len(infos)} file, vượt {MAX_FILES}")
        bad = [i.filename for i in infos if not NAME.match(i.filename) or i.file_size > MAX_BYTES]
        if bad:
            raise SessionError(f"Zip chứa file không hợp lệ hoặc quá lớn: {bad[:3]}")
        files = {i.filename: z.read(i) for i in infos}
    try:
        samples = json.loads(files.pop("samples.json"))["samples"]
    except (KeyError, json.JSONDecodeError, TypeError) as e:
        raise SessionError("Zip thiếu samples.json hợp lệ") from e
    if not isinstance(samples, list) or not samples:
        raise SessionError("Phiên không có ảnh")
    listed = set()
    for s in samples:
        path = s.get("image_path") if isinstance(s, dict) else None
        if path not in files:
            raise SessionError(f"{s.get('qid') if isinstance(s, dict) else s}: thiếu file {path}")
        if hashlib.sha256(files[path]).hexdigest() != s.get("sha256"):
            raise SessionError(f"{s['qid']}: sha256 không khớp file")
        listed.add(path)
    if set(files) - listed:
        raise SessionError(f"Zip có ảnh không nằm trong samples.json: {sorted(set(files) - listed)[:3]}")
    return samples, files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", type=Path)
    ap.add_argument("--manifest", type=Path, default=TARGET)
    ap.add_argument("--catalog", type=Path, default=ROOT / "database.json")
    ap.add_argument("--families", type=Path, help="registry họ đã duyệt để đối chiếu khi nhập")
    ap.add_argument("--require-families", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    base = args.manifest.parent
    written: list[Path] = []
    tmp: Path | None = None
    try:
        samples, files = read_session(args.zip)
        current = json.loads(args.manifest.read_text(encoding="utf-8"))
        dup = {s["qid"] for s in current["samples"]} & {s["qid"] for s in samples}
        if dup:
            raise SessionError(f"qid đã có trong manifest: {sorted(dup)[:3]}")
        clash = [p for p in files if (base / p).exists()]
        if clash:
            raise SessionError(f"File đã tồn tại trong raw/: {clash[:3]}")
        (base / "raw").mkdir(exist_ok=True)
        for path, data in files.items():
            (base / path).write_bytes(data)
            written.append(base / path)
        fd, name = tempfile.mkstemp(dir=base, prefix=".manifest.", suffix=".json")
        tmp = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({**current, "samples": current["samples"] + samples}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        report = audit(tmp, args.catalog, args.families, args.require_families)
        if report["status"] == "invalid":
            errors = [f"{i['code']} @ {i['path']}: {i['message']}" for i in report["issues"] if i["level"] == "error"]
            raise SessionError("audit invalid — " + "; ".join(errors[:5]))
        print(f"{len(samples)} ảnh, họ {sorted({s['family_id'] for s in samples})}, audit: {report['status']}")
        if args.dry_run:
            print("dry-run: không ghi gì")
            return 0
        os.replace(tmp, args.manifest)
        tmp, written = None, []
        print(f"Đã nhập vào {args.manifest}; người duyệt cần điền judgment và independence_review.")
        return 0
    except (SessionError, zipfile.BadZipFile, OSError, json.JSONDecodeError, KeyError) as e:
        print(f"invalid: {e}", file=sys.stderr)
        return 1
    finally:
        # Dry-run hoặc lỗi: dọn mọi thứ vừa ghi, manifest đích giữ nguyên.
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        for p in written:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
