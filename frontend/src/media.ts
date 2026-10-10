// Ghi âm và chuẩn bị ảnh trong trình duyệt trước khi gửi cho API.
// Âm thanh: MediaRecorder → giải mã → 16 kHz mono → WAV PCM 16-bit (backend không cần ffmpeg).
// Ảnh: cắt vùng người dùng chọn, thu nhỏ, mã hóa lại JPEG → bỏ EXIF/GPS trước khi rời máy.

export const MAX_RECORD_SECONDS = 10;
export const TARGET_RATE = 16000;
const MIN_RECORD_MS = 700;
export const MAX_IMAGE_FILE_BYTES = 20 * 1024 * 1024; // ảnh gốc trên máy; ảnh gửi đi nhỏ hơn nhiều
export const MAX_UPLOAD_SIDE = 1024;
export const MIN_IMAGE_SIDE = 32;

export type MicErrorKind = "denied" | "notfound" | "unsupported" | "busy" | "short" | "failed";

export class MicError extends Error {
  constructor(public kind: MicErrorKind, message: string) {
    super(message);
  }
}

const MIC_MESSAGES: Record<MicErrorKind, string> = {
  denied: "Micro đang bị chặn. Hãy cho phép micro cho trang này trong cài đặt trình duyệt, hoặc gõ chữ để tìm.",
  notfound: "Không tìm thấy micro trên thiết bị. Hãy gõ chữ để tìm.",
  unsupported: "Trình duyệt này không hỗ trợ ghi âm (cần HTTPS hoặc trình duyệt mới hơn). Hãy gõ chữ để tìm.",
  busy: "Micro đang được ứng dụng khác sử dụng. Đóng ứng dụng đó rồi thử lại.",
  short: "Đoạn ghi âm quá ngắn. Hãy nói câu tìm rồi mới bấm dừng.",
  failed: "Không ghi âm được. Hãy thử lại hoặc gõ chữ để tìm.",
};

function micError(kind: MicErrorKind) {
  return new MicError(kind, MIC_MESSAGES[kind]);
}

export function canRecord(): boolean {
  // mediaDevices không có trong ngữ cảnh không bảo mật (HTTP ngoài localhost).
  return typeof navigator.mediaDevices?.getUserMedia === "function" && typeof MediaRecorder !== "undefined"
    && typeof AudioContext !== "undefined";
}

/** Một phiên ghi âm: start() xin quyền và bắt đầu ghi; stop() trả WAV; cancel() bỏ. */
export class Recorder {
  private stream: MediaStream | null = null;
  private rec: MediaRecorder | null = null;
  private chunks: Blob[] = [];
  private startedAt = 0;

  async start(): Promise<void> {
    if (!canRecord()) throw micError("unsupported");
    try {
      // Không bật khử ồn mặc định: có thể làm mất phụ âm/dấu thanh (PLAN.md mục 6.2).
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, noiseSuppression: false, echoCancellation: true },
      });
    } catch (e) {
      const name = (e as DOMException)?.name;
      if (name === "NotAllowedError" || name === "SecurityError") throw micError("denied");
      if (name === "NotFoundError" || name === "OverconstrainedError") throw micError("notfound");
      if (name === "NotReadableError" || name === "AbortError") throw micError("busy");
      throw micError("failed");
    }
    this.chunks = [];
    this.rec = new MediaRecorder(this.stream);
    this.rec.ondataavailable = (ev) => ev.data.size > 0 && this.chunks.push(ev.data);
    this.rec.start(250);
    this.startedAt = performance.now();
  }

  async stop(): Promise<Blob> {
    const rec = this.rec;
    if (!rec) throw micError("failed");
    const done = new Promise<void>((resolve) => (rec.onstop = () => resolve()));
    if (rec.state !== "inactive") rec.stop();
    await done;
    this.release();
    if (performance.now() - this.startedAt < MIN_RECORD_MS) throw micError("short");
    const blob = new Blob(this.chunks, { type: rec.mimeType || "audio/webm" });
    if (!blob.size) throw micError("failed");
    return toWav(blob);
  }

  cancel() {
    if (this.rec && this.rec.state !== "inactive") this.rec.stop();
    this.release();
  }

  private release() {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
  }
}

async function toWav(blob: Blob): Promise<Blob> {
  const ctx = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
  } catch {
    throw micError("failed");
  } finally {
    void ctx.close();
  }
  const length = Math.max(1, Math.ceil(decoded.duration * TARGET_RATE));
  const offline = new OfflineAudioContext(1, length, TARGET_RATE);
  const src = offline.createBufferSource();
  src.buffer = decoded; // nhiều kênh được trộn về mono khi nối vào đích 1 kênh
  src.connect(offline.destination);
  src.start();
  const pcm = (await offline.startRendering()).getChannelData(0);
  return encodeWav(pcm, TARGET_RATE);
}

export function encodeWav(samples: Float32Array, rate: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const str = (off: number, s: string) => [...s].forEach((c, i) => v.setUint8(off + i, c.charCodeAt(0)));
  str(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  str(8, "WAVE");
  str(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); // PCM
  v.setUint16(22, 1, true); // mono
  v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  str(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const x = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, x < 0 ? x * 0x8000 : x * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

// ---------- Ảnh ----------

/** Vùng chọn theo tỉ lệ 0..1 của ảnh đã xoay đúng chiều (như ảnh xem trước). */
export interface Crop {
  x: number;
  y: number;
  w: number;
  h: number;
}

export class ImageInputError extends Error {}

const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
export const ACCEPT_ATTR = ACCEPTED.join(",");

export function checkImageFile(file: File): void {
  // Một số máy không gán MIME (để trống) — vẫn thử giải mã; loại rõ ràng các kiểu khác.
  if (file.type && !ACCEPTED.includes(file.type)) {
    throw new ImageInputError("Chỉ nhận ảnh JPEG, PNG hoặc WebP. Ảnh HEIC hãy chuyển sang JPEG trước.");
  }
  if (file.size > MAX_IMAGE_FILE_BYTES) {
    throw new ImageInputError(`Ảnh vượt ${MAX_IMAGE_FILE_BYTES / 1024 / 1024} MB. Hãy chọn ảnh nhỏ hơn.`);
  }
}

export async function decodeImage(file: File): Promise<ImageBitmap> {
  checkImageFile(file);
  let bmp: ImageBitmap;
  try {
    bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    throw new ImageInputError("Ảnh không hợp lệ hoặc bị hỏng. Hãy chọn ảnh khác.");
  }
  if (Math.min(bmp.width, bmp.height) < MIN_IMAGE_SIDE) {
    bmp.close();
    throw new ImageInputError(`Ảnh quá nhỏ (cần tối thiểu ${MIN_IMAGE_SIDE}px mỗi chiều).`);
  }
  return bmp;
}

/** Cắt + thu nhỏ + mã hóa lại JPEG. Vùng quá nhỏ bị từ chối thay vì phóng to ảnh vỡ. */
export async function prepareImage(bmp: ImageBitmap, crop: Crop | null): Promise<Blob> {
  const c = crop ?? { x: 0, y: 0, w: 1, h: 1 };
  const sx = Math.round(c.x * bmp.width);
  const sy = Math.round(c.y * bmp.height);
  const sw = Math.max(1, Math.round(c.w * bmp.width));
  const sh = Math.max(1, Math.round(c.h * bmp.height));
  if (Math.min(sw, sh) < MIN_IMAGE_SIDE) throw new ImageInputError("Vùng chọn quá nhỏ. Hãy chọn vùng lớn hơn.");
  const scale = Math.min(1, MAX_UPLOAD_SIDE / Math.max(sw, sh));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(sw * scale);
  canvas.height = Math.round(sh * scale);
  const g = canvas.getContext("2d");
  if (!g) throw new ImageInputError("Trình duyệt không xử lý được ảnh.");
  g.fillStyle = "#fff"; // nền trắng cho ảnh PNG trong suốt
  g.fillRect(0, 0, canvas.width, canvas.height);
  g.drawImage(bmp, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", 0.9));
  if (!blob) throw new ImageInputError("Không mã hóa được ảnh.");
  return blob;
}
