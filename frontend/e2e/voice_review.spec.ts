import { test, expect, cardTitles } from "./fixtures";

async function record(page: import("@playwright/test").Page) {
  await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
  await expect(page.getByText("Đang nghe…")).toBeVisible();
  await page.waitForTimeout(850);
  await page.getByRole("button", { name: "Dừng và xem lời" }).click();
  await expect(page.getByRole("region", { name: "Xác nhận bản chép lời" })).toBeVisible();
}

test("selecting a suggestion preserves original and only searches after confirmation", async ({ page }) => {
  const queries: string[] = [];
  page.on("request", (r) => {
    if (new URL(r.url()).pathname === "/api/search") queries.push(r.postDataJSON().query);
  });
  await page.route("**/api/search/voice*", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    body.transcript.text = "khăn nụa";
    body.transcript.raw_text = "  khăn nụa  ";
    body.transcript.suggestions = [{ text: "khăn lụa", phrase: "khăn lụa", evidence: "catalog_text_only" }];
    body.warnings = ["Âm lượng nhỏ. Hãy kiểm tra bản chép lời hoặc nói gần micro hơn và ghi lại."];
    await route.fulfill({ response, json: body });
  });
  await page.goto("/");
  await record(page);
  await expect(page.getByRole("region", { name: "Xác nhận bản chép lời" }).locator("audio")).toHaveCount(0);
  await expect(page.getByText(/Âm lượng nhỏ/)).toBeVisible();
  expect(queries).toEqual([]);
  await page.getByRole("button", { name: "khăn lụa", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Cụm từ dùng để tìm kiếm" })).toHaveValue("khăn lụa");
  await expect(page.locator(".voice-original")).toHaveText("  khăn nụa  ");
  expect(queries).toEqual([]);
  await page.getByRole("region", { name: "Xác nhận bản chép lời" })
    .screenshot({ path: test.info().outputPath("voice-review.png") });
  await page.getByRole("button", { name: "Tìm theo câu này" }).click();
  await expect(cardTitles(page)).toHaveText(["Khăn lụa tơ tằm màu đỏ"]);
  expect(queries).toEqual(["khăn lụa"]);
  await expect(page.getByText(/Bản chép lời gốc:/)).toContainText("khăn nụa");
});

test("cancel and blank edits never search; English choice is passed per recording", async ({ page }) => {
  let searches = 0;
  let language = "";
  page.on("request", (r) => { if (new URL(r.url()).pathname === "/api/search") searches++; });
  await page.route("**/api/search/voice*", async (route) => {
    language = new URL(route.request().url()).searchParams.get("language") ?? "";
    await route.fulfill({ json: { mode: "voice", warnings: [], timings_ms: { total: 5 }, transcript: {
      text: "Marou dark chocolate", raw_text: "Marou dark chocolate", language: "en", model_id: "fake",
      revision: "test", editable: true, duration_s: 1, suggestions: [],
    } } });
  });
  await page.goto("/");
  await page.getByRole("combobox", { name: "Ngôn ngữ giọng nói" }).selectOption("en");
  await record(page);
  expect(language).toBe("en");
  const query = page.getByRole("textbox", { name: "Cụm từ dùng để tìm kiếm" });
  await expect(query).toHaveValue("Marou dark chocolate");
  await query.fill("   ");
  await expect(page.getByRole("button", { name: "Tìm theo câu này" })).toBeDisabled();
  await page.getByRole("button", { name: "Hủy", exact: true }).click();
  await expect(page.getByRole("region", { name: "Xác nhận bản chép lời" })).toHaveCount(0);
  expect(searches).toBe(0);
});

test("failed confirmed search retains editable transcript for retry", async ({ page, allowConsoleErrors }) => {
  allowConsoleErrors();
  let fail = true;
  await page.route("**/api/search", async (route) => {
    if (fail) await route.fulfill({ status: 503, json: { detail: { message: "Hãy thử lại", code: "busy" } } });
    else await route.continue();
  });
  await page.goto("/");
  await record(page);
  await page.getByRole("textbox", { name: "Cụm từ dùng để tìm kiếm" }).fill("khăn lụa");
  await page.getByRole("button", { name: "Tìm theo câu này" }).click();
  await expect(page.getByText("Hãy thử lại", { exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Cụm từ dùng để tìm kiếm" })).toHaveValue("khăn lụa");
  fail = false;
  await page.getByRole("button", { name: "Tìm theo câu này" }).click();
  await expect(cardTitles(page)).toHaveText(["Khăn lụa tơ tằm màu đỏ"]);
});
