// Mô-típ vector (assets/design-elements/nep-viet-v2/svg): sen, tre, nan nón, mặt nước, đường chia.
// Tất cả trang trí: aria-hidden, không nhận focus. Màu theo currentColor của phần tử cha.

export function LotusMark({ size = 24, className = "" }: { size?: number; className?: string }) {
  return (
    <svg className={`lotus-mark ${className}`} width={size} height={size} viewBox="0 0 48 48" aria-hidden="true"
      focusable="false" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <g className="petal-center"><path d="M24 39C12 30 13 17 24 6c11 11 12 24 0 33Z" /></g>
      <g className="petal-left"><path d="M24 39C10 39 4 28 5 15c12 2 19 12 19 24Z" /></g>
      <g className="petal-right"><path d="M24 39c14 0 20-11 19-24-12 2-19 12-19 24Z" /></g>
      <path d="M5 32c4 11 12 12 19 10 7 2 15 1 19-10" />
    </svg>
  );
}

export function BambooLines({ className = "" }: { className?: string }) {
  return (
    <svg className={`bamboo-lines ${className}`} viewBox="0 0 360 480" aria-hidden="true" focusable="false" fill="none"
      stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <g className="stems" strokeWidth={3}>
        <path d="M278 461q-24-193-45-433M296 461q-6-140 12-293" />
        <path d="m263 355 14-2m-25-99 14-2m-24-100 14-2m-24-96 14-2m51 296 12 1m-11-85 12 1" strokeWidth={2} />
      </g>
      <g className="leaves-upper" fill="currentColor" stroke="none">
        <path d="M244 159q-62-31-110-95 61 27 110 95ZM204 119q-41 6-77-19 45-5 77 19ZM175 93q-14-43-40-57-3 39 40 57ZM240 140q28-52 76-72-22 48-76 72ZM278 103q10-41 36-59 6 37-36 59Z" />
      </g>
      <g className="leaves-lower" fill="currentColor" stroke="none">
        <path d="M266 313q-67-29-128-64 57 3 128 64ZM207 284q-14-45-42-66 0 40 42 66ZM180 271q-44 11-80-7 40-15 80 7ZM287 353q35-62 62-75-10 47-62 75Z" />
      </g>
    </svg>
  );
}

export function NonLaLines({ className = "" }: { className?: string }) {
  return (
    <svg className={`non-la-lines ${className}`} viewBox="0 0 240 140" aria-hidden="true" focusable="false" fill="none"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <g className="ribs-outline"><path d="M120 17 20 104q100 40 200 0L120 17Z" /><path d="M20 104q100 20 200 0" /></g>
      <g className="ribs-a" opacity=".8"><path d="m120 17-72 94m72-94-30 101m30-101 20 103m-20-103 62 97" /></g>
      <g className="ribs-b" opacity=".5"><path d="M91 42q29 12 58 0M66 64q54 21 108 0M42 85q78 29 156 0" /></g>
    </svg>
  );
}

export function WaterRipple({ className = "" }: { className?: string }) {
  return (
    <svg className={`water-ripple ${className}`} viewBox="0 0 240 80" aria-hidden="true" focusable="false" fill="none"
      stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
      <path d="M100 36c-24 5-5 13 20 13s44-8 20-13" />
      <path d="M75 27c-59 13-24 37 45 37s104-24 45-37" opacity=".65" />
      <path d="M46 17C-6 37 17 75 120 75S246 37 194 17" opacity=".35" />
    </svg>
  );
}

/** Đường chia nhịp đốt tre — dùng ở header công cụ nội bộ và giữa các khối. */
export function BambooDivider({ className = "" }: { className?: string }) {
  return (
    <svg className={`bamboo-divider ${className}`} viewBox="0 0 640 32" preserveAspectRatio="none" aria-hidden="true"
      focusable="false" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
      <path d="M8 16h177m12 0h246m12 0h177" />
      <path d="m184 12 3 8m8-8 3 8m243-8 3 8m8-8 3 8" />
    </svg>
  );
}

export function WeaveDivider({ className = "" }: { className?: string }) {
  return (
    <svg className={`weave-divider ${className}`} viewBox="0 0 320 48" preserveAspectRatio="none" aria-hidden="true"
      focusable="false" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <g opacity=".65">
        <path d="m8 32 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16" />
        <path d="m8 16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16 16 16 16-16" />
      </g>
    </svg>
  );
}

/** Số chương + gạch ngắn: “01 ——”. */
export function ChapterNo({ n }: { n: string }) {
  return <p className="chapter-no" aria-hidden="true"><span>{n}</span></p>;
}
