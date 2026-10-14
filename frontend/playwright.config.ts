import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
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

// Micro giả của Chrome phát lặp file WAV này (âm 440 Hz, không phải giọng người).
const FAKE_AUDIO = path.join(ROOT, "artifacts", "e2e-media", "tone-440hz.wav");
function writeTone(file: string, seconds = 3, rate = 16000) {
  const n = seconds * rate;
  const buf = Buffer.alloc(44 + n * 2);
  buf.write("RIFF", 0);
  buf.writeUInt32LE(36 + n * 2, 4);
  buf.write("WAVEfmt ", 8);
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);
  buf.writeUInt16LE(1, 22);
  buf.writeUInt32LE(rate, 24);
  buf.writeUInt32LE(rate * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write("data", 36);
  buf.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) buf.writeInt16LE(Math.round(0.3 * 32767 * Math.sin((2 * Math.PI * 440 * i) / rate)), 44 + i * 2);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, buf);
}
if (!fs.existsSync(FAKE_AUDIO)) writeTone(FAKE_AUDIO);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // Two Chrome workers intermittently exhaust Windows network buffers on this
  // demo machine (ERR_NO_BUFFER_SPACE). Keep local checks reproducible; CI or a
  // larger machine can opt in to concurrency with CLI --workers.
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { outputFolder: "../artifacts/e2e-report", open: "never" }]],
  outputDir: "../artifacts/e2e-results",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    locale: "vi-VN",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    permissions: ["microphone"],
    launchOptions: {
      args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
             `--use-file-for-fake-audio-capture=${FAKE_AUDIO}`],
    },
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
        // Adapter GIẢ (backend/tests/fakes.py) để kiểm thử luồng voice/ảnh; không phải model.
        VNSTORE_ASR_ADAPTER: "tests.fakes:FakeASR",
        VNSTORE_IMAGE_ADAPTER: "tests.fakes:ByteHistogramEmbedder",
        VNSTORE_IMAGE_INDEX_DIR: path.join(ROOT, "artifacts", "e2e-indexes"),
        VNSTORE_IMAGE_INDEX_AUTOBUILD: "1",
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
