import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok"
    assert r["catalog"]["version"] == "fixture-001"
    assert r["catalog"]["products_visible"] == 12
    assert r["search"]["voice"] == "unavailable"


def test_products_list_and_filters(client):
    r = client.get("/products", params={"category_id": "gom-su"}).json()
    assert r["total"] == 3
    assert all(x["category"]["id"].startswith("gom-su") for x in r["results"])
    r = client.get("/products", params={"place_id": "lang-coi-kim-son"}).json()
    assert r["total"] == 3


def test_product_detail_by_id_and_slug(client):
    a = client.get("/products/fx-tui-coi-quai-da").json()
    assert a["name_vi"] == "Túi cói quai da"
    assert {b["claim_type"] for b in a["origin_badges"]} == {"made_in_vn", "craft_village", "vn_material"}
    assert a["sources"] and a["category_path"][0]["id"] == "may-tre-coi"
    assert a["images"][0]["url"].startswith("/images/")


def test_product_404_and_draft_hidden(client):
    assert client.get("/products/khong-co").status_code == 404
    assert client.get("/products/fx-ban-nhap").status_code == 404


def test_unknown_price_badge_not_shown_as_zero(client):
    a = client.get("/products/fx-tui-coi-lien-he").json()
    assert a["price"]["min_vnd"] is None and a["price"]["has_unknown"]


def test_unknown_claim_not_badged(client):
    a = client.get("/products/fx-khan-lua-do").json()
    assert "traditional_craft" not in {b["claim_type"] for b in a["origin_badges"]}


def test_similar(client):
    r = client.get("/products/fx-tui-coi-quai-da/similar").json()
    assert r["results"][0]["category"]["id"] == "may-tre-coi-tui"
    assert all(x["id"] != "fx-tui-coi-quai-da" for x in r["results"])


def test_search_endpoint(client):
    r = client.post("/search", json={"query": "binh gom bat trang duoi 500k"}).json()
    assert r["results"][0]["id"] == "fx-binh-gom-men-lam"
    assert r["applied_filters"][0]["key"] == "price"
    assert "timings_ms" in r


def test_search_validation(client):
    assert client.post("/search", json={"query": "x" * 400}).status_code == 422
    assert client.post("/search", json={"query": "a", "limit": 0}).status_code == 422


def test_voice_and_image_unavailable(client):
    for path in ("/search/voice", "/search/image"):
        r = client.post(path)
        assert r.status_code == 503
        assert r.json()["detail"]["code"] == "model_unavailable"


def test_images(client):
    r = client.get("/images/img-fx-tui-coi-quai-da-1")
    assert r.status_code == 200 and b"<svg" in r.content
    assert client.get("/images/..%2F..%2Fdatabase.json").status_code == 404
    assert client.get("/images/img-fx-ban-nhap-1").status_code == 404


def test_categories_brands_places(client):
    cats = client.get("/categories").json()
    assert {c["id"] for c in cats} == {"gom-su", "may-tre-coi", "det-may", "go-son-mai", "thuc-pham"}
    assert next(c for c in cats if c["id"] == "may-tre-coi")["count"] == 6
    assert len(client.get("/brands").json()) == 2
    assert len(client.get("/places", params={"place_type": "craft_village"}).json()) == 3


def test_suggest_and_facets(client):
    assert client.get("/suggest", params={"q": "son"}).json()
    f = client.get("/facets").json()
    assert f["price"]["unknown"] == 1
