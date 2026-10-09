import { cards, cardTitles, expect, test } from "./fixtures";

test.describe("Duyệt catalog", () => {
  test("trang chủ: banner fixture, danh mục, sản phẩm", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/VNStore/);
    await expect(page.getByRole("note").filter({ hasText: "FIXTURE" })).toBeVisible();
    await expect(page.locator("a.cat")).toHaveCount(5);
    await expect(cards(page)).toHaveCount(12);
    // Bản nháp không bao giờ hiển thị.
    await expect(cardTitles(page).filter({ hasText: "bản nháp" })).toHaveCount(0);
    await expect(page.getByText(/Catalog fixture-001/)).toBeVisible();
  });

  test("giá chưa biết hiện Liên hệ, không hiện 0đ", async ({ page }) => {
    await page.goto("/");
    const card = cards(page).filter({ hasText: "Túi cói hộp nắp gỗ" });
    await expect(card.locator(".card-price")).toHaveText("Liên hệ");
    await expect(page.getByText(/^0đ$/)).toHaveCount(0);
  });

  test("chi tiết sản phẩm: thuộc tính, biến thể, nguồn gốc có căn cứ", async ({ page }) => {
    await page.goto("/");
    await cards(page).filter({ hasText: "Bình gốm men lam vẽ sen" }).getByRole("link").click();
    await expect(page).toHaveURL(/#\/p\/fx-binh-gom-men-lam/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Bình gốm men lam vẽ sen");
    await expect(page.locator(".price")).toHaveText("450.000đ – 520.000đ");
    await expect(page.getByRole("navigation", { name: "Danh mục" })).toContainText("Gốm sứ");

    const badges = page.getByRole("list", { name: "Căn cứ nguồn gốc" }).first();
    await expect(badges).toContainText("Sản xuất tại Việt Nam");
    await expect(badges).toContainText("Làng nghề");

    const variants = page.getByRole("table").first();
    await expect(variants.getByRole("row")).toHaveCount(3);
    await expect(variants).toContainText("FX-FX-BINH-GOM-MEN-LAM-1");

    const origin = page.getByRole("table").nth(1);
    await expect(origin).toContainText("Nhà sản xuất công bố");
    await expect(origin.getByRole("link").first()).toHaveAttribute("href", /example\.invalid/);
    await expect(page.getByRole("heading", { name: "Sản phẩm tương tự" })).toBeVisible();
  });

  test("claim 'unknown' hiện Chưa rõ và không thành nhãn", async ({ page }) => {
    await page.goto("/#/p/fx-khan-lua-do");
    const origin = page.getByRole("table").nth(1);
    const row = origin.getByRole("row").filter({ hasText: "Thủ công/truyền thống" });
    await expect(row).toContainText("Chưa rõ");
    await expect(page.getByRole("list", { name: "Căn cứ nguồn gốc" }).first()).not.toContainText("Thủ công");
  });

  test("gallery đổi ảnh khi bấm thumbnail", async ({ page }) => {
    await page.goto("/#/p/fx-tui-coi-quai-da");
    const main = page.locator(".gallery-main img");
    await expect(main).toHaveAttribute("src", /img-fx-tui-coi-quai-da-1/);
    await page.locator(".thumbs button").nth(1).click();
    await expect(main).toHaveAttribute("src", /img-fx-tui-coi-quai-da-2/);
    // Ảnh tải được thật (không vỡ ảnh).
    await expect.poll(() => main.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  });

  test("sản phẩm draft hoặc không tồn tại báo không tìm thấy", async ({ page, allowConsoleErrors }) => {
    allowConsoleErrors(); // trình duyệt log 404 của API
    await page.goto("/#/p/fx-ban-nhap");
    await expect(page.getByRole("alert")).toContainText("Không tìm thấy sản phẩm");
    await page.goto("/#/khong-co-trang");
    await expect(page.getByText("Không tìm thấy trang.")).toBeVisible();
  });

  test("làng nghề và thương hiệu dẫn tới kết quả đã lọc", async ({ page }) => {
    await page.goto("/#/places");
    await expect(page.locator(".entry-list li")).toHaveCount(3);
    await page.getByRole("link", { name: /Kim Sơn/ }).click();
    await expect(page).toHaveURL(/place=lang-coi-kim-son/);
    await expect(cards(page)).toHaveCount(3);

    await page.goto("/#/brands");
    await page.getByRole("link", { name: /Mẫu A Ceramics/ }).click();
    await expect(page).toHaveURL(/brand=brand-fx-a/);
    await expect(cards(page)).toHaveCount(3);
  });

  test("yêu thích lưu trên thiết bị, còn sau khi tải lại", async ({ page }) => {
    await page.goto("/");
    const card = cards(page).filter({ hasText: "Giỏ mây có quai xách" });
    await card.getByRole("button", { name: "Yêu thích" }).click();
    await expect(card.getByRole("button", { name: "Bỏ yêu thích" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("link", { name: "Yêu thích (1)" })).toBeVisible();

    await page.reload();
    await page.getByRole("link", { name: "Yêu thích (1)" }).click();
    await expect(cardTitles(page)).toHaveText(["Giỏ mây có quai xách"]);

    await cards(page).first().getByRole("button", { name: "Bỏ yêu thích" }).click();
    await expect(page.getByText("Chưa có sản phẩm yêu thích.")).toBeVisible();
  });
});

test.describe("Bố cục", () => {
  for (const path of ["/", "/#/search?q=t%C3%BAi%20c%C3%B3i", "/#/p/fx-binh-gom-men-lam", "/#/places"]) {
    test(`không cuộn ngang: ${decodeURIComponent(path)}`, async ({ page }) => {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });
  }
});
