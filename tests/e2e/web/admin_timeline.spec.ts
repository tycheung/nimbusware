import { test, expect } from "@playwright/test";

test("timeline explain endpoint returns markdown", async ({ request }) => {
  const runRes = await request.post("/v1/runs", {
    data: { workflow_profile: "default" },
  });
  expect(runRes.ok()).toBeTruthy();
  const runId = (await runRes.json()).run_id;
  const res = await request.get(`/v1/runs/${runId}/timeline/events/explain`);
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body.markdown).toBeTruthy();
});
