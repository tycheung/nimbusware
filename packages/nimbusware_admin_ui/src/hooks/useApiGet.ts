import { useCallback, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

export function useApiGet<T>(
  path: string | null,
  select: (body: unknown) => T,
  empty: T,
): { data: T; error: string; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T>(empty);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(path));

  const reload = useCallback(() => {
    if (!path) return;
    setLoading(true);
    apiJson(path)
      .then((body) => {
        setData(select(body));
        setError("");
      })
      .catch((e) => {
        setData(empty);
        setError(String((e as Error).message || e));
      })
      .finally(() => setLoading(false));
    // select/empty are stable for a given panel; path drives refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, error, loading, reload };
}
