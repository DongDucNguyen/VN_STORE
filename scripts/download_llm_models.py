"""Tải các checkpoint LLM ONNX ứng viên cho trợ lý vào cache Hugging Face của dự án (artifacts/hf-cache).

    .venv-ml-gpu/Scripts/python -X utf8 scripts/download_llm_models.py [--only Qwen3_4B_Instruct ...] [--connections 48]

Mạng ở máy demo giới hạn tốc độ theo từng kết nối (~15–40 KB/s mỗi kết nối, đo ngày 15/10/2026), nên tệp lớn được tải
song song nhiều đoạn (HTTP Range), tải tiếp được khi đứt, rồi kiểm SHA-256 với giá trị LFS do Hugging Face công bố cho
đúng revision đã ghim. Tệp đạt được đặt vào `snapshots/<revision>/<đường dẫn>` để `hf_hub_download` (app.ml.hf_file)
dùng lại mà không cần mạng. Tệp nhỏ (config/tokenizer) tải bằng hf_hub_download như thường.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

CHUNK = 8 * 1024 * 1024
SMALL = ("config.json", "generation_config.json", "tokenizer.json", "tokenizer_config.json")
OPTIONAL = ("chat_template.jinja", "chat_template.json", "special_tokens_map.json")


def cache_dir() -> Path:
    return Path(os.environ.get("VNSTORE_HF_CACHE", ROOT / "artifacts" / "hf-cache"))


def snapshot_path(repo: str, revision: str, filename: str) -> Path:
    return cache_dir() / ("models--" + repo.replace("/", "--")) / "snapshots" / revision / filename


def paths_info(repo: str, revision: str, files: list[str]) -> dict[str, dict]:
    body = "&".join(f"paths={urllib.request.quote(f)}" for f in files).encode()
    req = urllib.request.Request(f"https://huggingface.co/api/models/{repo}/paths-info/{revision}", data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {x["path"]: x for x in json.load(r)}


def resolve(repo: str, revision: str, filename: str) -> str:
    """URL CDN đã ký (theo redirect một lần) để mọi đoạn dùng chung."""
    url = f"https://huggingface.co/{repo}/resolve/{revision}/{filename}"

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        opener.open(urllib.request.Request(url, method="HEAD"), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            loc = e.headers["Location"]
            return loc if loc.startswith("http") else "https://huggingface.co" + loc
        raise
    return url


def fetch_parallel(urls: list[tuple[str, int]], size: int, dest: Path) -> None:
    """urls: (URL, số kết nối) — có thể trộn CDN Hugging Face và mirror; nội dung được kiểm SHA-256 sau cùng."""
    part = dest.with_suffix(dest.suffix + ".part")
    state_file = dest.with_suffix(dest.suffix + ".parts.json")
    done: set[int] = set(json.loads(state_file.read_text())) if state_file.exists() and part.exists() else set()
    if not part.exists() or part.stat().st_size != size:
        with open(part, "wb") as f:
            f.truncate(size)
        done = set()
    chunks = [i for i in range((size + CHUNK - 1) // CHUNK) if i not in done]
    lock = threading.Lock()
    progress = {"bytes": len(done) * CHUNK, "t0": time.time(), "last": 0.0}

    def worker(url: str):
        while True:
            with lock:
                if not chunks:
                    return
                idx = chunks.pop(0)
            start, end = idx * CHUNK, min(size, (idx + 1) * CHUNK) - 1
            for attempt in range(30):
                try:
                    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
                    with urllib.request.urlopen(req, timeout=120) as r:
                        data = r.read()
                    if len(data) != end - start + 1:
                        raise IOError(f"short read {len(data)}")
                    with lock:
                        with open(part, "r+b") as f:
                            f.seek(start)
                            f.write(data)
                        done.add(idx)
                        progress["bytes"] += len(data)
                        state_file.write_text(json.dumps(sorted(done)))
                        now = time.time()
                        if now - progress["last"] > 20:
                            progress["last"] = now
                            rate = progress["bytes"] / max(1, now - progress["t0"])
                            print(f"   {dest.name}: {progress['bytes'] / size:5.1%} ~{rate / 1e6:.2f} MB/s", flush=True)
                    break
                except Exception as e:  # noqa: BLE001 — mạng chập chờn: thử lại đoạn này
                    time.sleep(min(30, 2 + attempt * 2))
                    if attempt == 29:
                        raise RuntimeError(f"Không tải được đoạn {idx} của {dest.name}: {e}") from e

    threads = [threading.Thread(target=worker, args=(u,), daemon=True) for u, n in urls for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if len(done) * CHUNK < size - CHUNK:
        raise RuntimeError(f"{dest.name}: thiếu đoạn")
    part.replace(dest)
    state_file.unlink(missing_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(16 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(cls, connections: int, mirror: str | None, mirror_connections: int) -> None:
    from huggingface_hub import hf_hub_download
    repo, rev = cls.repo, cls.revision
    big = [f for f in (cls.decoder_cuda, *cls.data_files_cuda, cls.embed_cuda, *cls.embed_data_cuda) if f]
    print(f"== {cls.__name__} ({repo}@{rev[:12]})", flush=True)
    for name in SMALL:
        hf_hub_download(repo, name, revision=rev, cache_dir=cache_dir())
    for name in OPTIONAL:
        try:
            hf_hub_download(repo, name, revision=rev, cache_dir=cache_dir())
        except Exception:  # noqa: BLE001
            pass
    info = paths_info(repo, rev, big)
    for name in big:
        meta = info[name]
        lfs = meta.get("lfs")
        dest = snapshot_path(repo, rev, name)
        if dest.exists() and dest.stat().st_size == meta["size"]:
            if not lfs or sha256(dest) == lfs["oid"]:
                print(f"   ok (đã có) {name}", flush=True)
                continue
            dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        if meta["size"] < 64 * 1024 * 1024:
            tmp = hf_hub_download(repo, name, revision=rev, cache_dir=cache_dir())
            print(f"   ok {name} ({meta['size'] / 1e6:.1f} MB)", flush=True)
            continue
        t0 = time.time()
        urls = [(resolve(repo, rev, name), connections)]
        if mirror:
            urls.append((f"{mirror.rstrip('/')}/{repo}/resolve/{rev}/{name}", mirror_connections))
        fetch_parallel(urls, meta["size"], dest)
        if lfs and sha256(dest) != lfs["oid"]:
            dest.unlink()
            raise RuntimeError(f"SHA-256 không khớp cho {name}")
        print(f"   ok {name} ({meta['size'] / 1e9:.2f} GB, {time.time() - t0:.0f} s, sha256 khớp)", flush=True)


def main() -> int:
    from app.ml.llm import CANDIDATES
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(CANDIDATES))
    ap.add_argument("--connections", type=int, default=48)
    ap.add_argument("--mirror", default=None, help="vd. https://hf-mirror.com — thêm nguồn song song")
    ap.add_argument("--mirror-connections", type=int, default=24)
    args = ap.parse_args()
    failed = []
    for name in args.only:
        try:
            download(CANDIDATES[name], args.connections, args.mirror, args.mirror_connections)
        except Exception as e:  # noqa: BLE001
            print(f"   LỖI {name}: {type(e).__name__}: {e}", flush=True)
            failed.append(name)
    print("XONG" if not failed else f"XONG, lỗi: {failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
