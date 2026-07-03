import { useApiGet } from "../hooks/useApiGet";
import { KeyValueTable } from "./DynamicTable";
import { PanelFrame } from "./PanelFrame";

type IawData = {
  present: boolean;
  caption: string;
  rows: { field: string; value: string }[];
};

export function IntegrationAdapterPanel({ runId }: { runId: string }) {
  const { data, error, reload } = useApiGet<IawData>(
    `/admin/ui/runs/${runId}/integration-adapter-writer`,
    (body) => {
      const raw = body as {
        present?: boolean;
        caption?: string;
        rows?: { field: string; value: string }[];
      };
      return {
        present: Boolean(raw.present),
        caption: raw.caption || "",
        rows: raw.rows || [],
      };
    },
    { present: false, caption: "", rows: [] },
  );

  if (!data.present) {
    return <p class="muted">{error || data.caption || "No Integration Adapter Writer stage."}</p>;
  }

  return (
    <PanelFrame error={error} empty={false} emptyMessage="" onRefresh={reload}>
      <p>{data.caption}</p>
      <KeyValueTable
        rows={data.rows}
        keyField="field"
        valueField="value"
        keyLabel="Field"
        valueLabel="Value"
      />
    </PanelFrame>
  );
}
