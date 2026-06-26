import { test, expect, chromium } from "@playwright/test";

test("collab model routing — host and guest bindings isolated", async () => {
  test.skip(!process.env.NIMBUSWARE_COLLAB_E2E, "set NIMBUSWARE_COLLAB_E2E=1 for dual-browser collab E2E");

  const browser = await chromium.launch();
  const hostCtx = await browser.newContext();
  const guestCtx = await browser.newContext();
  const hostPage = await hostCtx.newPage();
  const guestPage = await guestCtx.newPage();
  const suffix = Date.now().toString(36);

  const hostSignup = await hostPage.request.post("/v1/auth/signup", {
    data: {
      username: `pw-host-${suffix}`,
      password: "password1234",
      display_name: "Host",
    },
  });
  expect(hostSignup.ok()).toBeTruthy();
  const guestSignup = await guestPage.request.post("/v1/auth/signup", {
    data: {
      username: `pw-guest-${suffix}`,
      password: "password1234",
      display_name: "Guest",
    },
  });
  expect(guestSignup.ok()).toBeTruthy();
  const guest = await guestSignup.json();

  await hostPage.request.post("/v1/auth/signin", {
    data: { username: `pw-host-${suffix}`, password: "password1234" },
  });
  await guestPage.request.post("/v1/auth/signin", {
    data: { username: `pw-guest-${suffix}`, password: "password1234" },
  });

  const repoRoot = process.env.NIMBUSWARE_REPO_ROOT || "../../..";
  const project = await hostPage.request.post("/v1/projects", {
    data: {
      name: "collab-routing",
      workspace_path: `${repoRoot}/tests/fixtures/repos/tiny_python_app`,
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
    data: { user_id: guest.user_id, role: "session_write" },
  });

  const hostPut = await hostPage.request.put(
    `/v1/chat/sessions/${sessionId}/participant-bindings`,
    {
      data: {
        agent_role: "backend_writer",
        provider_kind: "cloud",
        provider_id: "openai",
        model_id: "gpt-4o-mini",
        connection_id: null,
      },
    },
  );
  expect(hostPut.ok()).toBeTruthy();

  const guestPut = await guestPage.request.put(
    `/v1/chat/sessions/${sessionId}/participant-bindings`,
    {
      data: {
        agent_role: "backend_writer",
        provider_kind: "local",
        provider_id: "ollama",
        model_id: "llama3.1:8b",
        connection_id: null,
      },
    },
  );
  expect(guestPut.ok()).toBeTruthy();

  const hostGet = await hostPage.request.get(
    `/v1/chat/sessions/${sessionId}/participant-bindings`,
  );
  const guestGet = await guestPage.request.get(
    `/v1/chat/sessions/${sessionId}/participant-bindings`,
  );
  expect(hostGet.ok()).toBeTruthy();
  expect(guestGet.ok()).toBeTruthy();
  const hostRoles = (await hostGet.json()).roles || {};
  const guestRoles = (await guestGet.json()).roles || {};
  expect(hostRoles.backend_writer?.provider_id).toBe("openai");
  expect(guestRoles.backend_writer?.provider_id).toBe("ollama");

  await browser.close();
});
