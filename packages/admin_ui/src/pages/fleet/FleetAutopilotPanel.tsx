type FleetAutopilotPanelProps = {
  policyLevel: number;
  policyCheckpoints: string;
  policyCatalog: string[];
  policyCaption: string;
  enforcementMin: number;
  enforcementMax: number;
  enforcementCaption: string;
  onPolicyLevelChange: (n: number) => void;
  onPolicyCheckpointsChange: (v: string) => void;
  onEnforcementMinChange: (n: number) => void;
  onEnforcementMaxChange: (n: number) => void;
  onSaveAutopilotPolicy: () => void;
  onSaveEnforcementPolicy: () => void;
};

export function FleetAutopilotPanel({
  policyLevel,
  policyCheckpoints,
  policyCatalog,
  policyCaption,
  enforcementMin,
  enforcementMax,
  enforcementCaption,
  onPolicyLevelChange,
  onPolicyCheckpointsChange,
  onEnforcementMinChange,
  onEnforcementMaxChange,
  onSaveAutopilotPolicy,
  onSaveEnforcementPolicy,
}: FleetAutopilotPanelProps) {
  return (
    <>
      <h3>Fleet autopilot policy</h3>
      <p class="muted">
        Cap max autonomy level and require checkpoints for runs in the selected tenant.
      </p>
      {policyCaption ? <p class="hint">{policyCaption}</p> : null}
      <label>
        Max autopilot level{" "}
        <input
          type="number"
          min={0}
          max={10}
          value={policyLevel}
          onInput={(e) => onPolicyLevelChange(Number((e.target as HTMLInputElement).value) || 0)}
        />
      </label>{" "}
      <label>
        Required checkpoints (comma-separated){" "}
        <input
          value={policyCheckpoints}
          onInput={(e) => onPolicyCheckpointsChange((e.target as HTMLInputElement).value)}
          placeholder={policyCatalog.slice(0, 2).join(", ")}
        />
      </label>{" "}
      <button type="button" class="secondary" onClick={onSaveAutopilotPolicy}>
        Save policy
      </button>
      <h3>Fleet enforcement policy</h3>
      <p class="muted">Clamp per-run enforcement depth (0–10) for workspaces in the selected tenant.</p>
      {enforcementCaption ? <p class="hint">{enforcementCaption}</p> : null}
      <label>
        Min enforcement level{" "}
        <input
          type="number"
          min={0}
          max={10}
          value={enforcementMin}
          onInput={(e) => onEnforcementMinChange(Number((e.target as HTMLInputElement).value) || 0)}
          data-testid="admin-fleet-enforcement-min"
        />
      </label>{" "}
      <label>
        Max enforcement level{" "}
        <input
          type="number"
          min={0}
          max={10}
          value={enforcementMax}
          onInput={(e) => onEnforcementMaxChange(Number((e.target as HTMLInputElement).value) || 0)}
          data-testid="admin-fleet-enforcement-max"
        />
      </label>{" "}
      <button
        type="button"
        class="secondary"
        onClick={onSaveEnforcementPolicy}
        data-testid="admin-fleet-enforcement-save"
      >
        Save enforcement policy
      </button>
    </>
  );
}
