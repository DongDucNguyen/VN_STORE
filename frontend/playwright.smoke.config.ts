import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Opt-in local model integration, never part of the fixture suite or a quality benchmark.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = path.join(ROOT, process.env.VNSTORE_SMOKE_ML_VENV || ".venv-ml",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const externalServers = process.env.VNSTORE_SMOKE_EXTERNAL_SERVERS === "1";
const audio = path.join(ROOT, "artifacts/voice_smoke/fleurs-vi-dev/raw/fleurs-10056093347220194289.wav");
export default defineConfig({
  testDir: "./smoke", workers: 1, retries: 0, timeout: 120_000,
  outputDir: "../artifacts/stage6-smoke", reporter: "line",
  use: { baseURL: "http://127.0.0.1:5181", locale: "vi-VN", permissions: ["microphone"],
    launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
      `--use-file-for-fake-audio-capture=${audio}`] } },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], channel: "chrome" } },
             { name: "mobile", use: { ...devices["Pixel 7"], channel: "chrome" } }],
  webServer: externalServers ? [] : [
    { command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8011`, cwd: path.join(ROOT, "backend"),
      env: { VNSTORE_CATALOG: path.join(ROOT, "database.json"), VNSTORE_INCLUDE_DRAFTS: "1",
        VNSTORE_ASR_ADAPTER: "app.ml.asr:PhoWhisperSmall", VNSTORE_IMAGE_ADAPTER: "app.ml.image:SigLIP2Base",
        VNSTORE_IMAGE_INDEX_DIR: path.join(ROOT, "artifacts/indexes/image"), VNSTORE_IMAGE_INDEX_AUTOBUILD: "0",
        VNSTORE_SEARCH_CONFIG: '{"ocr_weight":0.35}', VNSTORE_OCR: "rapidocr-latin", VNSTORE_IMAGE_MULTI_VIEW: "1",
        VNSTORE_ML_DEVICE: process.env.VNSTORE_ML_DEVICE || "auto", VNSTORE_ML_TRT: "0",
        VNSTORE_ASR_VAD: "1", VNSTORE_VAD_THRESHOLD: "0.5",
        VNSTORE_VAD_MIN_MS: "250", VNSTORE_SILENCE_DBFS: "-60", VNSTORE_ASR_MAX_NEW_TOKENS: "96",
        VNSTORE_CORS_ORIGINS: "http://127.0.0.1:5181" },
      url: "http://127.0.0.1:8011/health", reuseExistingServer: false, timeout: 60_000 },
    { command: "npx vite --host 127.0.0.1 --port 5181 --strictPort", env: { VNSTORE_API: "http://127.0.0.1:8011" },
      url: "http://127.0.0.1:5181", reuseExistingServer: false, timeout: 60_000 },
  ],
});
