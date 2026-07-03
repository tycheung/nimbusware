export function DynamicTable({
  rows,
  emptyMessage = "No data.",
  columns,
}: {
  rows: Record<string, string>[];
  emptyMessage?: string;
  columns?: string[];
}) {
  if (!rows.length) return <p class="muted">{emptyMessage}</p>;
  const cols = columns ?? Object.keys(rows[0]);
  return (
    <table class="data-table">
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {cols.map((c) => (
              <td key={c}>{r[c]}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function KeyValueTable({
  rows,
  keyField,
  valueField,
  keyLabel,
  valueLabel,
}: {
  rows: { [k: string]: string }[];
  keyField: string;
  valueField: string;
  keyLabel: string;
  valueLabel: string;
}) {
  if (!rows.length) return null;
  return (
    <table class="data-table">
      <thead>
        <tr>
          <th>{keyLabel}</th>
          <th>{valueLabel}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={row[keyField] || i}>
            <td>{row[keyField]}</td>
            <td>{row[valueField]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
