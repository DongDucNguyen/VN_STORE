import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "./fixtures";
import type { Page, TestInfo } from "@playwright/test";

// Ghi (micro giả 440 Hz) → duyệt bản chép lời → nhập/áp vào manifest tạm. Không phải giọng người thật.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON = process.platform === "win32"
  ? path.join(ROOT, ".venv", "Scripts", "python.exe")
  : path.join(ROOT, ".venv", "bin", "python");

function py(script: string, args: string[]): string {
  return execFileSync(PYTHON, ["-X", "utf8", path.join(ROOT, "scripts/benchmark", script), ...args],
                      { encoding: "utf8" });
}

function tempManifest(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "vnstore-review-"));
  fs.copyFileSync(path.join(ROOT, "benchmarks/voice/manifest.schema.json"), path.join(dir, "manifest.schema.json"));
  const target = path.join(dir, "manifest.json");
  fs.writeFileSync(target, JSON.stringify({ manifest_version: "1.0.0", samples: [] }));
  return target;
}

async function recordSession(page: Page, info: TestInfo): Promise<string> {
  await page.goto("/#/collect/voice");
  await page.getByLabel("Mã người nói").fill("s902");
  await page.getByLabel("Mã thiết bị").fill("e2e-fake-mic");
  await page.getByLabel(/Split/).selectOption("dev");
  await page.getByLabel("Mã hồ sơ đồng ý").fill("consent-e2e");
  await page.getByLabel(/Người nói đã đồng ý/).check();
  for (const id of ["p01", "p05"]) {
    await page.getByRole("button", { name: `Ghi câu ${id}` }).click();
    await expect(page.getByRole("button", { name: "Dừng", exact: true })).toBeVisible();
    // Cho micro giả đủ thời gian vượt ngưỡng 700 ms kể cả khi Chrome khởi động chậm.
    await page.waitForTimeout(1200);
    await page.getByRole("button", { name: "Dừng" }).click();
    await expect(page.getByLabel(`Nghe lại câu ${id}`)).toBeVisible();
  }
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Tải file zip của phiên" }).click();
  const file = await download;
  const zipPath = path.join(info.outputDir, file.suggestedFilename());
  await file.saveAs(zipPath);
  return zipPath;
}

test("ghi → duyệt bản chép lời → nhập mới và áp vào manifest đã nhập", async ({ page }, info) => {
  const sessionZip = await recordSession(page, info);

  await page.goto("/#/review/voice");
  // Zip được nén lại (deflate) bằng công cụ khác vẫn đọc được.
  const deflated = path.join(info.outputDir, "deflated.zip");
  execFileSync(PYTHON, ["-c", "import sys,zipfile\nsrc=zipfile.ZipFile(sys.argv[1])\n"
    + "with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as d:\n"
    + " [d.writestr(i.filename, src.read(i)) for i in src.infolist()]", sessionZip, deflated]);
  await page.getByLabel("File zip của phiên").setInputFiles(deflated);
  await expect(page.getByRole("status").filter({ hasText: "2 clip" })).toContainText("deflated.zip");
  await page.getByLabel("File zip của phiên").setInputFiles(sessionZip);
  await expect(page.getByRole("status").filter({ hasText: "2 clip" })).toContainText("s902");
  const exportBtn = page.getByRole("button", { name: "Tải zip đã duyệt" });
  await expect(exportBtn).toBeDisabled();

  const text = page.getByLabel(/^Bản chép lời s902-.*-p01$/);
  await expect(text).toHaveValue("tìm cho mình cái túi cói dưới ba trăm nghìn");
  // Gợi ý ASR (adapter giả) chỉ hiện để tham khảo, không ghi vào ô.
  await page.getByRole("button", { name: /Gợi ý từ ASR cho s902-.*-p01/ }).click();
  await expect(page.getByText(/ASR \(chỉ tham khảo/)).toContainText("túi cói");
  await text.fill("tìm cho mình cái túi cói dưới ba trăm");
  await page.getByLabel(/^Đã nghe và xác nhận s902-.*-p01$/).check();
  await expect(exportBtn).toBeDisabled(); // chưa nhập người duyệt
  await page.getByLabel(/Người duyệt/).fill("r-e2e");
  // Sửa sau khi xác nhận thì phải xác nhận lại.
  await text.fill("tìm cho mình cái túi cói dưới ba trăm ");
  await expect(page.getByLabel(/^Đã nghe và xác nhận s902-.*-p01$/)).not.toBeChecked();
  await expect(exportBtn).toBeDisabled();
  await page.getByLabel(/^Đã nghe và xác nhận s902-.*-p01$/).check();

  const download = page.waitForEvent("download");
  await exportBtn.click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^voice-s902-\d{8}t\d{4}-reviewed-\d{8}t\d{6}\.zip$/);
  const reviewedZip = path.join(info.outputDir, file.suggestedFilename());
  await file.saveAs(reviewedZip);

  // Phiên chưa nhập: nhập thẳng zip đã duyệt.
  const fresh = tempManifest();
  expect(py("import_voice_session.py", [reviewedZip, "--manifest", fresh])).toContain("2 clip");
  const rows = JSON.parse(fs.readFileSync(fresh, "utf8")).samples;
  const p01 = rows.find((s: { qid: string }) => s.qid.endsWith("-p01"));
  const p05 = rows.find((s: { qid: string }) => s.qid.endsWith("-p05"));
  expect(p01.reference_text).toBe("tìm cho mình cái túi cói dưới ba trăm");
  expect(p01.transcript_review.reviewed_by).toBe("r-e2e");
  expect(p05.transcript_review).toBeNull();
  expect(p05.reference_text).toBe("bình hoa Minh Long");

  // Phiên đã nhập bản gốc: áp kết quả duyệt theo qid.
  const imported = tempManifest();
  py("import_voice_session.py", [sessionZip, "--manifest", imported]);
  expect(py("apply_voice_review.py", [reviewedZip, "--manifest", imported])).toContain("áp 1");
  const applied = JSON.parse(fs.readFileSync(imported, "utf8")).samples;
  expect(applied.find((s: { qid: string }) => s.qid.endsWith("-p01")).transcript_review.reviewed_by).toBe("r-e2e");
  for (const m of [fresh, imported]) fs.rmSync(path.dirname(m), { recursive: true, force: true });
});

test("zip không hợp lệ bị từ chối với thông báo rõ", async ({ page }, info) => {
  const bad = path.join(info.outputDir, "khong-phai-zip.zip");
  fs.mkdirSync(info.outputDir, { recursive: true });
  fs.writeFileSync(bad, "không phải zip");
  await page.goto("/#/review/voice");
  await page.getByLabel("File zip của phiên").setInputFiles(bad);
  await expect(page.getByRole("alert")).toContainText("Không phải file zip hợp lệ");
  await expect(page.getByRole("button", { name: "Tải zip đã duyệt" })).toHaveCount(0);
});
