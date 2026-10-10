import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "./fixtures";

// Trang thu âm nội bộ: micro giả của Chrome phát âm 440 Hz (không phải giọng người).
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON = process.platform === "win32"
  ? path.join(ROOT, ".venv", "Scripts", "python.exe")
  : path.join(ROOT, ".venv", "bin", "python");

test("thu âm 2 câu → zip đúng schema, script nhập chấp nhận", async ({ page }, info) => {
  await page.goto("/#/collect/voice");
  const record = page.getByRole("button", { name: "Ghi câu p01" });
  await expect(record).toBeDisabled(); // chưa đủ thông tin phiên và đồng ý

  await page.getByLabel("Mã người nói").fill("s901");
  await page.getByLabel("Mã thiết bị").fill("e2e-fake-mic");
  await page.getByLabel(/Split/).selectOption("dev");
  await page.getByLabel("Mã hồ sơ đồng ý").fill("consent-e2e");
  await page.getByLabel(/Người nói đã đồng ý/).check();

  for (const id of ["p01", "p02"]) {
    await page.getByRole("button", { name: `Ghi câu ${id}` }).click();
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "Dừng" }).click();
    await expect(page.getByLabel(`Nghe lại câu ${id}`)).toBeVisible();
  }
  await expect(page.getByText("Đã ghi 2/")).toBeVisible();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Tải file zip của phiên" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^voice-s901-\d{8}t\d{4}\.zip$/);
  const zipPath = path.join(info.outputDir, file.suggestedFilename());
  await file.saveAs(zipPath);

  // Script nhập (dry-run) trên manifest rỗng tạm thời: schema, hash, giải mã WAV, split người nói.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vnstore-voice-"));
  const target = path.join(dir, "manifest.json");
  fs.writeFileSync(target, JSON.stringify({ manifest_version: "1.0.0", samples: [] }));
  const out = execFileSync(PYTHON, ["-X", "utf8", path.join(ROOT, "scripts/benchmark/import_voice_session.py"),
                                    zipPath, "--manifest", target, "--dry-run"], { encoding: "utf8" });
  expect(out).toContain("2 clip");
  expect(out).toContain("s901");
  fs.rmSync(dir, { recursive: true, force: true });
});
