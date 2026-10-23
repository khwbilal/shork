import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // :8000 has stuck zombie listeners with old code; current API is on :8002.
        target: "http://127.0.0.1:8002",
        changeOrigin: true,
      },
    },
  },
});
