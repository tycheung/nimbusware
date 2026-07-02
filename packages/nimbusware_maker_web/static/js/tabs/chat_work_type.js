import { apiJson, toast } from "../api-client.js";
import { renderMessagesFromSession, workTypeLabel } from "./chat_session_ui.js";

async function switchWorkType(root, sessionId, turnId, workType, { replayFromSeq } = {}) {
  const payload = { work_type: workType };
  if (replayFromSeq != null) {
    payload.align_run_replay = true;
    payload.replay_from_seq = replayFromSeq;
  }
  const updated = await apiJson(
    `/chat/sessions/${encodeURIComponent(sessionId)}/turns/${encodeURIComponent(turnId)}/switch-mode`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  const select = root.querySelector("#chat-work-type");
  if (select) select.value = workType;
  renderMessagesFromSession(root, updated);
  if (replayFromSeq != null) {
    toast(`Mode: ${workTypeLabel(workType)} (replay seq ${replayFromSeq} on next start)`, "success");
  } else {
    toast(`Mode: ${workTypeLabel(workType)}`, "success");
  }
  return updated;
}

export { switchWorkType };
