import { test, expect, cards } from "./fixtures";

test("voice uses returned results once; editing transcript performs keyword search", async ({ page }) => {
  let keywordRequests = 0;
  page.on("request", (r) => { if (new URL(r.url()).pathname === "/api/search") keywordRequests++; });
  await page.goto("/");
  await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
  await expect(page.getByText("Đang nghe…")).toBeVisible();
  await page.waitForTimeout(850);
  await page.getByRole("button", { name: "Dừng và tìm" }).click();
  await expect(page).toHaveURL(/voice_id=/);
  await expect(cards(page).first()).toBeVisible();
  expect(keywordRequests).toBe(0);
  await page.getByRole("searchbox").fill("khăn lụa");
  await page.getByRole("searchbox").press("Enter");
  await expect(page).not.toHaveURL(/via=voice/);
  await expect.poll(() => keywordRequests).toBe(1);
});

test("cancel delayed ASR does not navigate away from typed search", async ({ page, allowConsoleErrors }) => {
  allowConsoleErrors();
  let release!: () => void;
  const waiting = new Promise<void>((r) => { release = r; });
  await page.route("**/api/search/voice", async (route) => {
    const response = await route.fetch();
    await waiting;
    await route.fulfill({ response }).catch(() => {});
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
  await expect(page.getByText("Đang nghe…")).toBeVisible();
  await page.waitForTimeout(850);
  await page.getByRole("button", { name: "Dừng và tìm" }).click();
  await expect(page.getByText("Đang chép lời…")).toBeVisible();
  await page.getByRole("button", { name: "Hủy", exact: true }).click();
  await page.getByRole("searchbox").fill("khăn lụa");
  await page.getByRole("searchbox").press("Enter");
  release();
  await expect(cards(page).first()).toBeVisible();
  await expect(page).not.toHaveURL(/via=voice/);
  await expect(page.getByRole("searchbox")).toHaveValue("khăn lụa");
});

test("late microphone permission is released after leaving the page", async ({ page }) => {
  await page.addInitScript(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    const state = window as unknown as { releaseMic: () => void; micTracks: MediaStreamTrack[] };
    navigator.mediaDevices.getUserMedia = async (constraints) => {
      const stream = await original(constraints);
      state.micTracks = stream.getTracks();
      await new Promise<void>((r) => { state.releaseMic = r; });
      return stream;
    };
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
  await expect.poll(() => page.evaluate(() => typeof (window as unknown as { releaseMic: unknown }).releaseMic)).toBe("function");
  await page.getByRole("button", { name: "Tìm bằng ảnh" }).click();
  await page.evaluate(() => (window as unknown as { releaseMic: () => void }).releaseMic());
  await expect.poll(() => page.evaluate(() => (window as unknown as { micTracks: MediaStreamTrack[] })
    .micTracks.every((track) => track.readyState === "ended"))).toBe(true);
});

test("diagnostics exports only opt-in timing data", async ({ page }, testInfo) => {
  await page.goto("/#/diagnostics");
  await expect(page.getByRole("heading", { name: "Chẩn đoán demo" })).toBeVisible();
  await page.getByRole("button", { name: "Bắt đầu đo" }).click();
  await page.getByRole("link", { name: "Tìm bằng chữ hoặc giọng nói" }).click();
  await page.getByRole("searchbox").fill("khăn lụa");
  await page.getByRole("searchbox").press("Enter");
  await expect(cards(page).first()).toBeVisible();
  await page.waitForTimeout(100); // two result-paint frames
  await page.evaluate(() => { location.hash = "/diagnostics"; });
  await expect(page.getByText(/Đang ghi số đo · 1 lượt/)).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất số đo JSON" }).click();
  const artifact = await download;
  const path = testInfo.outputPath("browser-timings.json");
  await artifact.saveAs(path);
  const { readFile } = await import("node:fs/promises");
  const data = JSON.parse(await readFile(path, "utf8"));
  expect(data.quality_benchmark).toBe(false);
  expect(data.version).toBe(2);
  expect(data.outcomes.keyword).toEqual({ error: 0, cancelled: 0 });
  expect(data.samples[0].browser_ms).toBeGreaterThan(0);
  expect(Object.keys(data.samples[0]).sort()).toEqual([
    "browser_ms", "cached", "catalog_version", "kind", "model_id", "revision", "server_ms",
  ]);
  expect(JSON.stringify(data)).not.toContain("khăn lụa");
  await page.getByRole("button", { name: "Xóa số đo" }).click();
  await expect(page.getByRole("button", { name: "Xuất số đo JSON" })).toBeDisabled();
});

test("diagnostics counts failed searches outside the latency distribution", async ({ page, allowConsoleErrors }, testInfo) => {
  allowConsoleErrors();
  await page.route((url) => url.pathname === "/api/search", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "synthetic" }) }));
  await page.goto("/#/diagnostics");
  await page.getByRole("button", { name: "Bắt đầu đo" }).click();
  await page.getByRole("link", { name: "Tìm bằng chữ hoặc giọng nói" }).click();
  await page.getByRole("searchbox").fill("khăn lụa");
  await page.getByRole("searchbox").press("Enter");
  await expect(page.getByRole("alert").first()).toBeVisible();
  await page.evaluate(() => { location.hash = "/diagnostics"; });
  await expect(page.getByText(/0 lượt · 1 lỗi\/hủy/)).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất số đo JSON" }).click();
  const path = testInfo.outputPath("browser-timings.json");
  await (await download).saveAs(path);
  const { readFile } = await import("node:fs/promises");
  const data = JSON.parse(await readFile(path, "utf8"));
  expect(data.samples).toEqual([]);
  expect(data.outcomes.keyword).toEqual({ error: 1, cancelled: 0 });
});

test("changing image discards an older pending response", async ({ page, allowConsoleErrors }) => {
  allowConsoleErrors();
  let release!: () => void;
  let received!: () => void;
  const arrived = new Promise<void>((r) => { received = r; });
  const hold = new Promise<void>((r) => { release = r; });
  await page.route("**/api/search/image?**", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.warnings = ["OLD_IMAGE_RESULT"];
    received();
    await hold;
    await route.fulfill({ response, json }).catch(() => {});
  });
  await page.goto("/#/image");
  const bytes = await page.evaluate(() => {
    const canvas = document.createElement("canvas"); canvas.width = 80; canvas.height = 80;
    canvas.getContext("2d")!.fillRect(0, 0, 80, 80);
    return canvas.toDataURL("image/png").split(",")[1];
  });
  const input = page.locator('input[type="file"]').last();
  await input.setInputFiles({ name: "first.png", mimeType: "image/png", buffer: Buffer.from(bytes, "base64") });
  await page.getByRole("button", { name: "Tìm mẫu tương tự" }).click();
  await arrived;
  await input.setInputFiles({ name: "second.png", mimeType: "image/png", buffer: Buffer.from(bytes, "base64") });
  release();
  await expect(page.getByRole("button", { name: "Tìm mẫu tương tự" })).toBeEnabled();
  await expect(page.getByText("OLD_IMAGE_RESULT")).toHaveCount(0);
  await expect(cards(page)).toHaveCount(0);
});
