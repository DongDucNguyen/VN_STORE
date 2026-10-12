import zlib from "node:zlib";
import type { Page } from "@playwright/test";
import { cards, cardTitles, expect, test } from "./fixtures";

// Backend E2E dùng adapter GIẢ (backend/tests/fakes.py): FakeASR luôn trả
// "tìm cho mình cái túi cói dưới ba trăm nghìn"; embedder ảnh là histogram byte, không hiểu nội dung.
// Các test này kiểm tra luồng giao diện/API, không đo chất lượng model.
const TRANSCRIPT = "tìm cho mình cái túi cói dưới ba trăm nghìn";

function png(width = 240, height = 160): Buffer {
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
    for (let x = 0; x < width; x++) row.set([(x * 255) / width, (y * 255) / height, 90], 1 + x * 3);
    rows.push(row);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(Buffer.concat(rows))),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

async function mockModelState(page: Page, kind: "voice" | "image", state: string, reason: string) {
  await page.route("**/api/health", async (route) => {
    const res = await route.fetch();
    const body = await res.json();
    body.search[kind] = state;
    body.search.models[kind] = { state, model_id: null, revision: null, detail: null, reason };
    await route.fulfill({ response: res, json: body });
  });
}

test.describe("Tìm bằng giọng nói", () => {
  test("ghi âm → bản chép lời sửa được → kết quả và bộ lọc giá", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await expect(page.getByText("Đang nghe…")).toBeVisible();
    await expect(page.getByRole("button", { name: "Dừng ghi âm" })).toBeVisible();
    await page.waitForTimeout(1200);
    const answered = page.waitForResponse("**/api/search/voice*");
    await page.getByRole("button", { name: "Dừng và xem lời" }).click();
    const res = await answered;
    expect(res.request().headers()["content-type"]).toBe("audio/wav");
    // Backend giải mã được WAV do trình duyệt mã hóa và đo đúng thời lượng đã ghi.
    expect(res.status()).toBe(200);
    expect((await res.json()).transcript.duration_s).toBeGreaterThan(0.8);

    await expect(page.getByRole("textbox", { name: "Cụm từ dùng để tìm kiếm" })).toHaveValue(TRANSCRIPT);
    await page.getByRole("button", { name: "Tìm theo câu này" }).click();
    await expect(page).toHaveURL(/via=voice/);
    await expect(page.getByText(/Đã chép lời từ giọng nói/)).toBeVisible();
    const box = page.getByRole("searchbox", { name: "Tìm sản phẩm" });
    await expect(box).toHaveValue(TRANSCRIPT);
    await expect(page.getByText("Giá dưới 300.000đ")).toBeVisible();
    await expect(cardTitles(page)).toHaveText(["Túi cói quai da"]);

    // Sửa bản chép lời rồi tìm lại bằng chữ.
    await box.fill("túi cói");
    await box.press("Enter");
    await expect(page.getByText(/Đã chép lời từ giọng nói/)).toHaveCount(0);
    await expect(cards(page)).toHaveCount(3);
  });

  test("bấm dừng ngay: báo quá ngắn, không gửi", async ({ page }) => {
    let sent = false;
    page.on("request", (r) => r.url().includes("/api/search/voice") && (sent = true));
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await page.getByRole("button", { name: "Dừng và xem lời" }).click();
    await expect(page.getByRole("alert")).toContainText("quá ngắn");
    expect(sent).toBe(false);
  });

  test("hủy ghi âm không gửi gì", async ({ page }) => {
    let sent = false;
    page.on("request", (r) => r.url().includes("/api/search/voice") && (sent = true));
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await expect(page.getByText("Đang nghe…")).toBeVisible();
    await page.getByRole("button", { name: "Hủy" }).click();
    await expect(page.getByText("Đang nghe…")).toHaveCount(0);
    expect(sent).toBe(false);
  });

  test("micro bị từ chối: hướng dẫn và cho ghi lại", async ({ page }) => {
    await page.addInitScript(() => {
      navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException("denied", "NotAllowedError"));
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("Micro đang bị chặn");
    await expect(alert.getByRole("button", { name: "Ghi lại" })).toBeVisible();
    await alert.getByRole("button", { name: "Đóng" }).click();
    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("trình duyệt không hỗ trợ ghi âm", async ({ page }) => {
    await page.addInitScript(() => {
      // @ts-expect-error mô phỏng trình duyệt cũ
      delete window.MediaRecorder;
    });
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await expect(page.getByRole("alert")).toContainText("không hỗ trợ ghi âm");
    await expect(page.getByRole("button", { name: "Ghi lại" })).toHaveCount(0);
  });

  test("máy chủ báo không nghe thấy tiếng nói", async ({ page, allowConsoleErrors }) => {
    allowConsoleErrors(); // 422 có chủ đích
    await page.route("**/api/search/voice*", (route) =>
      route.fulfill({ status: 422, json: { detail: { code: "audio_silent",
        message: "Không nghe thấy tiếng nói. Kiểm tra micro rồi ghi lại." } } }));
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await expect(page.getByText("Đang nghe…")).toBeVisible();
    await page.waitForTimeout(1000);
    await page.getByRole("button", { name: "Dừng và xem lời" }).click();
    await expect(page.getByRole("alert")).toContainText("Không nghe thấy tiếng nói");
    await page.getByRole("button", { name: "Ghi lại" }).click();
    await expect(page.getByText("Đang nghe…")).toBeVisible();
  });
});

test.describe("Tìm bằng ảnh", () => {
  async function pickImage(page: Page, file = { name: "gio.png", mimeType: "image/png", buffer: png() }) {
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng ảnh" }).click();
    await expect(page).toHaveURL(/#\/image/);
    await page.getByLabel("Chọn ảnh từ máy").setInputFiles(file);
  }

  test("chọn ảnh + yêu cầu giá → mẫu tương tự đúng bộ lọc cứng", async ({ page }) => {
    await pickImage(page);
    await expect(page.getByRole("img", { name: "Ảnh bạn chọn để tìm" })).toBeVisible();
    await page.getByLabel("Yêu cầu thêm").fill("dưới 400k");
    const sent = page.waitForRequest("**/api/search/image?*");
    await page.getByRole("button", { name: "Tìm mẫu tương tự" }).click();
    const req = await sent;
    expect(req.headers()["content-type"]).toBe("image/jpeg"); // đã mã hóa lại, bỏ metadata
    expect(new URL(req.url()).searchParams.get("text")).toBe("dưới 400k");

    await expect(page.getByRole("heading", { name: "Mẫu tương tự" })).toBeVisible();
    const interpret = page.getByRole("region", { name: "Cách hệ thống hiểu truy vấn" });
    await expect(interpret.getByText("Giá dưới 400.000đ")).toBeVisible();
    await expect(interpret.getByText(/không khẳng định đúng sản phẩm/)).toBeVisible();
    await expect(cards(page).first()).toBeVisible();
    for (const over of ["Khăn lụa", "Hộp sơn mài", "Lọ hoa gốm men rạn"]) {
      await expect(cardTitles(page).filter({ hasText: over })).toHaveCount(0);
    }
  });

  test("bộ lọc sau khi có kết quả: gửi lại cùng ảnh kèm bộ lọc, gỡ được", async ({ page }) => {
    await pickImage(page);
    await page.getByRole("button", { name: "Tìm mẫu tương tự" }).click();
    await expect(cards(page).first()).toBeVisible();
    const panel = page.locator("details.filters");
    if (!(await panel.evaluate((d) => (d as HTMLDetailsElement).open))) await panel.locator("summary").click();
    const sent = page.waitForRequest((r) => r.url().includes("/api/search/image") && r.url().includes("filters="));
    await panel.getByRole("checkbox", { name: /^cói/ }).check();
    const req = await sent;
    expect(JSON.parse(new URL(req.url()).searchParams.get("filters")!).materials).toEqual(["cói"]);
    expect(new URL(req.url()).searchParams.get("reuse")).toBe("1"); // only filter changes may use server cache
    await expect(page.getByRole("region", { name: "Cách hệ thống hiểu truy vấn" }).getByText("Chất liệu: cói"))
      .toBeVisible();
    await expect(cardTitles(page).filter({ hasText: "Khăn lụa" })).toHaveCount(0);
    await expect(cardTitles(page).filter({ hasText: /Túi cói/ }).first()).toBeVisible();
    await page.getByRole("button", { name: "Xóa bộ lọc" }).click();
    await expect(page.getByRole("button", { name: "Xóa bộ lọc" })).toHaveCount(0);
    await expect(cards(page).first()).toBeVisible();
  });

  test("kéo để chọn vùng rồi bỏ vùng chọn", async ({ page }) => {
    await pickImage(page);
    const box = page.getByTestId("crop-box");
    await expect(box).toBeVisible();
    const b = (await box.boundingBox())!;
    await page.mouse.move(b.x + b.width * 0.2, b.y + b.height * 0.2);
    await page.mouse.down();
    await page.mouse.move(b.x + b.width * 0.7, b.y + b.height * 0.8, { steps: 5 });
    await page.mouse.up();
    await expect(page.getByText("Đã chọn vùng.")).toBeVisible();
    await page.getByRole("button", { name: "Tìm mẫu tương tự" }).click();
    await expect(cards(page).first()).toBeVisible();
    await page.getByRole("button", { name: /Bỏ vùng chọn/ }).click();
    await expect(page.getByText(/Đang dùng cả ảnh/)).toBeVisible();
  });

  test("file hỏng hoặc sai định dạng bị chặn trước khi gửi", async ({ page }) => {
    let sent = false;
    page.on("request", (r) => r.url().includes("/api/search/image") && (sent = true));
    await pickImage(page, { name: "hong.png", mimeType: "image/png", buffer: Buffer.from("không phải ảnh") });
    await expect(page.getByRole("alert")).toContainText("Ảnh không hợp lệ hoặc bị hỏng");
    await page.getByLabel("Chọn ảnh từ máy").setInputFiles({ name: "a.gif", mimeType: "image/gif",
                                                             buffer: Buffer.from("GIF89a") });
    await expect(page.getByRole("alert")).toContainText("Chỉ nhận ảnh JPEG, PNG hoặc WebP");
    await expect(page.getByRole("button", { name: "Tìm mẫu tương tự" })).toHaveCount(0);
    expect(sent).toBe(false);
  });

  test("model ảnh chưa sẵn sàng: báo rõ, không cho gửi", async ({ page }) => {
    await mockModelState(page, "image", "index_missing", "chưa dựng chỉ mục ảnh cho model này");
    await pickImage(page);
    await expect(page.getByText(/Tìm bằng ảnh chưa sẵn sàng: chưa dựng chỉ mục ảnh/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Tìm mẫu tương tự" })).toBeDisabled();
  });
});
