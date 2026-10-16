import { expect, test } from "./fixtures";
import type { Page } from "@playwright/test";

// Trợ lý chạy với LLM GIẢ (tests.fakes:FakeLLM): kiểm luồng giao diện/API, không đo chất lượng model.

async function openPanel(page: Page) {
  await page.getByRole("button", { name: "Mở trợ lý mua sắm" }).click();
  const panel = page.getByRole("dialog", { name: "Trợ lý mua sắm" });
  await expect(panel).toBeVisible();
  return panel;
}

async function chooseConsent(page: Page, label: RegExp) {
  const panel = page.getByRole("dialog", { name: "Trợ lý mua sắm" });
  await panel.getByRole("radio", { name: label }).check();
  await panel.getByRole("button", { name: "Lưu lựa chọn" }).click();
  await expect(panel.getByRole("button", { name: "Lưu lựa chọn" })).toHaveCount(0);
}

async function send(page: Page, text: string) {
  const panel = page.getByRole("dialog", { name: "Trợ lý mua sắm" });
  await panel.getByRole("textbox", { name: "Tin nhắn cho trợ lý" }).fill(text);
  await panel.getByRole("button", { name: "Gửi", exact: true }).click();
}

test.describe("Trợ lý mua sắm", () => {
  test("gợi ý có thẻ sản phẩm, lý do, giá từ catalog; so sánh hai món", async ({ page }) => {
    await page.goto("/");
    const panel = await openPanel(page);
    await expect(panel.getByText("Trợ lý có nên lưu cuộc trò chuyện không?")).toBeVisible();
    await chooseConsent(page, /Không lưu/);
    await send(page, "tìm giỏ mây có quai");
    const cards = panel.locator(".chat-card");
    await expect(cards.first()).toBeVisible();
    await expect(cards.first()).toContainText("Giỏ mây có quai xách");
    await expect(cards.first()).toContainText("Vì sao gợi ý");
    await expect(cards.first()).toContainText("360.000đ");
    await expect(panel.getByText(/giá 360\.000đ/)).toBeVisible();
    await panel.getByRole("button", { name: "So sánh #1 và #2" }).click();
    await expect(panel.locator(".chat-compare table")).toBeVisible();
    await expect(panel.locator(".chat-compare")).toContainText("Chất liệu");
  });

  test("hỏi về sản phẩm đang xem: nhận xét theo catalog, nói rõ chưa có đánh giá", async ({ page }) => {
    await page.goto("/#/p/fx-gio-may-co-quai");
    await page.getByRole("button", { name: /Hỏi trợ lý về sản phẩm này/ }).click();
    const panel = page.getByRole("dialog", { name: "Trợ lý mua sắm" });
    await expect(panel.getByText(/Đang hỏi về: Giỏ mây có quai xách/)).toBeVisible();
    await panel.getByRole("button", { name: "Gửi", exact: true }).click();
    const ev = panel.locator(".chat-eval");
    await expect(ev).toBeVisible();
    await expect(ev.getByText("Thông tin từ catalog")).toBeVisible();
    await expect(ev.getByText("Khách hàng nói gì")).toBeVisible();
    await expect(ev.getByText(/chưa có đánh giá nào/i)).toBeVisible();
    await expect(ev.getByText(/Nhận định của trợ lý/)).toBeVisible();
  });

  test("ghi nhớ sở thích qua phiên, xem và xóa dữ liệu", async ({ page }) => {
    await page.goto("/");
    const panel = await openPanel(page);
    await chooseConsent(page, /Lưu lịch sử và ghi nhớ/);
    await send(page, "quà tân gia cho mẹ, giỏ dưới 400k");
    await expect(panel.locator(".chat-card").first()).toBeVisible();
    await panel.getByRole("button", { name: "Cuộc trò chuyện mới" }).click();
    await panel.getByRole("link", { name: "Ghi nhớ" }).click();
    await expect(page.getByRole("heading", { name: "Trợ lý ghi nhớ gì về bạn" })).toBeVisible();
    await expect(page.locator(".facts").first()).toContainText("mẹ");
    await expect(page.locator(".facts").first()).toContainText("tân gia");
    await page.getByRole("button", { name: "Xóa mọi thứ trợ lý biết về tôi" }).click();
    await page.getByRole("button", { name: "Xóa vĩnh viễn" }).click();
    await expect(page.getByText("Đã xóa toàn bộ dữ liệu của bạn.")).toBeVisible();
    await expect(page.getByText("Chưa ghi nhớ gì.")).toBeVisible();
  });

  test("đánh giá sản phẩm: chưa có thì nói chưa có; đánh giá đạt luật được đăng ngay", async ({ page }, info) => {
    // Mỗi project một sản phẩm riêng: hai project dùng chung DB của server E2E.
    const pid = info.project.name === "mobile" ? "fx-bat-su-trang" : "fx-tra-thai-nguyen";
    await page.goto(`/#/p/${pid}`);
    const section = page.locator("section", { has: page.getByRole("heading", { name: "Đánh giá của khách hàng" }) });
    await expect(section.getByText(/chưa có đánh giá nào/i)).toBeVisible();
    await section.getByText("Viết đánh giá").click();
    await section.getByRole("textbox", { name: "Nội dung đánh giá" }).fill("Đóng gói cẩn thận, đúng như mô tả");
    await section.getByRole("button", { name: "Gửi đánh giá" }).click();
    await expect(section.getByText("Cảm ơn bạn. Đánh giá đã được đăng.")).toBeVisible();
    await expect(section.getByText(/từ 1 đánh giá/)).toBeVisible();
    await expect(section.getByText("Đóng gói cẩn thận, đúng như mô tả")).toBeVisible();
  });

  test("đóng/mở bằng nút và phím Esc; câu ngoài phạm vi được đưa về mua sắm", async ({ page }) => {
    await page.goto("/");
    const panel = await openPanel(page);
    await chooseConsent(page, /Không lưu/);
    await send(page, "dự báo thời tiết ngày mai");
    await expect(panel.getByText(/chỉ hỗ trợ tìm và tư vấn sản phẩm/)).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await openPanel(page);
    await page.getByRole("button", { name: "Đóng trợ lý" }).click();
    await expect(page.getByRole("button", { name: "Mở trợ lý mua sắm" })).toBeVisible();
  });
});
