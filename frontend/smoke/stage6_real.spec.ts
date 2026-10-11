import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

test("local models: browser → WAV/image → inference → editable results and timing export", async ({ page }, info) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/#/diagnostics");
  await expect(page.getByText(/voice: ok/)).toBeVisible();
  await expect(page.getByText(/image: ok/)).toBeVisible();
  await page.getByRole("button", { name: "Bắt đầu đo" }).click();
  await page.getByRole("link", { name: "Tìm bằng chữ hoặc giọng nói" }).click();
  for (const query of ["túi cói", "bình gốm", "khăn lụa"]) {
    await page.getByRole("searchbox").fill(query);
    await page.getByRole("searchbox").press("Enter");
    await expect(page.getByText(/\d+ kết quả/)).toBeVisible();
    await page.waitForTimeout(150);
  }
  await page.getByRole("button", { name: "Tìm bằng ảnh" }).click();
  const root = path.resolve("..");
  const catalog = JSON.parse(fs.readFileSync(path.join(root, "database.json"), "utf8"));
  // Fresh searches always run embedding + OCR (the server cache is only used for filter changes).
  for (const id of ["p-marou-ba-ria-76-80g", "p-marou-ben-tre-78-80g", "p-marou-lam-dong-74-80g"]) {
    const product = catalog.products.find((p: { id: string }) => p.id === id);
    await page.locator('input[type="file"]').last().setInputFiles(path.join(root, product.images[0].local_path));
    const response = page.waitForResponse((r) => r.url().includes("/api/search/image?"));
    await page.getByRole("button", { name: "Tìm mẫu tương tự" }).click();
    const res = await response;
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.visual.model_id).toContain("siglip2");
    expect(body.visual.query_cache).toBe("miss");
    expect(body.timings_ms.ocr).toBeGreaterThan(0);
    expect(body.warnings.join(" ")).not.toContain("Chưa đọc được chữ");
    await expect(page.locator("article.card").first()).toBeVisible();
    await page.waitForTimeout(150);
  }
  // Changing a filter re-sends the prepared image; the server reuses embedding/OCR (exported as cached).
  const panel = page.locator("details.filters");
  if (!(await panel.evaluate((d) => (d as HTMLDetailsElement).open))) await panel.locator("summary").click();
  const refiltered = page.waitForResponse((r) => r.url().includes("/api/search/image?") && r.url().includes("filters="));
  await panel.getByRole("checkbox").first().check();
  const cached = await (await refiltered).json();
  expect(cached.visual.query_cache).toBe("hit");
  expect(cached.timings_ms.embed).toBe(0);
  await page.waitForTimeout(150);
  await page.screenshot({ path: info.outputPath("image-results.png"), fullPage: true });
  for (let i = 0; i < 3; i++) {
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await expect(page.getByText("Đang nghe…")).toBeVisible();
    await page.waitForTimeout(4000); // FLEURS replay, not a VNStore query or a live participant
    const response = page.waitForResponse("**/api/search/voice");
    await page.getByRole("button", { name: "Dừng và tìm" }).click();
    const res = await response;
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.transcript.model_id).toContain("PhoWhisper-small");
    await expect(page.getByRole("searchbox")).toHaveValue(body.transcript.text);
    await expect(page.getByText(/Đã chép lời từ giọng nói/)).toBeVisible();
    await page.waitForTimeout(150);
  }
  await page.screenshot({ path: info.outputPath("voice-results.png"), fullPage: true });
  await page.evaluate(() => { location.hash = "/diagnostics"; });
  await expect(page.getByText(/Đang ghi số đo · 10 lượt/)).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất số đo JSON" }).click();
  await (await download).saveAs(info.outputPath("browser-timings.json"));
  await page.screenshot({ path: info.outputPath("diagnostics.png"), fullPage: true });
  expect(errors).toEqual([]);
});
