import { apiJson, toast } from "../../api-client.js";
import { wireAutopilotRibbon } from "../../autopilot-ribbon.js";
import { wireEnforcementRibbon } from "../../enforcement-ribbon.js";
import { wireInterjectionRibbon } from "../../interjection-ribbon.js";
import { wireStandardsRibbon } from "../../standards-ribbon.js";
import {
  refreshCouncilRibbon,
  refreshDevEnvStatus,
  refreshLearningsPanel,
  refreshVariantRibbon,
} from "./progress_ribbon_refresh.js";

export function wireOperatorRibbons(runId) {
  document.getElementById("dev-env-start-btn")?.addEventListener("click", async () => {
    try {
      await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/start`, { method: "POST" });
      toast("Dev env started", "success");
      await refreshDevEnvStatus(runId);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  document.getElementById("dev-env-stop-btn")?.addEventListener("click", async () => {
    try {
      await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/stop`, { method: "POST" });
      toast("Dev env stopped", "success");
      await refreshDevEnvStatus(runId);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  document.getElementById("dev-env-regression-btn")?.addEventListener("click", async () => {
    try {
      const res = await apiJson(`/runs/${encodeURIComponent(runId)}/dev-env/regression`, { method: "POST" });
      toast(res.passed ? "Regression passed" : `Regression failed: ${res.detail}`, res.passed ? "success" : "error");
      await refreshDevEnvStatus(runId);
    } catch (e) {
      toast(String(e.message || e), "error");
    }
  });
  const interjectionRibbon = document.getElementById("interjection-ribbon");
  if (interjectionRibbon) wireInterjectionRibbon(interjectionRibbon, runId);
  const enforcementRibbon = document.getElementById("enforcement-ribbon");
  if (enforcementRibbon) void wireEnforcementRibbon(enforcementRibbon, runId);
  const standardsRibbon = document.getElementById("standards-ribbon");
  if (standardsRibbon) void wireStandardsRibbon(standardsRibbon, runId);
  const autopilotRibbon = document.getElementById("autopilot-ribbon");
  if (autopilotRibbon) void wireAutopilotRibbon(autopilotRibbon, runId);
  void refreshDevEnvStatus(runId);
  void refreshCouncilRibbon(runId);
  void refreshVariantRibbon(runId);
  void refreshLearningsPanel(runId);
}
