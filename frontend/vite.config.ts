import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API = process.env.VNSTORE_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: API, changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
      "/images": { target: API, changeOrigin: true },
    },
  },
});
