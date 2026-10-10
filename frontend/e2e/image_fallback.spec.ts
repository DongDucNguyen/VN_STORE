import { cards, expect, test } from "./fixtures";

// Fulfill 200 with non-image bytes to exercise decoding failure without console/network noise.
const invalidImage = { status: 200, contentType: "image/png", body: "invalid image bytes" };

for (const failure of ["http404", "network"] as const) {
  test(`ảnh ${failure}: card báo lỗi, gallery chuyển sang ảnh còn tải được`, async ({ page, allowConsoleErrors, consoleErrors }) => {
    allowConsoleErrors();
    await page.route("**/images/img-fx-tui-coi-quai-da-1", route => failure === "http404"
      ? route.fulfill({ status: 404, body: "Image not found" })
      : route.abort("failed"));
    await page.goto("/");
    const card = cards(page).filter({ hasText: "Túi cói quai da" });
    await card.scrollIntoViewIfNeeded();
    await expect(card.locator(".img-missing")).toHaveText("Ảnh tạm thời không tải được");
    await card.getByRole("link").click();
    const main = page.locator(".gallery-main img");
    await expect(main).toHaveAttribute("src", /img-fx-tui-coi-quai-da-2$/);
    await expect.poll(() => main.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
    await page.goto("about:blank");
    // Only the intentional browser resource failures are allowed; JS errors still fail.
    expect(consoleErrors.length).toBeGreaterThan(0);
    for (const error of consoleErrors) {
      expect(error).toMatch(failure === "http404"
        ? /^console: Failed to load resource: the server responded with a status of 404/
        : /^console: Failed to load resource: net::ERR_FAILED$/);
    }
  });
}

test("ảnh lỗi trên card vẫn cho xem thông tin và mở sản phẩm", async ({ page }) => {
  await page.route("**/images/img-fx-tui-coi-quai-da-1", route => route.fulfill(invalidImage));
  await page.goto("/");
  const card = cards(page).filter({ hasText: "Túi cói quai da" });
  await card.scrollIntoViewIfNeeded();
  await expect(card.locator(".img-missing")).toHaveText("Ảnh tạm thời không tải được");
  await expect(card.locator(".card-img img")).toHaveCount(0);
  await card.getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Túi cói quai da");
  await expect(page.locator(".gallery-main img")).toHaveAttribute("src", /-2$/);
});

test("gallery bỏ ảnh hỏng và hiển thị ảnh kế tiếp tải được", async ({ page }) => {
  await page.route("**/images/img-fx-tui-coi-quai-da-1", route => route.fulfill(invalidImage));
  await page.goto("/#/p/fx-tui-coi-quai-da");
  const main = page.locator(".gallery-main img");
  await expect(main).toHaveAttribute("src", /img-fx-tui-coi-quai-da-2$/);
  await expect.poll(() => main.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  await expect(page.locator(".thumbs")).toHaveCount(0);
});

test("mọi ảnh lỗi có thể tải lại sau khi nguồn phục hồi", async ({ page }) => {
  await page.route("**/images/img-fx-tui-coi-quai-da-*", route => route.fulfill(invalidImage));
  await page.goto("/#/p/fx-tui-coi-quai-da");
  await expect(page.locator(".gallery-main .img-missing")).toContainText("Ảnh tạm thời không tải được");
  await expect(page.locator(".gallery img")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Biến thể", exact: true })).toBeVisible();
  await page.unroute("**/images/img-fx-tui-coi-quai-da-*");
  await page.getByRole("button", { name: "Tải lại ảnh", exact: true }).click();
  const main = page.locator(".gallery-main img");
  await expect.poll(() => main.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  await expect(page.locator(".thumbs button")).toHaveCount(2);
});

test("đổi sản phẩm không giữ lỗi ảnh của trang trước", async ({ page }) => {
  await page.route("**/images/img-fx-tui-coi-quai-da-*", route => route.fulfill(invalidImage));
  await page.goto("/#/p/fx-tui-coi-quai-da");
  await expect(page.getByRole("button", { name: "Tải lại ảnh", exact: true })).toBeVisible();
  await page.evaluate(() => { location.hash = "#/p/fx-binh-gom-men-lam"; });
  const main = page.locator(".gallery-main img");
  await expect(main).toHaveAttribute("src", /img-fx-binh-gom-men-lam-1$/);
  await expect.poll(() => main.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  await expect(page.getByRole("button", { name: "Tải lại ảnh", exact: true })).toHaveCount(0);
});
