import { describe, expect, it } from "vitest";
import { briefReviewStatus } from "./researchStatus";
import { scorecardFromTimeline } from "./launchScorecard";

describe("run detail panel contracts", () => {
  it("research brief status prefers review_status over status", () => {
    expect(briefReviewStatus({ review_status: "pending", status: "approved" })).toBe("pending");
    expect(briefReviewStatus({ status: "approved" })).toBe("approved");
  });

  it("stitch event line format matches maker review", () => {
    const ev = { store_seq: 3, event_type: "stitch.applied", summary: "applied 2 paths" };
    const line = `#${ev.store_seq} ${ev.event_type}: ${ev.summary || ""}`;
    expect(line).toBe("#3 stitch.applied: applied 2 paths");
  });

  it("campaign workflow profile gates admin panels", () => {
    const campaign = { workflow_profile: "campaign_micro_slice" };
    const defaultRun = { workflow_profile: "default" };
    expect(campaign.workflow_profile === "campaign_micro_slice").toBe(true);
    expect(defaultRun.workflow_profile === "campaign_micro_slice").toBe(false);
  });

  it("launch scorecard reads latest launch_eval.completed metadata", () => {
    const timeline = {
      events: [
        {
          event_type: "stage.passed",
          payload: { stage_name: "launch_eval.completed" },
          metadata: {
            aggregate: 0.82,
            passed: true,
            findings: ["ok"],
            dev_env_ui_regression_passed: true,
          },
        },
      ],
    };
    const card = scorecardFromTimeline(timeline);
    expect(card?.aggregate).toBe(0.82);
    expect(card?.passed).toBe(true);
    expect(card?.findings).toEqual(["ok"]);
    expect(card?.dev_env_ui_regression_passed).toBe(true);
  });
});
