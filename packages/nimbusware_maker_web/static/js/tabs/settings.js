import { apiJson, toast } from "../api-client.js";

export async function mountSettings(root) {
  const me = await apiJson("/settings/me");
  root.innerHTML = `<form id="settings-form"></form><div id="hardware-mount"></div>`;
  const form = root.querySelector("#settings-form");
  const entries = Object.entries(me.values || me.settings || me);
  for (const [key, val] of entries) {
    if (typeof val !== "string" && typeof val !== "number" && typeof val !== "boolean") continue;
    const label = document.createElement("label");
    label.textContent = key;
    const input = document.createElement("input");
    input.name = key;
    input.value = String(val);
    label.appendChild(input);
    form?.appendChild(label);
  }
  const btn = document.createElement("button");
  btn.type = "submit";
  btn.textContent = "Save";
  btn.className = "primary";
  form?.appendChild(btn);

  form?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(form);
    const patch = Object.fromEntries(fd.entries());
    await apiJson("/settings/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    toast("Settings saved", "success");
  });

  const hw = await apiJson("/platform/hardware");
  root.querySelector("#hardware-mount").innerHTML = `<pre>${JSON.stringify(hw.profile || hw, null, 2)}</pre>`;
}
