import { test, expect } from "./fixtures";

test("late autocomplete cannot repopulate a cleared query", async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/suggest?*", async (route) => {
    await pending;
    await route.fulfill({ json: [{ type: "product", id: "old", text: "Kết quả cũ" }] });
  });
  await page.goto("/");
  const box = page.getByRole("searchbox", { name: "Tìm sản phẩm" });
  const sent = page.waitForRequest("**/api/suggest?*");
  await box.fill("khăn");
  await sent;
  await box.fill("");
  const finished = page.waitForEvent("requestfinished", {
    predicate: (request) => request.url().includes("/api/suggest"), timeout: 2000,
  }).catch(() => null); // cancelling the request is also a valid outcome
  release();
  await finished;
  await expect(page.getByRole("listbox")).toHaveCount(0);
});

test("Escape discards selected autocomplete before Enter submits typed text", async ({ page }) => {
  await page.route("**/api/suggest?*", (route) => route.fulfill({ json: [
    { type: "product", id: "unwanted-product", text: "Gợi ý khác" },
  ] }));
  await page.goto("/");
  const box = page.getByRole("searchbox", { name: "Tìm sản phẩm" });
  await box.fill("khăn lụa");
  await expect(page.getByRole("listbox").getByRole("option")).toHaveCount(1);
  await box.press("ArrowDown");
  await box.press("Escape");
  await box.press("Enter");
  await expect(page).toHaveURL(/#\/search\?q=/);
  expect(new URLSearchParams(new URL(page.url()).hash.split("?")[1]).get("q")).toBe("khăn lụa");
});
