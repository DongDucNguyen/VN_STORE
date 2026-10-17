// Icon tác vụ SVG 24px, nét 1.75 đầu tròn (assets/design-elements/nep-viet-v2/svg/icon-*.svg).
// Luôn aria-hidden: tên truy cập đặt trên nút/link chứa icon.

const PATHS = {
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
  microphone: <><rect x="9" y="2" width="6" height="13" rx="3" /><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8" /></>,
  camera: <><path d="M3 6h4l2-3h6l2 3h4v15H3z" /><circle cx="12" cy="13" r="4" /></>,
  heart: <path d="M12 21 3.5 12.5C-2 6.5 6 0 12 6c6-6 14 .5 8.5 6.5Z" />,
  chat: <><path d="M21 3H3v15h5l4 4v-4h9z" /><path d="M7 8h10M7 12h7" /></>,
  menu: <path d="M3 5h18M3 12h18M3 19h18" />,
  close: <path d="m5 5 14 14M19 5 5 19" />,
  arrow: <path d="M3 12h18m-7-7 7 7-7 7" />,
  filter: <path d="M3 5h18M6 12h12M9 19h6" />,
  check: <path d="m4 12 5 5L20 6" />,
  home: <path d="m2 11 10-9 10 9M5 9v13h5v-8h4v8h5V9" />,
  source: <path d="M14 3h7v7m0-7L10 14M10 5H3v16h16v-7" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="1.5" />,
  image: <><rect x="3" y="4" width="18" height="16" rx="1.5" /><circle cx="9" cy="10" r="2" /><path d="m21 16-5-5-9 9" /></>,
  chevron: <path d="m6 9 6 6 6-6" />,
  alert: <><path d="M12 3 2 20h20Z" /><path d="M12 10v4m0 3v.01" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8v.01" /></>,
  refresh: <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" />,
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20, filled = false, className }: {
  name: IconName; size?: number; filled?: boolean; className?: string;
}) {
  return (
    <svg className={`icon ${className ?? ""}`} width={size} height={size} viewBox="0 0 24 24" aria-hidden="true"
      focusable="false" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      {PATHS[name]}
    </svg>
  );
}
