import { createContext, type ComponentChildren } from "preact";
import { useCallback, useContext, useEffect, useState } from "preact/hooks";
import { apiJson } from "../api/client";

export type CampaignProgress = {
  state?: string;
  autonomous?: boolean;
  current_slice_id?: string | null;
  slices_completed?: number;
  slices_total?: number;
  next_maintenance?: {
    refactor_in_slices?: number | null;
    architecture_in_slices?: number | null;
  };
};

export type BacklogTree = {
  epics?: {
    epic_id?: string;
    title?: string;
    status?: string;
    features?: {
      feature_id?: string;
      title?: string;
      slices?: { slice_id?: string; status?: string }[];
    }[];
  }[];
  summary?: {
    total_slices?: number;
    slices_completed?: number;
    slices_pending?: number;
  };
};

type CampaignProgressBody = {
  progress?: CampaignProgress;
  maintenance_events?: string[];
  backlog?: BacklogTree;
};

type CampaignProgressContextValue = {
  body: CampaignProgressBody | null;
  error: string;
  reload: () => void;
};

const CampaignProgressContext = createContext<CampaignProgressContextValue>({
  body: null,
  error: "",
  reload: () => undefined,
});

export function CampaignProgressProvider({
  campaignId,
  children,
}: {
  campaignId: string;
  children: ComponentChildren;
}) {
  const [body, setBody] = useState<CampaignProgressBody | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(() => {
    apiJson<CampaignProgressBody>(`/campaigns/${campaignId}/progress`)
      .then((raw) => {
        setBody(raw);
        setError("");
      })
      .catch((e) => {
        setBody(null);
        setError(String((e as Error).message || e));
      });
  }, [campaignId]);

  useEffect(() => {
    reload();
  }, [reload]);

  return (
    <CampaignProgressContext.Provider value={{ body, error, reload }}>
      {children}
    </CampaignProgressContext.Provider>
  );
}

export function useCampaignProgress() {
  return useContext(CampaignProgressContext);
}
