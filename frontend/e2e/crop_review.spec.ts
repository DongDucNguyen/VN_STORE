import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expect, test } from "./fixtures";

// Trang duyệt vùng cắt của bộ ảnh thử khám phá, dựng trên bộ dữ liệu tổng hợp (ảnh sinh bằng media_samples).
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON = path.join(ROOT, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");

function makeDataset(): string {
  const ds = fs.mkdtempSync(path.join(os.tmpdir(), "vnstore-crop-review-"));
  const png = execFileSync(PYTHON, ["-c",
    "import sys; sys.path.insert(0, 'backend'); from tests.media_samples import png; sys.stdout.buffer.write(png(160, 120))"],
  { cwd: ROOT });
  const images = ["a", "b"].map((id) => {
    const rel = `raw/images/similar_candidate/gom-su/${id}.png`;
    fs.mkdirSync(path.join(ds, path.dirname(rel)), { recursive: true });
    fs.writeFileSync(path.join(ds, rel), png);
    // Tiêu đề có thẻ HTML: trang phải hiện nguyên văn, không chèn thành phần tử.
    return { id, role: "similar_candidate", group: "gom-su", topic: null, title: `File:<b>${id}</b>.png`, image_path: rel,
      sha256: createHash("sha256").update(png).digest("hex") };
  });
  fs.writeFileSync(path.join(ds, "manifest.json"), JSON.stringify({ dataset_version: "e2e-1", images }));
  fs.writeFileSync(path.join(ds, "test_cases.json"), JSON.stringify({ cases: images.map((im) => ({
    case_id: `${im.id}-crop`, image_id: im.id, image_path: im.image_path, task: "manual_crop_comparison",
    text_vi: "", crop_instruction_vi: `Chọn vật thể ${im.id}`,
  })) }));
  fs.writeFileSync(path.join(ds, "crops.json"), JSON.stringify({
    format: "xyxy", chosen_by: "e2e", crops: { "a-crop": [0.1, 0.1, 0.9, 0.9], "b-crop": [0.2, 0.2, 0.8, 0.8] },
  }));
  execFileSync(PYTHON, ["-X", "utf8", path.join(ROOT, "scripts/benchmark/prepare_crop_review.py"), "--dataset", ds]);
  return ds;
}

test("duyệt vùng cắt: vẽ lại, xác nhận, đồng ý → xuất file runner nhận được", async ({ page }) => {
  const ds = makeDataset();
  try {
    await page.goto(pathToFileURL(path.join(ds, "crop_review.html")).href);
    const cards = page.locator("section.card");
    await expect(cards).toHaveCount(2);
    await expect.poll(() => cards.first().locator("canvas").evaluate((c) => (c as HTMLCanvasElement).width)).toBeGreaterThan(0);
    await expect(cards.first()).toContainText("<b>a</b>.png");
    await expect(cards.first().locator("b")).toHaveCount(0);
    await expect(page.locator("#progress")).toHaveText("Đã duyệt 0/2");

    // Vẽ vùng mới bằng chuột trên ảnh thứ nhất.
    const first = cards.first();
    const img = first.locator("img");
    await img.scrollIntoViewIfNeeded();
    const bb = (await img.boundingBox())!;
    await page.mouse.move(bb.x + bb.width * 0.25, bb.y + bb.height * 0.25);
    await page.mouse.down();
    await page.mouse.move(bb.x + bb.width * 0.75, bb.y + bb.height * 0.75, { steps: 4 });
    await page.mouse.up();
    await expect(first.locator(".chip")).toHaveText("đã sửa — chưa xác nhận");
    const coords = await first.locator(".coords input").evaluateAll((es) => es.map((e) => Number((e as HTMLInputElement).value)));
    expect(coords.map((v) => Math.round(v * 4) / 4)).toEqual([0.25, 0.25, 0.75, 0.75]);

    // Chưa xác nhận thì không xuất được; thiếu mã người duyệt cũng không.
    await page.getByRole("button", { name: "Xuất kết quả duyệt" }).click();
    await expect(page.locator("#notice")).toContainText("mã người duyệt");
    await page.locator("#reviewer").fill("r-e2e");
    await page.getByRole("button", { name: "Xuất kết quả duyệt" }).click();
    await expect(page.locator("#notice")).toContainText("chưa xác nhận");

    await first.getByRole("button", { name: "Xác nhận vùng đã sửa" }).click();
    await expect(first.locator(".chip")).toHaveText("đã sửa");
    await cards.nth(1).getByRole("button", { name: "Đồng ý" }).click();
    await expect(page.locator("#progress")).toHaveText("Đã duyệt 2/2");

    // Nháp còn sau khi tải lại.
    await page.reload();
    await expect(page.locator("#progress")).toHaveText("Đã duyệt 2/2");

    const [download] = await Promise.all([page.waitForEvent("download"),
      page.getByRole("button", { name: "Xuất kết quả duyệt" }).click()]);
    const out = path.join(ds, "crops.reviewed.json");
    await download.saveAs(out);
    const exported = JSON.parse(fs.readFileSync(out, "utf8"));
    expect(exported.kind).toBe("vnstore_crop_review");
    expect(exported.complete).toBe(true);
    expect(exported.reviewed_by).toBe("r-e2e");
    expect(Object.keys(exported.crops).sort()).toEqual(["a-crop", "b-crop"]);
    expect(exported.items.map((i: { decision: string }) => i.decision)).toEqual(["edited", "approved"]);

    // Runner chấp nhận đúng file vừa xuất (kiểm hợp lệ vùng/ca, không cần model).
    execFileSync(PYTHON, ["-X", "utf8", "-c",
      "import sys; from pathlib import Path; sys.path.insert(0, 'scripts/benchmark'); import run_image_exploratory as r; "
      + "m, c, crops = r.load_dataset(Path(sys.argv[1]), Path(sys.argv[2])); assert len(crops) == 2; "
      + "assert r.crops_meta(Path(sys.argv[2]))['reviewed']", ds, out], { cwd: ROOT });
  } finally {
    fs.rmSync(ds, { recursive: true, force: true });
  }
});
