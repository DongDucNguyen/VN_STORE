import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { expect, test } from "./fixtures";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const template = readFileSync(path.join(ROOT, "scripts/benchmark/review_template.html"), "utf8");
// Synthetic annotation packet: never exports real benchmark labels.
const packet = {
  catalog_sha256: "fixture-review", queries_sha256: "fixture-queries", catalog_version: "fixture-review",
  queries: [{ qid: "q1", query: "giỏ tre", split: "dev", relevance: { a: 3 }, has_answer: true,
    labeled_by: "ai-draft", verified: false }],
  products: ["a", "b"].map((id) => ({ id, name: `Sản phẩm ${id}`, category: "Giỏ", description: "Mô tả",
    materials: ["tre"], colors: [], variants: [{ price_vnd: null }], claims: [], sources: [], image: null })),
  candidate_order: { q1: ["b", "a"] },
};

test("review: cần chấm đủ và xác nhận; xuất nhãn do người kiểm tra", async ({ page }) => {
  await page.goto("/");
  await page.setContent(template.replace("__PACKET_JSON__", JSON.stringify(packet)));
  await page.getByRole("button", { name: "Xuất nhãn đã duyệt" }).click();
  await expect(page.getByRole("status")).toContainText("Cần tên người kiểm tra");
  await page.locator("#reviewer").fill("synthetic-tester");
  await page.locator("#confirmed").click();
  await expect(page.locator("#confirmed")).not.toBeChecked();
  await page.getByLabel("Mức phù hợp: Sản phẩm a", { exact: true }).selectOption("3");
  await page.getByLabel("Mức phù hợp: Sản phẩm b", { exact: true }).selectOption("0");
  await page.locator("#confirmed").check();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất nhãn đã duyệt" }).click();
  const stream = await (await downloaded).createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const row = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  expect(row).toMatchObject({ verified: true, labeled_by: "synthetic-tester", relevance: { a: 3, b: 0 },
    has_answer: true, catalog_sha256: "fixture-review" });
  // Editing an accepted label invalidates the explicit confirmation.
  await page.getByLabel("Mức phù hợp: Sản phẩm a", { exact: true }).selectOption("0");
  await expect(page.locator("#confirmed")).not.toBeChecked();
});

test("review: lưu và khôi phục nháp, không trộn catalog", async ({ page }) => {
  await page.goto("/");
  const document = template.replace("__PACKET_JSON__", JSON.stringify(packet));
  await page.setContent(document);
  await page.locator("#reviewer").fill("draft-tester");
  await page.getByLabel("Mức phù hợp: Sản phẩm a", { exact: true }).selectOption("2");
  await page.goto("/");
  await page.setContent(document);
  await expect(page.locator("#reviewer")).toHaveValue("draft-tester");
  await expect(page.getByLabel("Mức phù hợp: Sản phẩm a", { exact: true })).toHaveValue("2");
  await page.locator("#restore").setInputFiles({ name: "wrong.json", mimeType: "application/json",
    buffer: Buffer.from(JSON.stringify({ key: "another-catalog", state: {} })) });
  await expect(page.getByRole("status")).toContainText("không khớp catalog");
});

test("review: packet thật đủ 30 sản phẩm và ảnh local", async ({ page }) => {
  const output = path.join(ROOT, "artifacts", `keyword-review-test-${randomUUID()}`);
  const python = path.join(ROOT, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  execFileSync(python, [path.join(ROOT, "scripts/benchmark/prepare_review.py"),
    "--queries", path.join(ROOT, "benchmarks/keyword/seed_unverified.jsonl"), "--include-drafts", "--out", output]);
  const generated = JSON.parse(readFileSync(path.join(output, "packet.json"), "utf8"));
  const file = path.join(output, "index.html");
  await page.goto(pathToFileURL(file).href);
  await expect(page.locator("article")).toHaveCount(generated.products.length);
  await expect(page.locator("#query option")).toHaveCount(generated.queries.length);
  // Load all lazy images so a missing file cannot pass simply by staying below the fold.
  await page.locator("article img").evaluateAll((images) => images.forEach((img) => img.setAttribute("loading", "eager")));
  await expect.poll(() => page.locator("article img").evaluateAll((images) =>
    images.filter((img) => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0).length)).toBe(generated.products.filter((p: { image: string | null }) => p.image).length);
  await expect(page.locator("#confirmed")).not.toBeChecked();
});
