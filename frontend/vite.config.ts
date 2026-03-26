import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repoDocs = path.resolve(process.cwd(), "../docs");

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@docs": repoDocs,
    },
  },
  server: {
    port: 5173,
    fs: {
      allow: [path.resolve(process.cwd(), "..")],
    },
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_API || "http://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,
      },
      "/ws": {
        target: process.env.VITE_PROXY_API || "http://127.0.0.1:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
