import { test, expect } from "./fixtures";

// Inject device failures while retaining the real browser MediaStream. These
// checks exercise shared Recorder behavior used by search and sample collection.
test("recorder start failure releases the microphone", async ({ page }) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    // @ts-expect-error Vite serves this TypeScript module in the test browser.
    const { Recorder } = await import("/src/media.ts");
    const original = MediaRecorder.prototype.start;
    const getMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    let stream: MediaStream | undefined;
    navigator.mediaDevices.getUserMedia = async (constraints) => (stream = await getMedia(constraints));
    MediaRecorder.prototype.start = () => { throw new DOMException("device failure"); };
    let failed = false;
    try { await new Recorder().start(); } catch { failed = true; }
    finally { MediaRecorder.prototype.start = original; }
    return { failed, states: stream?.getTracks().map((track) => track.readyState) };
  });
  expect(result.failed).toBe(true);
  expect(result.states).toEqual(["ended"]);
});

test("device stops before user: stop settles instead of hanging", async ({ page }) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    // @ts-expect-error Vite serves this TypeScript module in the test browser.
    const { Recorder } = await import("/src/media.ts");
    const NativeRecorder = MediaRecorder;
    let native: MediaRecorder | undefined;
    window.MediaRecorder = class extends NativeRecorder {
      constructor(stream: MediaStream) { super(stream); native = this; }
    };
    const recorder = new Recorder();
    await recorder.start();
    await new Promise((resolve) => setTimeout(resolve, 850));
    const stopped = new Promise((resolve) => native!.addEventListener("stop", resolve, { once: true }));
    native!.stop();
    await stopped;
    try {
      return await Promise.race([
        recorder.stop().then((blob: Blob) => blob.type),
        new Promise<string>((resolve) => setTimeout(() => resolve("hung"), 3000)),
      ]);
    } finally { recorder.cancel(); window.MediaRecorder = NativeRecorder; }
  });
  expect(result).toBe("audio/wav");
});

test("async recorder failure releases tracks and reports an error", async ({ page }) => {
  await page.goto("/");
  const result = await page.evaluate(async () => {
    // @ts-expect-error Vite serves this TypeScript module in the test browser.
    const { Recorder } = await import("/src/media.ts");
    const NativeRecorder = MediaRecorder;
    let native: MediaRecorder | undefined;
    let stream: MediaStream | undefined;
    window.MediaRecorder = class extends NativeRecorder {
      constructor(input: MediaStream) { super(input); native = this; stream = input; }
    };
    const recorder = new Recorder();
    await recorder.start();
    // Pass the minimum recording duration so a short-recording error cannot
    // accidentally satisfy this test without handling the device error.
    await new Promise((resolve) => setTimeout(resolve, 850));
    native!.dispatchEvent(new Event("error"));
    const statesBeforeStop = stream!.getTracks().map((track) => track.readyState);
    let failed = false;
    try { await recorder.stop(); } catch { failed = true; }
    finally { recorder.cancel(); window.MediaRecorder = NativeRecorder; }
    return { failed, statesBeforeStop, states: stream?.getTracks().map((track) => track.readyState) };
  });
  expect(result).toEqual({ failed: true, statesBeforeStop: ["ended"], states: ["ended"] });
});
