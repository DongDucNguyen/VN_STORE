// Yêu thích lưu trên thiết bị (localStorage), không cần tài khoản.
import { useCallback, useEffect, useState } from "react";

const KEY = "vnstore:favorites";
const EVENT = "vnstore:favorites-changed";

function read(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function write(ids: string[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    /* chế độ riêng tư: bỏ qua */
  }
  window.dispatchEvent(new Event(EVENT));
}

export function useFavorites() {
  const [ids, setIds] = useState<string[]>(read);
  useEffect(() => {
    const sync = () => setIds(read());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  const toggle = useCallback((id: string) => {
    const cur = read();
    write(cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]);
  }, []);
  return { ids, has: (id: string) => ids.includes(id), toggle };
}
