import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expect, test } from "./fixtures";

// Trang duyệt họ dựng từ đề xuất thật + ảnh catalog thật; quyết định do test chọn chỉ để kiểm tra luồng.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON = path.join(ROOT, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const script = (name: string) => path.join(ROOT, "scripts/benchmark", name);

test("duyệt họ: tách, gộp/không gộp, ảnh dùng chung → xuất → áp thành families.json", async ({ page }) => {
  const out = path.join(ROOT, "artifacts", `family-review-test-${randomUUID()}`);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vnstore-family-"));
  execFileSync(PYTHON, ["-X", "utf8", script("prepare_family_review.py"), "--out", out]);
  try {
    const packet = JSON.parse(fs.readFileSync(path.join(out, "packet.json"), "utf8"));
    await page.goto(pathToFileURL(path.join(out, "index.html")).href);
    const cards = page.locator("article.card");
    await expect(cards).toHaveCount(packet.families.length);
    // Ảnh local phải tải được (không phải chỉ có thẻ img).
    const first = cards.first().locator("img").first();
    await expect.poll(() => first.evaluate((i) => (i as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);

    await page.locator("#reviewer").fill("r-e2e");
    // Họ đầu tiên: tách — chưa gán đủ nhóm thì chưa tính là xong.
    await cards.first().getByLabel("Tách thành nhiều họ").check();
    const selects = cards.first().locator("select");
    const n = await selects.count();
    for (let i = 0; i < n; i++) await selects.nth(i).selectOption(i === 0 ? "A" : "B");
    for (const c of await cards.all()) {
      const confirm = c.getByLabel("Đúng là một họ");
      if (!(await c.getByLabel("Tách thành nhiều họ").isChecked())) await confirm.check();
    }
    await page.getByRole("button", { name: "Ứng viên ảnh" }).click();
    const cand = page.locator("article.card");
    await expect(cand).toHaveCount(packet.candidates.length);
    for (const c of await cand.all()) await c.getByLabel("Khác họ").check();
    await page.getByRole("button", { name: "Ảnh dùng chung" }).click();
    await page.locator("article.card").first().getByLabel("Đề nghị loại khỏi gallery").check();
    await expect(page.locator("#summary")).toContainText(`họ ${packet.families.length}/${packet.families.length}`);

    // "Khác họ" cho mọi cặp mâu thuẫn với các họ vừa xác nhận; phải sửa trước khi xuất.
    await page.getByRole("button", { name: "Xuất quyết định" }).click();
    await expect(page.locator("#notice")).toContainText("Mâu thuẫn");
    await page.getByRole("button", { name: "Ứng viên ảnh" }).click();
    const split = packet.families[0];
    const group = (pid: string) => split.products.includes(pid)
      ? `${split.family_id}:${pid === split.products[0] ? "A" : "B"}` : packet.products[pid].family;
    for (let i = 0; i < packet.candidates.length; i++) {
      const c = packet.candidates[i];
      if (group(c.a) === group(c.b)) await cand.nth(i).getByLabel("Cùng họ (gộp)", { exact: true }).check();
    }

    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: "Xuất quyết định" }).click();
    const file = path.join(tmp, (await dl).suggestedFilename());
    await (await dl).saveAs(file);
    const dec = JSON.parse(fs.readFileSync(file, "utf8"));
    expect(dec).toMatchObject({ complete: true, reviewed_by: "r-e2e" });
    expect(Object.values(dec.shared)).toEqual(["exclude"]);

    const target = path.join(tmp, "families.json");
    const log = execFileSync(PYTHON, ["-X", "utf8", script("apply_family_review.py"), file, "--out", target],
                             { encoding: "utf8" });
    expect(log).toContain("tách 1 họ đề xuất, gộp 0 cặp");
    const fam = JSON.parse(fs.readFileSync(target, "utf8"));
    expect(fam.status).toBe("reviewed");
    const products = JSON.parse(fs.readFileSync(path.join(ROOT, "database.json"), "utf8")).products;
    expect(Object.keys(fam.product_family)).toHaveLength(products.length);  // mọi sản phẩm đều có họ
    // Bản nháp còn sau khi tải lại.
    await page.reload();
    await expect(page.locator("#reviewer")).toHaveValue("r-e2e");
  } finally {
    fs.rmSync(out, { recursive: true, force: true });
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});
