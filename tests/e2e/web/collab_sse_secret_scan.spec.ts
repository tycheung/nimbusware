import { test, expect, chromium } from "@playwright/test";

const SECRET_HOST = "sk-playwright-host-zzzzzzzzzzzzzzzz";
const SECRET_GUEST = "sk-playwright-guest-yyyyyyyyyyyyyyyy";

async function signup(page: import("@playwright/test").Page, username: string) {
  const res = await page.request.post("/v1/auth/signup", {
    data: { username, password: "password1234", display_name: username },
  });
  expect(res.ok()).toBeTruthy();
  return res.json();
}

async function signin(page: import("@playwright/test").Page, username: string) {
  const res = await page.request.post("/v1/auth/signin", {
    data: { username, password: "password1234" },
  });
  expect(res.ok()).toBeTruthy();
}

test("collab SSE secret scan — two browsers, zero key leaks", async () => {
  test.skip(!process.env.NIMBUSWARE_COLLAB_E2E, "set NIMBUSWARE_COLLAB_E2E=1 to run dual-browser collab SSE scan");

  const browser = await chromium.launch();
  const hostCtx = await browser.newContext();
  const guestCtx = await browser.newContext();
  const hostPage = await hostCtx.newPage();
  const guestPage = await guestCtx.newPage();

  const suffix = Date.now().toString(36);
  const hostUser = `pw-host-${suffix}`;
  const guestUser = `pw-guest-${suffix}`;

  await signup(hostPage, hostUser);
  const guest = await signup(guestPage, guestUser);

  const repoRoot = process.env.NIMBUSWARE_REPO_ROOT || "../../..";
  const ws = `${repoRoot}/tests/fixtures/repos/tiny_python_app`;
  const project = await hostPage.request.post("/v1/projects", {
    data: {
      name: "collab-e2e",
      workspace_path: ws,
      template: "attach",
      default_workflow_profile: "micro_slice",
    },
  });
  expect(project.ok()).toBeTruthy();
  const projectId = (await project.json()).project_id;

  const sess = await hostPage.request.post("/v1/chat/sessions", {
    data: { project_id: projectId },
  });
  expect(sess.ok()).toBeTruthy();
  const sessionId = (await sess.json()).session_id;

  await hostPage.request.post(`/v1/chat/sessions/${sessionId}/participants`, {
    data: { user_id: guest.user_id, role: "session_read" },
  });

  await hostPage.request.post(`/v1/chat/sessions/${sessionId}/commentary`, {
    data: { text: `theater leak api_key=${SECRET_HOST}` },
  });

  await signin(guestPage, guestUser);

  const streamRes = await guestPage.request.get(`/v1/chat/sessions/${sessionId}/stream`, {
    timeout: 15000,
  });
  expect(streamRes.ok()).toBeTruthy();
  const body = await streamRes.text();
  expect(body).not.toContain(SECRET_HOST);
  expect(body).not.toContain(SECRET_GUEST);
  expect(body).toContain("[redacted]");

  await browser.close();
});
