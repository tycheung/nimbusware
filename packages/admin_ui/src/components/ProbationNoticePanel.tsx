import { useMemo } from "preact/hooks";

export function ProbationNoticePanel({ rows }: { rows: Record<string, string>[] }) {
  const notices = useMemo(
    () =>
      rows.filter(
        (r) =>
          r.reason_code === "persona_probation_promotion_notice" ||
          (r.category || "").includes("probation"),
      ),
    [rows],
  );

  if (!notices.length) {
    return <p class="muted">No probation promotion notices on this run.</p>;
  }

  return (
    <ul>
      {notices.map((n, i) => (
        <li key={i}>
          {n.severity ? `${n.severity}: ` : ""}
          {n.summary || n.category || "Probation notice"}
        </li>
      ))}
    </ul>
  );
}
