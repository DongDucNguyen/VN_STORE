import { expect, test as base, type Page } from "@playwright/test";

// Mọi test tự động thất bại nếu trang có lỗi JS hoặc console.error.
// Test nào cố ý gây lỗi mạng thì gọi allowConsoleErrors().
export const test = base.extend<{ consoleErrors: string[]; allowConsoleErrors: () => void }>({
  consoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = [];
      let allowed = false;
      page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
      page.on("console", (m) => {
        if (m.type() === "error") errors.push(`console: ${m.text()}`);
      });
      (page as Page & { __allow?: () => void }).__allow = () => {
        allowed = true;
      };
      await use(errors);
      if (!allowed) expect(errors, "Trang không được có lỗi JS/console").toEqual([]);
    },
    { auto: true },
  ],
  allowConsoleErrors: async ({ page }, use) => {
    await use(() => (page as Page & { __allow?: () => void }).__allow?.());
  },
});

export { expect };

export async function search(page: Page, q: string) {
  const box = page.getByRole("searchbox", { name: "Tìm sản phẩm" });
  await box.fill(q);
  await box.press("Enter");
  await expect(page.getByText(/\d+ kết quả/)).toBeVisible();
}

export function cards(page: Page) {
  return page.locator("article.card");
}

export function cardTitles(page: Page) {
  return page.locator("article.card .card-title");
}
