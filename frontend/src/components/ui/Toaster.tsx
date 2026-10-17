import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

const EVENT = "vnstore:toast";

export interface ToastInput { text: string; action?: { label: string; href: string } }
interface ToastItem extends ToastInput { id: number; leaving: boolean }

/** Thông báo ngắn bằng chữ (ví dụ lưu/bỏ yêu thích). Không thay cho thông báo lỗi cạnh trường nhập. */
export function toast(input: ToastInput) {
  window.dispatchEvent(new CustomEvent<ToastInput>(EVENT, { detail: input }));
}

export function Toaster() {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);
  useEffect(() => {
    const timers = new Set<ReturnType<typeof setTimeout>>();
    const later = (fn: () => void, ms: number) => {
      const t = setTimeout(() => { timers.delete(t); fn(); }, ms);
      timers.add(t);
    };
    const onToast = (e: Event) => {
      const id = ++seq.current;
      const detail = (e as CustomEvent<ToastInput>).detail;
      // Chỉ giữ thông báo mới nhất để không chồng nhiều lớp lên nội dung.
      setItems([{ ...detail, id, leaving: false }]);
      later(() => setItems((xs) => xs.map((x) => (x.id === id ? { ...x, leaving: true } : x))), 2600);
      later(() => setItems((xs) => xs.filter((x) => x.id !== id)), 2900);
    };
    window.addEventListener(EVENT, onToast);
    return () => {
      window.removeEventListener(EVENT, onToast);
      timers.forEach(clearTimeout);
    };
  }, []);
  return (
    <div className="toaster" role="status" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className={`toast ${t.leaving ? "is-leaving" : ""}`}>
          <Icon name="check" size={18} />
          <span>{t.text}</span>
          {t.action && <a href={t.action.href}>{t.action.label}</a>}
        </div>
      ))}
    </div>
  );
}
