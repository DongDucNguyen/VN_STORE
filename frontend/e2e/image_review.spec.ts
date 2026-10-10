import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expect, test } from "./fixtures";

// Packet chấm ảnh trên manifest TỔNG HỢP + catalog fixture (backend/tests/image_review_demo.py), adapter giả.
// Nhãn do test chọn chỉ để kiểm tra luồng, không phải judgment benchmark.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON = process.platform === "win32"
  ? path.join(ROOT, ".venv", "Scripts", "python.exe")
  : path.join(ROOT, ".venv", "bin", "python");

test("chấm query ảnh: điều kiện xác nhận, no-match cần đủ gallery, xuất → áp → audit", async ({ page }) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vnstore-image-review-"));
  const paths = JSON.parse(execFileSync(PYTHON, ["-X", "utf8", "-m", "tests.image_review_demo", path.join(dir, "demo")],
    { cwd: path.join(ROOT, "backend"), encoding: "utf8" }).trim().split("\n").pop()!);
  await page.goto(pathToFileURL(path.join(paths.packet, "index.html")).href);
  await expect(page.locator("#summary")).toContainText("3 query");
  await page.locator("#reviewer").fill("r-e2e");

  // exact: chấm hết danh sách chính, chọn sản phẩm đúng rồi mới xác nhận được.
  await page.locator("#query").selectOption("q-exact");
  const pool = page.locator("#pool select");
  const n = await pool.count();
  expect(n).toBeGreaterThan(2);
  for (let i = 0; i < n; i++) await pool.nth(i).selectOption(i === 0 ? "3" : "0");
  await page.locator("#confirmed").click();
  await expect(page.locator("#confirmed")).not.toBeChecked();
  await expect(page.getByRole("status")).toContainText("Chọn sản phẩm đúng");
  const exactOptions = page.locator("#exact option");
  await expect(exactOptions).toHaveCount(2);
  await page.locator("#exact").selectOption({ index: 1 });
  await page.locator("#indep").selectOption("yes");
  await page.locator("#indep-note").fill("Ảnh tự chụp, khác gallery");
  await page.locator("#confirmed").check();
  await expect(page.locator("#query option:checked")).toContainText("✓");
  // Sửa nhãn sau khi xác nhận thì mất xác nhận.
  await pool.nth(1).selectOption("1");
  await expect(page.locator("#confirmed")).not.toBeChecked();
  await page.locator("#confirmed").check();

  // no-match: chấm 0 cho danh sách chính chưa đủ; phải chấm cả phần còn lại của gallery.
  await page.locator("#query").selectOption("q-nomatch");
  for (const s of await page.locator("#pool select").all()) await s.selectOption("0");
  await page.locator("#confirmed").click();
  await expect(page.locator("#confirmed")).not.toBeChecked();
  await expect(page.getByRole("status")).toContainText("phần còn lại của gallery");
  await page.locator("#toggle-rest").click();
  for (const s of await page.locator("#rest select").all()) await s.selectOption("0");
  await page.locator("#confirmed").check();
  await expect(page.locator("#confirmed")).toBeChecked();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất judgment đã xác nhận" }).click();
  const exported = path.join(dir, (await download).suggestedFilename());
  await (await download).saveAs(exported);
  const data = JSON.parse(fs.readFileSync(exported, "utf8"));
  expect(data.items.map((i: { qid: string }) => i.qid)).toEqual(["q-exact", "q-nomatch"]);
  expect(data.items[0].judgment).toMatchObject({ has_answer: true, reviewed_by: "r-e2e" });
  expect(data.items[0].independence_review).toMatchObject({ independent: true, note: "Ảnh tự chụp, khác gallery" });
  expect(Object.keys(data.items[1].judgment.relevance)).toHaveLength(12);

  // Bản nháp còn sau khi tải lại trang.
  await page.reload();
  await expect(page.locator("#reviewer")).toHaveValue("r-e2e");

  const out = execFileSync(PYTHON, ["-X", "utf8", path.join(ROOT, "scripts/benchmark/apply_image_judgments.py"), exported,
    "--manifest", paths.manifest, "--catalog", paths.catalog], { encoding: "utf8" });
  expect(out).toContain("áp 2");
  expect(out).toContain("pending_review"); // q-text chưa chấm
  const rows = JSON.parse(fs.readFileSync(paths.manifest, "utf8")).samples;
  expect(rows.find((s: { qid: string }) => s.qid === "q-exact").judgment.exact_product_id)
    .toBe(data.items[0].judgment.exact_product_id);
  fs.rmSync(dir, { recursive: true, force: true });
});
