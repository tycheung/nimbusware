import type { ComponentChildren } from "preact";

export function PanelFrame({
  error,
  empty,
  emptyMessage,
  loading,
  loadingMessage = "Loading…",
  onRefresh,
  children,
}: {
  error?: string;
  empty?: boolean;
  emptyMessage: string;
  loading?: boolean;
  loadingMessage?: string;
  onRefresh?: () => void;
  children: ComponentChildren;
}) {
  if (loading) return <p class="loading">{loadingMessage}</p>;
  if (error && empty) return <p class="muted">{error}</p>;
  if (empty) return <p class="muted">{emptyMessage}</p>;

  return (
    <div>
      {onRefresh ? (
        <button type="button" class="secondary" onClick={onRefresh}>
          Refresh
        </button>
      ) : null}
      {error ? <p class="hint">{error}</p> : null}
      {children}
    </div>
  );
}
