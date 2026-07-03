import { useApiGet } from "../hooks/useApiGet";
import { KeyValueTable } from "./DynamicTable";
import { PanelFrame } from "./PanelFrame";

type ReliabilityData = {
  caption: string;
  rows: { metric: string; value: string }[];
};

export function CriticReliabilityPanel({ runId }: { runId: string }) {
  const { data, error, loading, reload } = useApiGet<ReliabilityData>(
    `/admin/ui/runs/${runId}/critic-reliability`,
    (body) => {
      const raw = body as { caption?: string; rows?: { metric: string; value: string }[] };
      return {
        caption: raw.caption || "",
        rows: raw.rows || [],
      };
    },
    { caption: "", rows: [] },
  );

  return (
    <PanelFrame
      error={error}
      empty={!data.rows.length}
      emptyMessage={data.caption || "No critic reliability data."}
      loading={loading}
      onRefresh={reload}
    >
      {data.caption ? <p>{data.caption}</p> : null}
      <KeyValueTable
        rows={data.rows}
        keyField="metric"
        valueField="value"
        keyLabel="Metric"
        valueLabel="Value"
      />
    </PanelFrame>
  );
}
