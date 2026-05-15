import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.BACKEND_URL || "http://localhost:8000";

  const proxyOptions = {
    target: backendUrl,
    changeOrigin: true,
    timeout: 0,
    proxyTimeout: 0,
  };

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      watch: {
        usePolling: true,
        interval: 300,
      },
      proxy: {
        "/campaigns": proxyOptions,
        "/health": proxyOptions,
        "/voice": proxyOptions,
      },
    },
    preview: {
      host: true,
      port: 5173,
    },
  };
});
