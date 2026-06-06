import path from "node:path";
import { defineConfig } from "@playwright/test";

const port = 8765;
const baseURL = `http://127.0.0.1:${port}`;
const repoRoot = path.resolve(process.cwd(), "../../..");

export default defineConfig({
  testDir: ".",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL,
    viewport: { width: 1280, height: 800 },
    trace: "on-first-retry",
  },
  webServer: {
    command: `poetry run python -m uvicorn nimbusware_api.app:app --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/v1/maker/app/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NIMBUSWARE_SKIP_PREFLIGHT: "1",
      NIMBUSWARE_REPO_ROOT: process.env.NIMBUSWARE_REPO_ROOT || repoRoot,
    },
  },
});
