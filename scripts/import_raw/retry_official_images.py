"""Resolve missing Kilomet109 downloads and Hanoia full-size images from official pages."""
import io
import json
from urllib.parse import unquote, urlsplit
import httpx
from bs4 import BeautifulSoup
from PIL import Image
from collect_images import ROOT, BATCH, STAMP, digest, contact_sheets


def main():
    manifest_path = BATCH / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("review_completed_at"):
        raise SystemExit("Batch already reviewed; create a new batch for further downloads.")
    attempts = []
    with httpx.Client(timeout=40, follow_redirects=True) as client:
        for p in manifest["products"]:
            if "kilomet109" in p["product_id"]:
                slug = urlsplit(p["source_page"]).path.strip("/").split("/")[-1]
                url = "https://www.kilomet109.com/wp-json/wc/store/v1/products?slug=" + slug
                r = client.get(url)
                attempts.append({"url": url, "status": r.status_code})
                if r.status_code == 200:
                    dest = BATCH / "pages" / (p["product_id"] + ".json")
                    dest.write_bytes(r.content)
                    p["api_evidence"] = {"url": url, "path": dest.relative_to(ROOT).as_posix(), "sha256": digest(r.content)}
                    raw = r.json()
                    if len(raw) == 1:
                        p["api_evidence"].update(name=raw[0]["name"], sku=raw[0]["sku"], permalink=raw[0]["permalink"])
                        for img in p["images"]:
                            img["api_image_match"] = any(x["src"] == img["source_url"] for x in raw[0]["images"])
                else:
                    print(p["product_id"], "API", r.status_code, r.text[:90], flush=True)
                for img in p["images"]:
                    if img["status"] != "downloaded":
                        url = img["source_url"]
                        r = client.get(url)
                        attempts.append({"url": url, "status": r.status_code})
                        if r.status_code == 200:
                            save_image(r, img, p)
                        else:
                            print(img["image_id"], r.status_code, flush=True)
            elif "hanoia" in p["product_id"]:
                page = (ROOT / p["page_path"]).read_text(encoding="utf-8")
                soup = BeautifulSoup(page, "html.parser")
                main = soup.select_one("img.gallery-placeholder__image")
                if main and main.get("data-original"):
                    url = main["data-original"]
                    r = client.get(url)
                    attempts.append({"url": url, "status": r.status_code})
                    if r.status_code == 200:
                        img = p["images"][0]
                        old = dict(img)
                        img["source_url"] = url
                        save_image(r, img, p)
                        img["previous_download"] = old
                        img["filename_on_page"] = True
        manifest["retry_attempts"] = attempts
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    contact_sheets(manifest["products"])


def save_image(response, img, p):
    data = response.content
    with Image.open(io.BytesIO(data)) as im:
        fmt, size = im.format, im.size
        im.verify()
    with Image.open(io.BytesIO(data)) as im:
        im.load()
    ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[fmt]
    dest = ROOT / "assets" / "products" / p["product_id"] / (img["image_id"] + ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    if "error" in img:
        img["previous_error"] = img.pop("error")
    img.update(status="downloaded", local_path=dest.relative_to(ROOT).as_posix(), sha256=digest(data),
               bytes=len(data), width=size[0], height=size[1], format=fmt,
               content_type=response.headers.get("content-type"), final_url=str(response.url), downloaded_at=STAMP())
    print(img["image_id"], size, flush=True)


if __name__ == "__main__":
    main()
