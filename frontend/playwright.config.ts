import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

// E2E chạy trên dữ liệu FIXTURE giả, cổng riêng để không đụng server đang phát triển.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const API_PORT = 8010;
const WEB_PORT = 5180;
const PYTHON = process.platform === "win32"
  ? path.join(ROOT, ".venv", "Scripts", "python.exe")
  : path.join(ROOT, ".venv", "bin", "python");
// Mặc định dùng Chrome đã cài trên máy; đặt PW_CHANNEL="" để dùng Chromium của Playwright.
const channel = process.env.PW_CHANNEL ?? "chrome";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // Giới hạn tải Chrome trên máy phát triển; CLI --workers vẫn có thể ghi đè.
  workers: 2,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { outputFolder: "../artifacts/e2e-report", open: "never" }]],
  outputDir: "../artifacts/e2e-results",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    locale: "vi-VN",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel: channel || undefined } },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: channel || undefined } },
  ],
  webServer: [
    {
      command: `"${PYTHON}" -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: path.join(ROOT, "backend"),
      env: {
        VNSTORE_CATALOG: path.join(ROOT, "backend", "tests", "fixtures", "catalog.fixture.json"),
        VNSTORE_CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT}`,
      },
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npx vite --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      env: { VNSTORE_API: `http://127.0.0.1:${API_PORT}` },
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
