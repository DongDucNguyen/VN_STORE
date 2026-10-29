import sys, json, os
sys.path.insert(0, ".")
from PIL import Image
from app.catalog.store import load_snapshot
from app.catalog.validation import REPO_ROOT
from app.search.engine import SearchEngine
OUT = sys.argv[1]
os.makedirs(OUT + "/img", exist_ok=True)
db = json.load(open(REPO_ROOT / "database.json"))
byid = {p["id"]: p for p in db["products"]}
e = SearchEngine(load_snapshot(REPO_ROOT / "database.json"))
def img_of(pid):
    p = byid[pid]
    for im in p.get("images", []):
        lp = im.get("local_path")
        if lp and (REPO_ROOT / lp).exists():
            dst = f"img/{pid}.jpg"
            if not os.path.exists(OUT + "/" + dst):
                I0 = Image.open(REPO_ROOT / lp).convert("RGBA"); I = Image.new("RGB", I0.size, (255,255,255)); I.paste(I0, mask=I0.split()[3]); I.thumbnail((900, 900)); I.save(OUT + "/" + dst, quality=90)
            return dst
    return None
def card(r):
    pid = r["id"]; pr = r.get("price") or {}
    return {"id": pid, "name": r["name_vi"], "brand": (r.get("brand") or {}).get("name"), "price": pr.get("min_vnd"), "img": img_of(pid)}
data = {}
for key, q, n in [("khan", "khăn lụa tầm 1tr5", 1), ("silk", "silk scarf", 6), ("bamboo", "bamboo basket", 4),
                  ("ao", "áo dài lụa", 4), ("tui", "túi đan", 10), ("luc", "lục bình", 10), ("vase", "bình hoa sen", 8),
                  ("may", "giỏ mây không lấy tre", 4), ("binh", "binh hoa duoi 5 trieu", 4), ("gift", "quà tặng hộp sô cô la", 8)]:
    r = e.search(q, limit=n)
    data[key] = [card(x) for x in r["results"]]
for k, v in data.items():
    print(k); [print("   ", c["name"][:60], c["price"], c["img"]) for c in v]
json.dump(data, open(OUT + "/data.json", "w"), ensure_ascii=False, indent=1)
