// Tùy chọn giao diện lưu trên thiết bị: theme (Theo hệ thống/Sáng/Tối) và chuyển động (Theo hệ thống/Giảm).
// Không liên quan tới mức đồng ý lưu dữ liệu của trợ lý. Hệ điều hành yêu cầu giảm chuyển động thì luôn giảm.
import { useCallback, useEffect, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";
export type MotionChoice = "system" | "reduce";

const THEME_KEY = "vnstore:theme";
const MOTION_KEY = "vnstore:motion";
const EVENT = "vnstore:prefs-changed";

function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;
  } catch {
    return fallback;
  }
}

function store(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

const systemReduce = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

export function prefersReducedMotion(): boolean {
  return systemReduce() || document.documentElement.dataset.motion === "reduce";
}

/** Gắn lựa chọn đã lưu lên <html> trước lần vẽ đầu (gọi từ main.tsx). */
export function applyStoredPrefs() {
  const root = document.documentElement;
  const theme = read<ThemeChoice>(THEME_KEY, ["system", "light", "dark"], "system");
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  if (read<MotionChoice>(MOTION_KEY, ["system", "reduce"], "system") === "reduce") root.dataset.motion = "reduce";
  else delete root.dataset.motion;
}

export function usePreferences() {
  const [theme, setThemeState] = useState<ThemeChoice>(() => read<ThemeChoice>(THEME_KEY, ["system", "light", "dark"], "system"));
  const [motion, setMotionState] = useState<MotionChoice>(() => read<MotionChoice>(MOTION_KEY, ["system", "reduce"], "system"));
  const [saveFailed, setSaveFailed] = useState(false);

  useEffect(() => {
    const sync = () => {
      setThemeState(read<ThemeChoice>(THEME_KEY, ["system", "light", "dark"], "system"));
      setMotionState(read<MotionChoice>(MOTION_KEY, ["system", "reduce"], "system"));
    };
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);

  const setTheme = useCallback((v: ThemeChoice) => {
    setSaveFailed(!store(THEME_KEY, v));
    const root = document.documentElement;
    if (v === "system") delete root.dataset.theme;
    else root.dataset.theme = v;
    setThemeState(v);
    window.dispatchEvent(new Event(EVENT));
  }, []);

  const setMotion = useCallback((v: MotionChoice) => {
    setSaveFailed(!store(MOTION_KEY, v));
    const root = document.documentElement;
    if (v === "reduce") root.dataset.motion = "reduce";
    else delete root.dataset.motion;
    // Hủy các animation trang trí đang chạy ngay khi người dùng chọn giảm.
    if (v === "reduce") document.getAnimations?.().forEach((a) => a.finish());
    setMotionState(v);
    window.dispatchEvent(new Event(EVENT));
  }, []);

  return { theme, motion, setTheme, setMotion, saveFailed, systemReduce: systemReduce() };
}
