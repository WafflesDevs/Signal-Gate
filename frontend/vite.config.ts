import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/paper": "http://127.0.0.1:8000",
      "/price": "http://127.0.0.1:8000",
      "/chat": "http://127.0.0.1:8000",
      "/getprice": "http://127.0.0.1:8000",
      "/tickers": "http://127.0.0.1:8000",
      "/candles": "http://127.0.0.1:8000",
    },
  },
});
