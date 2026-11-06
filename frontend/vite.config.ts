import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API = process.env.API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The frontend calls /api/* and Vite forwards it to FastAPI, so no
    // absolute backend URL is baked into the bundle during development.
    proxy: {
      "/api": { target: API, changeOrigin: true },
      "/health": { target: API, changeOrigin: true },
    },
  },
});
