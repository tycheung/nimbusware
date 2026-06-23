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

function graphRoots(graph) {
  const childIds = new Set((graph.edges || []).map((e) => e.to_turn_id));
  return (graph.nodes || []).filter((n) => !childIds.has(n.turn_id));
}

function graphChildren(graph, turnId) {
  return (graph.edges || [])
    .filter((e) => e.from_turn_id === turnId)
    .map((e) => e.to_turn_id);
}

function nodeById(graph, turnId) {
  return (graph.nodes || []).find((n) => n.turn_id === turnId);
}

function leafTurnIds(graph) {
  return (graph.nodes || [])
    .filter((n) => !(graph.edges || []).some((e) => e.from_turn_id === n.turn_id))
    .map((n) => n.turn_id);
}

function renderTreeNode(
  root,
  graph,
  turnId,
  depth,
  activeLeafId,
  sessionId,
  list,
  { onSessionUpdated },
) {
  const node = nodeById(graph, turnId);
  if (!node) return;
  const li = document.createElement("li");
  li.className = "chat-branch-tree__node";
  li.style.paddingLeft = `${depth * 1.25}rem`;
  li.dataset.testid = `maker-chat-branch-tree-node-${turnId}`;
  const btn = document.createElement("button");
  btn.type = "button";
  const isLeaf = leafTurnIds(graph).includes(turnId);
  btn.className =
    turnId === activeLeafId || (isLeaf && turnId === activeLeafId)
      ? "linkish branch-active"
      : "linkish";
  btn.textContent = (node.text || node.turn_id).slice(0, 72);
  btn.dataset.testid = `maker-chat-branch-${turnId}`;
  if (isLeaf) {
    btn.addEventListener("click", async () => {
      const updated = await apiJson(
        `/chat/sessions/${encodeURIComponent(sessionId)}/active-leaf`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ leaf_turn_id: turnId }),
        },
      );
      onSessionUpdated?.(updated);
      await refreshBranchPanel(root, sessionId, { onSessionUpdated });
      toast("Switched branch", "success");
    });
  } else {
    btn.disabled = true;
    btn.title = "Select a leaf branch to switch active path";
  }
  li.appendChild(btn);
  if (Number(node.sibling_count || 0) > 0) {
    const badge = document.createElement("span");
    badge.className = "chat-sibling-badge muted";
    badge.textContent = `${Number(node.sibling_count) + 1} branches`;
    li.appendChild(badge);
  }
  list.appendChild(li);
  const childIds = graphChildren(graph, turnId);
  for (const childId of childIds) {
    renderTreeNode(root, graph, childId, depth + 1, activeLeafId, sessionId, list, {
      onSessionUpdated,
    });
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
    list.dataset.testid = "maker-chat-branch-tree";
    const activeLeafId =
      graph.active_leaf_turn_id ||
      leafTurnIds(graph)[leafTurnIds(graph).length - 1] ||
      "";
    for (const rootNode of graphRoots(graph)) {
      renderTreeNode(root, graph, rootNode.turn_id, 0, activeLeafId, sessionId, list, {
        onSessionUpdated,
      });
    }
    panel.appendChild(list);
    applySiblingBadges(root, graph);
  } catch {
    panel.classList.add("hidden");
  }
}
