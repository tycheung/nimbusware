import path from "node:path";
import { defineConfig } from "@playwright/test";

const port = 8765;
const baseURL = `http://127.0.0.1:${port}`;
const repoRoot = path.resolve(process.cwd(), "../../..");

export default defineConfig({
  testDir: ".",
  timeout: 120_000,
  retries: 1,
  workers: 4,
  use: {
    baseURL,
    viewport: { width: 1280, height: 800 },
    trace: "on-first-retry",
  },
  webServer: {
    command: `poetry run python -m uvicorn api.app:app --host 127.0.0.1 --port ${port}`,
    url: `${baseURL}/v1/maker/app/`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NIMBUSWARE_SKIP_PREFLIGHT: "1",
      NIMBUSWARE_LAUNCH_TEST_STUB: "1",
      NIMBUSWARE_REPO_ROOT: process.env.NIMBUSWARE_REPO_ROOT || repoRoot,
      NIMBUSWARE_API_BASE: `http://127.0.0.1:${port}/v1`,
      NIMBUSWARE_ADMIN_TOKEN:
        process.env.NIMBUSWARE_ADMIN_TOKEN ||
        "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD",
      NIMBUSWARE_DATABASE_URL: "",
    },
  },
});
