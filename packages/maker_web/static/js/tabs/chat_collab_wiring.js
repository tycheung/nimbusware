import { apiJson } from "../api-client.js";
import { refreshAccessibleComputeTrigger } from "./accessible_compute_ui.js";
import {
  mountCommentaryComposer,
  mountInviteButton,
  mountMyModelsLink,
  bindSessionStream,
} from "./chat_collab_ui.js";
import { refreshHostTransferPanel } from "./chat_host_transfer_ui.js";
import { refreshSessionOptimizerPanel } from "./chat_optimizer_ui.js";
import {
  getCollabMyRole,
  renderParticipantStrip,
} from "./chat_session_ui.js";
import { renderMessagesFromSession, renderTurnLine } from "./chat_session_ui.js";

let sessionStreamTurnCount = 0;
let cachedCurrentUserId = null;

function maybeHostFallbackBanner(root, session, participants) {
  const hostId = session?.host_user_id;
  if (!hostId || !participants?.length) return;
  const hostPresent = participants.some((p) => String(p.user_id) === String(hostId));
  const existing = root.querySelector("[data-testid='maker-chat-host-fallback']");
  if (hostPresent) {
    existing?.remove();
    return;
  }
  if (existing) return;
  const banner = document.createElement("p");
  banner.className = "muted chat-host-fallback-banner";
  banner.dataset.testid = "maker-chat-host-fallback";
  banner.textContent =
    "Host is offline — theater and compute fall back to participants on this session.";
  root.querySelector(".chat-main")?.prepend(banner);
}

export async function resolveCurrentUserId() {
  if (cachedCurrentUserId) return cachedCurrentUserId;
  try {
    const me = await apiJson("/auth/me");
    cachedCurrentUserId = me.user_id || null;
  } catch {
    cachedCurrentUserId = null;
  }
  return cachedCurrentUserId;
}

export async function wireCollabSessionUi(root, sessionId, session) {
  if (!sessionId) return;
  renderMessagesFromSession(root, session);
  mountInviteButton(root, sessionId);
  mountMyModelsLink(root, sessionId);
  await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
  await refreshSessionOptimizerPanel(root, sessionId, {
    workloadMode: session?.workload_distribution || "host_only",
  });
  mountCommentaryComposer(root, sessionId, (turn) => {
    const thread = root.querySelector("#chat-thread");
    if (thread && turn) renderTurnLine(thread, turn);
  });
  const userId = await resolveCurrentUserId();
  await refreshHostTransferPanel(root, sessionId, {
    currentUserId: userId,
    onReload: async () => {
      const existing = await apiJson(
        `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
      );
      renderMessagesFromSession(root, existing);
    },
  });
  sessionStreamTurnCount = session?.turns?.length || 0;
  bindSessionStream(root, sessionId, {
    onSession: async (data) => {
      if (data.participants?.length) {
        renderParticipantStrip(root, {
          participants: data.participants,
          host_user_id: session?.host_user_id,
        });
        maybeHostFallbackBanner(root, session, data.participants);
        mountInviteButton(root, sessionId);
        mountMyModelsLink(root, sessionId);
      }
      await refreshAccessibleComputeTrigger(root, sessionId, getCollabMyRole());
      const count = data.turn_count ?? sessionStreamTurnCount;
      if (count > sessionStreamTurnCount) {
        sessionStreamTurnCount = count;
        try {
          const existing = await apiJson(
            `/chat/sessions/${encodeURIComponent(sessionId)}?include_turns=true`,
          );
          renderMessagesFromSession(root, existing);
        } catch {
          /* ignore */
        }
      }
    },
  });
}
