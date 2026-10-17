import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Font tự host (OFL, có subset tiếng Việt): Be Vietnam Pro cho giao diện, Newsreader cho tiêu đề lớn.
import "@fontsource/be-vietnam-pro/400.css";
import "@fontsource/be-vietnam-pro/500.css";
import "@fontsource/be-vietnam-pro/600.css";
import "@fontsource/newsreader/400.css";
import "@fontsource/newsreader/500.css";
import App from "./App";
import { applyStoredPrefs } from "./hooks/useMotionPreference";
import "./styles.css";

applyStoredPrefs();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
