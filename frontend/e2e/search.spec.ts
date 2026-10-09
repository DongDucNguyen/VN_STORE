import { cards, cardTitles, expect, search, test } from "./fixtures";

test.describe("Tìm kiếm keyword — ba hành trình trong PLAN.md", () => {
  test("hành trình 1: gõ không dấu, hiểu giá và làng nghề", async ({ page }) => {
    await page.goto("/");
    await search(page, "binh gom bat trang duoi 500k");

    await expect(page).toHaveURL(/#\/search\?q=binh/);
    const interpret = page.getByRole("region", { name: "Cách hệ thống hiểu truy vấn" });
    await expect(interpret.getByText("Giá dưới 500.000đ")).toBeVisible();
    await expect(cardTitles(page).first()).toHaveText("Bình gốm men lam vẽ sen");
    // Lọ 680k vượt giá không được xuất hiện.
    await expect(cardTitles(page).filter({ hasText: "Lọ hoa gốm men rạn" })).toHaveCount(0);

    // Xác nhận gợi ý làng nghề thành bộ lọc.
    const chip = interpret.getByRole("button", { name: "+ Bát Tràng" });
    await chip.click();
    await expect(page).toHaveURL(/place=lang-gom-bat-trang/);
    await expect(interpret.getByRole("button", { name: "✓ Bát Tràng" })).toHaveAttribute("aria-pressed", "true");
    await expect(interpret.getByText("Nơi sản xuất: Bát Tràng")).toBeVisible();
    await expect(cardTitles(page)).toHaveText(["Bình gốm men lam vẽ sen"]);
  });

  test("hành trình 2: câu nói tự nhiên, giá bằng chữ", async ({ page }) => {
    await page.goto("/");
    await search(page, "tìm cho mình cái túi cói dưới ba trăm nghìn");

    await expect(page.getByText("Giá dưới 300.000đ")).toBeVisible();
    await expect(cardTitles(page)).toHaveText(["Túi cói quai da"]);
    // Túi chưa có giá bị loại và được thông báo, không bị coi là 0đ.
    await expect(page.getByText(/1 sản phẩm phù hợp chưa có giá/)).toBeVisible();
    await expect(page.getByText(/Từ khóa:\s*túi cói/)).toBeVisible();
  });

  test("hành trình 3 (phần chữ): giỏ có quai dưới 400k", async ({ page }) => {
    await page.goto("/#/search?q=" + encodeURIComponent("giỏ có quai dưới 400k"));
    await expect(cardTitles(page).first()).toHaveText("Giỏ mây có quai xách");
  });

  test("phủ định là hard filter", async ({ page }) => {
    await page.goto("/#/search?q=" + encodeURIComponent("giỏ không lấy nhựa"));
    await expect(page.getByText("Không lấy chất liệu nhựa")).toBeVisible();
    await expect(cards(page).first()).toBeVisible();
    await expect(cardTitles(page).filter({ hasText: "nhựa" })).toHaveCount(0);
  });

  test("không có kết quả thì giải thích ràng buộc đang hạn chế", async ({ page }) => {
    await page.goto("/#/search?q=" + encodeURIComponent("khăn trừ màu đỏ"));
    await expect(page.getByText("Không tìm thấy sản phẩm phù hợp.")).toBeVisible();
    await expect(page.getByText(/Không lấy màu đỏ.*→ 1 kết quả/)).toBeVisible();
  });

  test("bộ lọc người dùng cập nhật URL và kết quả, gỡ được khi rỗng", async ({ page }) => {
    await page.goto("/#/search");
    await expect(cards(page).first()).toBeVisible();
    const filters = page.locator("details.filters");
    const isOpen = () => filters.evaluate((el) => (el as HTMLDetailsElement).open);
    if (!(await isOpen())) await filters.locator("summary").click();

    await filters.getByRole("checkbox", { name: /Túi đan/ }).check();
    await expect(page).toHaveURL(/cat=may-tre-coi-tui/);
    await expect(cards(page)).toHaveCount(3);
    // Panel vẫn mở sau khi chọn (trước đây tự đóng trên điện thoại).
    expect(await isOpen()).toBe(true);
    await expect(filters.getByRole("checkbox", { name: /Túi đan/ })).toBeChecked();

    await filters.getByPlaceholder("Đến").fill("300000");
    await filters.getByRole("button", { name: "Áp dụng" }).click();
    await expect(page).toHaveURL(/pmax=300000/);
    await expect(cardTitles(page)).toHaveText(["Túi cói quai da"]);

    await filters.getByPlaceholder("Đến").fill("100000");
    await filters.getByRole("button", { name: "Áp dụng" }).click();
    await expect(page.getByText("Không tìm thấy sản phẩm phù hợp.")).toBeVisible();
    await page.getByRole("button", { name: /Bỏ “Giá tối đa 100.000đ”/ }).click();
    await expect(page).not.toHaveURL(/pmax=/);
    await expect(cards(page)).toHaveCount(3);

    await page.getByRole("button", { name: "Xóa bộ lọc" }).click();
    await expect(page).not.toHaveURL(/cat=/);
  });

  test("nút Back của trình duyệt trả lại bộ lọc trước đó", async ({ page }) => {
    await page.goto("/#/search?q=" + encodeURIComponent("túi cói"));
    await expect(cards(page)).toHaveCount(3);
    await page.getByRole("region", { name: "Cách hệ thống hiểu truy vấn" })
      .getByRole("button", { name: "+ Túi đan" }).click();
    await expect(page).toHaveURL(/cat=may-tre-coi-tui/);
    await page.goBack();
    await expect(page).not.toHaveURL(/cat=/);
    await expect(page.getByRole("region", { name: "Cách hệ thống hiểu truy vấn" })
      .getByRole("button", { name: "+ Túi đan" })).toBeVisible();
    await page.goForward();
    await expect(page).toHaveURL(/cat=may-tre-coi-tui/);
  });

  test("gợi ý khi gõ và điều hướng bằng bàn phím", async ({ page }) => {
    await page.goto("/");
    const box = page.getByRole("searchbox", { name: "Tìm sản phẩm" });
    await box.fill("son mai");
    const list = page.getByRole("listbox");
    await expect(list.getByRole("option").first()).toBeVisible();
    await expect(list).toContainText("Hộp sơn mài khảm trứng");
    await list.getByRole("link", { name: /Hộp sơn mài khảm trứng/ }).click();
    await expect(page).toHaveURL(/#\/p\/fx-hop-son-mai/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Hộp sơn mài khảm trứng");
  });

  test("giọng nói và ảnh báo chưa sẵn sàng, tìm chữ vẫn chạy", async ({ page, allowConsoleErrors }) => {
    allowConsoleErrors(); // API trả 503 có chủ đích; trình duyệt tự log lỗi tải tài nguyên
    await page.goto("/");
    await page.getByRole("button", { name: "Tìm bằng giọng nói" }).click();
    await expect(page.getByText(/Tìm bằng giọng nói chưa sẵn sàng/)).toBeVisible();
    await page.getByRole("button", { name: "Đóng" }).click();
    await page.getByRole("button", { name: "Tìm bằng ảnh" }).click();
    await expect(page.getByText(/Tìm bằng ảnh chưa sẵn sàng/)).toBeVisible();
    await search(page, "túi cói");
    await expect(cards(page).first()).toBeVisible();
  });

  test("lỗi mạng hiện thông báo và thử lại được", async ({ page, allowConsoleErrors }) => {
    allowConsoleErrors();
    let fail = true;
    await page.route("**/api/search", (route) => (fail ? route.abort() : route.continue()));
    await page.goto("/#/search?q=" + encodeURIComponent("túi cói"));
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("Không kết nối được máy chủ");
    fail = false;
    await alert.getByRole("button", { name: "Thử lại" }).click();
    await expect(cards(page).first()).toBeVisible();
  });
});
