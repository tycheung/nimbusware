import { apiJson, toast } from "../api-client.js";

export function branchDepth(graph, turnId) {
  let depth = 0;
  let cur = turnId;
  while (cur) {
    const edge = graph.edges?.find((e) => e.to_turn_id === cur);
    if (!edge) break;
    depth += 1;
    cur = edge.from_turn_id;
  }
  return depth;
}

export function applySiblingBadges(root, graph) {
  const thread = root.querySelector("#chat-thread");
  if (!thread || !graph?.nodes) return;
  for (const node of graph.nodes) {
    const siblings = Number(node.sibling_count || 0);
    if (siblings < 1) continue;
    const line = thread.querySelector(`[data-turn-id="${node.turn_id}"]`);
    if (!line || line.querySelector(".chat-sibling-badge")) continue;
    const badge = document.createElement("span");
    badge.className = "chat-sibling-badge muted";
    badge.dataset.testid = `maker-chat-sibling-badge-${node.turn_id}`;
    badge.textContent = `${siblings + 1} branches`;
    line.appendChild(badge);
  }
}

export async function refreshBranchPanel(root, sessionId, { onSessionUpdated } = {}) {
  const panel = root.querySelector("#chat-branch-panel");
  if (!panel || !sessionId) return;
  try {
    const graph = await apiJson(`/chat/sessions/${encodeURIComponent(sessionId)}/graph`);
    panel.replaceChildren();
    if (!graph.nodes?.length) {
      applySiblingBadges(root, graph);
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    const title = document.createElement("h4");
    title.textContent = "Conversation branches";
    panel.appendChild(title);
    const list = document.createElement("ul");
    list.className = "chat-branch-tree";
    const leaves = (graph.nodes || []).filter(
      (n) => !graph.edges?.some((e) => e.from_turn_id === n.turn_id),
    );
    for (const leaf of leaves) {
      let cur = leaf.turn_id;
      const path = [];
      while (cur) {
        const node = graph.nodes.find((n) => n.turn_id === cur);
        if (node) path.unshift(node);
        const edge = graph.edges?.find((e) => e.to_turn_id === cur);
        cur = edge?.from_turn_id;
      }
      for (const node of path) {
        const depth = branchDepth(graph, node.turn_id);
        const li = document.createElement("li");
        li.className = "chat-branch-tree__node";
        li.style.paddingLeft = `${depth * 1.25}rem`;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = leaf.turn_id === node.turn_id ? "linkish branch-active" : "linkish";
        btn.textContent = (node.text || node.turn_id).slice(0, 72);
        btn.dataset.testid = `maker-chat-branch-${node.turn_id}`;
        btn.addEventListener("click", async () => {
          const updated = await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}/active-leaf`,
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ leaf_turn_id: leaf.turn_id }),
            },
          );
          onSessionUpdated?.(updated);
          await refreshBranchPanel(root, sessionId, { onSessionUpdated });
          toast("Switched branch", "success");
        });
        li.appendChild(btn);
        if (Number(node.sibling_count || 0) > 0) {
          const badge = document.createElement("span");
          badge.className = "chat-sibling-badge muted";
          badge.textContent = `${Number(node.sibling_count) + 1} branches`;
          li.appendChild(badge);
        }
        list.appendChild(li);
      }
    }
    panel.appendChild(list);
    applySiblingBadges(root, graph);
  } catch {
    panel.classList.add("hidden");
  }
}
