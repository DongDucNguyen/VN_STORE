import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import zlib from "node:zlib";
import { expect, test } from "./fixtures";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON = process.platform === "win32"
  ? path.join(ROOT, ".venv", "Scripts", "python.exe")
  : path.join(ROOT, ".venv", "bin", "python");

function png(seed: number, width = 200, height = 150): Buffer {
  const chunk = (type: string, body: Buffer) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(body.length);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(zlib.crc32(Buffer.concat([Buffer.from(type), body])) >>> 0);
    return Buffer.concat([len, Buffer.from(type), body, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.set([8, 2, 0, 0, 0], 8);
  const rows = [];
  for (let y = 0; y < height; y++) {
    const row = Buffer.alloc(1 + width * 3);
    for (let x = 0; x < width; x++) row.set([(x * seed) % 256, (y * 3) % 256, seed], 1 + x * 3);
    rows.push(row);
  }
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr),
                        chunk("IDAT", zlib.deflateSync(Buffer.concat(rows))), chunk("IEND", Buffer.alloc(0))]);
}

test("chụp 2 ảnh → zip, script nhập + audit chấp nhận (pending_review)", async ({ page }, info) => {
  await page.goto("/#/collect/image");
  const pick = page.getByLabel("📷 Chụp / chọn ảnh");
  await expect(pick).toBeDisabled();

  await page.getByLabel("Mã người chụp").fill("c901");
  await page.getByLabel(/Mã phiên chụp/).fill("c901-e2e");
  await page.getByLabel(/Split/).selectOption("dev");
  await page.getByLabel("Quyền sử dụng ảnh").selectOption("owned");
  await page.getByLabel("Mã bằng chứng quyền").fill("rights-e2e");
  await page.getByLabel(/Họ sản phẩm/).fill("fx-gio-may-co-quai");

  await pick.setInputFiles({ name: "a.png", mimeType: "image/png", buffer: png(7) });
  await expect(page.getByRole("img", { name: /Ảnh c901-.*-001/ })).toBeVisible();
  await page.getByLabel("Tác vụ").selectOption("image_text");
  await page.getByLabel("Yêu cầu bằng chữ").fill("giống mẫu này nhưng dưới 400k");
  await pick.setInputFiles({ name: "b.png", mimeType: "image/png", buffer: png(11) });
  await expect(page.getByText("Đã thêm 2 ảnh.")).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Tải file zip của phiên" }).click();
  const file = await download;
  const zipPath = path.join(info.outputDir, file.suggestedFilename());
  await file.saveAs(zipPath);

  // Bản sao manifest ảnh thật (gắn catalog fixture) để không đụng benchmarks/image.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vnstore-image-"));
  const target = path.join(dir, "manifest.json");
  const fixture = path.join(ROOT, "backend", "tests", "fixtures", "catalog.fixture.json");
  const sha = (await import("node:crypto")).createHash("sha256").update(fs.readFileSync(fixture)).digest("hex");
  fs.writeFileSync(target, JSON.stringify({ manifest_version: "1.0.0", catalog_sha256: sha, include_drafts: false,
                                            samples: [] }));
  const out = execFileSync(PYTHON, ["-X", "utf8", path.join(ROOT, "scripts/benchmark/import_image_session.py"),
                                    zipPath, "--manifest", target, "--catalog", fixture, "--dry-run"],
                           { encoding: "utf8" });
  expect(out).toContain("2 ảnh");
  expect(out).toContain("audit: pending_review");
  fs.rmSync(dir, { recursive: true, force: true });
});
