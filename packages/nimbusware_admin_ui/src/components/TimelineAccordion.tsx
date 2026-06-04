import { useState } from "preact/hooks";
import { apiJson } from "../api/client";

const SECTIONS: { key: string; label: string; timelineField?: string }[] = [
  { key: "events", label: "Events" },
  { key: "integrator_gate", label: "Integrator gate", timelineField: "integrator_gate" },
  { key: "micro_slice", label: "Micro slice", timelineField: "micro_slice" },
  { key: "critic_matrix_live", label: "Critic matrix (live)", timelineField: "critic_matrix_live" },
  { key: "memory_retrieval", label: "Memory retrieval", timelineField: "memory_retrieval" },
  { key: "preflight", label: "Preflight", timelineField: "preflight" },
];

type Timeline = Record<string, unknown>;

export function TimelineAccordion({ runId, timeline }: { runId: string; timeline: Timeline }) {
  const [open, setOpen] = useState<string | null>(null);
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
        const hasData = sec.key === "events" ? (timeline.events as unknown[])?.length : payload != null;
        if (!hasData && sec.key !== "events") return null;
        return (
          <details key={sec.key} open={open === sec.key}>
            <summary onClick={(e) => { e.preventDefault(); void toggle(sec.key); }}>
              {sec.label}
            </summary>
            {sec.key === "events" ? (
              <p>{(timeline.events as unknown[])?.length || 0} events (use findings/critic panels below).</p>
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
