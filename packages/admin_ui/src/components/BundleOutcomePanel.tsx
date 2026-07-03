import { useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

type OutcomeRow = {
  bundle_id: string;
  success_rate: number;
  sample_count: number;
  avg_fit_on_pass: number | null;
  avg_fit_on_fail: number | null;
};

import { fmtFit, fmtRate } from "../utils/formatters";
export function BundleOutcomePanel() {
  const [caption, setCaption] = useState("");
  const [rows, setRows] = useState<OutcomeRow[]>([]);
  const [available, setAvailable] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{
      available?: boolean;
      caption?: string;
      rows?: OutcomeRow[];
    }>("/platform/analytics/bundle-outcomes")
      .then((body) => {
        setAvailable(Boolean(body.available));
        setCaption(body.caption || "");
        setRows(body.rows || []);
        setError("");
      })
      .catch((e) => setError(String((e as Error).message || e)));
  }, []);

  if (error) return <p class="error">{error}</p>;

  return (
    <section>
      <h3>Bundle gate outcomes</h3>
      <p class="muted">
        Fit score versus integrator gate pass rate per bundle id (from bundle memory store).
      </p>
      {caption ? <p>{caption}</p> : null}
      {!available && !rows.length ? (
        <p class="muted">No bundle outcomes recorded yet.</p>
      ) : null}
      {rows.length ? (
        <table class="data-table">
          <thead>
            <tr>
              <th>Bundle</th>
              <th>Pass rate</th>
              <th>Samples</th>
              <th>Avg fit (pass)</th>
              <th>Avg fit (fail)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.bundle_id}>
                <td>{row.bundle_id}</td>
                <td>
                  <span
                    class="rate-bar"
                    style={{
                      display: "inline-block",
                      width: `${Math.round(row.success_rate * 100)}%`,
                      maxWidth: "8rem",
                      minWidth: row.success_rate > 0 ? "0.5rem" : "0",
                    }}
                  />
                  {fmtRate(row.success_rate)}
                </td>
                <td>{row.sample_count}</td>
                <td>{fmtFit(row.avg_fit_on_pass)}</td>
                <td>{fmtFit(row.avg_fit_on_fail)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
