import { apiJson, toast } from "../api-client.js";

export async function mountWizard(root) {
  const state = await apiJson("/platform/onboarding");
  if (state.onboarded) {
    root.innerHTML = "<p>Setup complete. Use Home to manage projects.</p>";
    return;
  }
  root.innerHTML = `
    <ol>
      <li>Check <a href="#/home">readiness</a> on Home</li>
      <li>Create a project with a workspace folder</li>
      <li>Pick a model on the Models tab</li>
      <li>Start a build from the Build tab</li>
    </ol>
    <button type="button" id="wizard-done" class="primary">Mark setup complete</button>`;
  root.querySelector("#wizard-done")?.addEventListener("click", async () => {
    await apiJson("/platform/onboarding", { method: "POST" });
    toast("Onboarding complete", "success");
    window.location.hash = "/home";
  });
}
