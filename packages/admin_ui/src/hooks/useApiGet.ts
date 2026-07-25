import { useCallback, useEffect, useState } from "preact/hooks";
import {
  apiJson,
  formatCapacityMissMessage,
  formatPeelMissMessage,
  formatReadCatchMessage,
  isDomainPeelMiss,
} from "../api/client"; // sak499-d
export function useApiGet<T>(
  path: string | null,
  select: (body: unknown) => T,
  empty: T,
  missFallback = "broker_miss",
): { data: T; error: string; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T>(empty);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(path));

  const reload = useCallback(() => {
    if (!path) return;
    setLoading(true);
    apiJson(path)
      .then((body) => {
        const miss = body as Record<string, unknown>;
        if (miss?.capacity_source != null) {
          setData(empty);
          setError(formatCapacityMissMessage(miss));
          return;
        }
        if (isDomainPeelMiss(body)) {
          setData(empty);
          setError(formatPeelMissMessage(body, missFallback));
          return;
        }
        setData(select(body));
        setError("");
      })
      .catch((e) => {
        setData(empty);
        setError(formatReadCatchMessage(e, missFallback));
      })
      .finally(() => setLoading(false));
    // select/empty/missFallback are stable for a given panel; path drives refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, error, loading, reload };
}
