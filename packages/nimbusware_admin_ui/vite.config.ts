import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [preact()],
  base: "/v1/admin/app/",
  resolve: {
    alias: {
      "@nimbusware/ui-shared": path.resolve(rootDir, "../nimbusware_ui_shared"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
    },
  },
});
