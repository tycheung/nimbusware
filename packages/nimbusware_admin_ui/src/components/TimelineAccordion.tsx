import { useState } from "preact/hooks";
import { apiJson } from "../api/client";

const SECTIONS: { key: string; label: string; timelineField?: string }[] = [
  { key: "events", label: "Events" },
  { key: "integrator_gate", label: "Integrator gate", timelineField: "integrator_gate" },
  { key: "micro_slice", label: "Micro slice", timelineField: "micro_slice" },
  { key: "critic_matrix_live", label: "Critic matrix (live)", timelineField: "critic_matrix_live" },
  { key: "memory_retrieval", label: "Memory retrieval", timelineField: "memory_retrieval" },
  { key: "preflight", label: "Preflight", timelineField: "preflight" },
  { key: "interjection", label: "Interjection SLO" },
];

type Timeline = Record<string, unknown>;

export function TimelineAccordion({
  runId,
  timeline,
  highlightSeq,
}: {
  runId: string;
  timeline: Timeline;
  highlightSeq?: number | null;
}) {
  const [open, setOpen] = useState<string | null>(highlightSeq != null ? "events" : null);
  const [explain, setExplain] = useState<Record<string, string>>({});

  async function toggle(section: string) {
    if (open === section) {
      setOpen(null);
      return;
    }
    setOpen(section);
    if (!explain[section]) {
      try {
        const body = await apiJson<{ markdown?: string }>(
          `/runs/${runId}/timeline/${encodeURIComponent(section)}/explain`,
        );
        setExplain((e) => ({ ...e, [section]: body.markdown || "" }));
      } catch {
        setExplain((e) => ({ ...e, [section]: "_Explain unavailable._" }));
      }
    }
  }

  return (
    <div class="timeline-accordion">
      {SECTIONS.map((sec) => {
        const payload = sec.timelineField ? timeline[sec.timelineField] : null;
        const hasData =
          sec.key === "events"
            ? (timeline.events as unknown[])?.length
            : sec.key === "interjection"
              ? true
              : payload != null;
        if (!hasData && sec.key !== "events" && sec.key !== "interjection") return null;
        return (
          <details key={sec.key} open={open === sec.key}>
            <summary onClick={(e) => { e.preventDefault(); void toggle(sec.key); }}>
              {sec.label}
            </summary>
            {sec.key === "events" ? (
              <ul class="timeline-events">
                {((timeline.events as Record<string, unknown>[]) || []).map((ev, i) => {
                  const seq = Number(ev.store_seq ?? ev.seq ?? 0);
                  const et = String(ev.event_type ?? ev.type ?? "event");
                  const hl = highlightSeq != null && seq === highlightSeq;
                  return (
                    <li key={`${seq}-${i}`} data-store-seq={seq || undefined} class={hl ? "highlight" : ""}>
                      <strong>#{seq || "—"}</strong> {et}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <pre class="json-block">{JSON.stringify(payload, null, 2)}</pre>
            )}
            {open === sec.key && explain[sec.key] ? (
              <div class="explain-md" dangerouslySetInnerHTML={{ __html: explain[sec.key].replace(/\n/g, "<br/>") }} />
            ) : null}
          </details>
        );
      })}
    </div>
  );
}
