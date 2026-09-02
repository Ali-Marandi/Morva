import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  base: "/Morva/",
  plugins: [react()],
  build: { sourcemap: false },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
