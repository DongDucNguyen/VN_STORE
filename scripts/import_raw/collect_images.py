"""Download catalog source images with page evidence; never infer usage rights.

Run with Python + httpx, beautifulsoup4, Pillow. Writes a manifest, page snapshots,
and original image bytes. Does not publish products or change database.json.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "data_collection" / "images" / "2026-10-10"
STAMP = lambda: datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def collect(product, sources):
    page_url = sources[product["source_ids"][0]]["url"]
    out = {"product_id": product["id"], "name_vi": product["name_vi"],
           "source_page": page_url, "skus": [v["sku"] for v in product["variants"]],
           "retrieved_at": STAMP(), "images": []}
    with httpx.Client(timeout=40, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (compatible; VNStoreCatalogReview/1.0)"}) as client:
        try:
            response = client.get(page_url)
            response.raise_for_status()
            page = response.text
            soup = BeautifulSoup(page, "html.parser")
            dest = BATCH / "pages" / (product["id"] + ".html")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(response.content)
            out.update(page_status=response.status_code, final_page_url=str(response.url),
                       page_path=dest.relative_to(ROOT).as_posix(), page_sha256=digest(response.content),
                       page_title=soup.title.get_text(" ", strip=True) if soup.title else None,
                       headings=[h.get_text(" ", strip=True) for h in soup.select("h1")],
                       sku_on_page={sku: sku.lower() in page.lower() for sku in out["skus"]})
        except Exception as exc:
            out["page_error"] = str(exc)
            page = ""
        for img in product["images"]:
            url = img["source_url"]
            name = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
            shared = name == "80g_bar_front_Bk_shadow_new.jpg"
            record = {"image_id": img["id"], "source_url": url,
                      "filename_on_page": name.lower() in unquote(page).lower(),
                      "shared_generic": shared, "usage_rights_status": img["usage_rights"]["status"]}
            try:
                response = client.get(url, headers={"Referer": page_url})
                response.raise_for_status()
                data = response.content
                with Image.open(io.BytesIO(data)) as im:
                    fmt, size = im.format, im.size
                    im.verify()
                with Image.open(io.BytesIO(data)) as im:
                    im.load()
                ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[fmt]
                dest = ROOT / "assets" / "products" / product["id"] / (img["id"] + ext)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                record.update(status="downloaded", local_path=dest.relative_to(ROOT).as_posix(),
                              sha256=digest(data), bytes=len(data), width=size[0], height=size[1],
                              format=fmt, content_type=response.headers.get("content-type"),
                              final_url=str(response.url), downloaded_at=STAMP())
            except Exception as exc:
                record.update(status="failed", error=str(exc))
            out["images"].append(record)
    print(product["id"], out.get("page_status", "PAGE ERROR"),
          [(i["status"], i["filename_on_page"]) for i in out["images"]], flush=True)
    return out


def contact_sheets(records):
    images = [(p, i) for p in records for i in p["images"] if i["status"] == "downloaded"]
    folder = ROOT / "artifacts" / "image_review" / "2026-10-10"
    folder.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(images), 12):
        sheet = Image.new("RGB", (1440, 1160), "#ededed")
        draw = ImageDraw.Draw(sheet)
        for n, (p, i) in enumerate(images[start:start+12]):
            x, y = n % 4 * 360, n // 4 * 386
            with Image.open(ROOT / i["local_path"]) as original:
                thumb = ImageOps.contain(original.convert("RGBA"), (340, 320))
                sheet.paste(thumb, (x + (360-thumb.width)//2, y), thumb)
            label = i["image_id"].removeprefix("img-")
            draw.text((x+8, y+326), label[:46], fill="black")
            draw.text((x+8, y+342), label[46:], fill="black")
            draw.text((x+8, y+358), f"{i['width']}x{i['height']}  shared={i['shared_generic']}", fill="black")
        sheet.save(folder / f"contact-{start//12+1:02d}.jpg", quality=90)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if (BATCH / "manifest.json").exists():
        raise SystemExit("Batch already exists. Use a new batch directory; do not overwrite reviewed evidence.")
    catalog_bytes = (ROOT / "database.json").read_bytes()
    catalog = json.loads(catalog_bytes)
    BATCH.mkdir(parents=True, exist_ok=True)
    backup = BATCH / "database.before.json"
    if not backup.exists():
        backup.write_bytes(catalog_bytes)
    sources = {s["id"]: s for s in catalog["sources"]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda p: collect(p, sources), catalog["products"]))
    manifest = {"batch": "2026-10-10-official-images", "retrieved_at": STAMP(),
                "catalog_sha256_before": digest(catalog_bytes),
                "method": "Direct HTTPS from official product pages and their image CDNs; web fallback explicitly authorized by user because Browser was disconnected.",
                "products": records}
    (BATCH / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    contact_sheets(records)
    imgs = [i for p in records for i in p["images"]]
    print(json.dumps({"products": len(records), "downloaded": sum(i["status"] == "downloaded" for i in imgs),
                      "total": len(imgs), "page_verified": sum(i["filename_on_page"] for i in imgs)}))


if __name__ == "__main__":
    main()
