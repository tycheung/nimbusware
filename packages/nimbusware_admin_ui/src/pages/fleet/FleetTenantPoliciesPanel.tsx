type FleetTenantPoliciesPanelProps = {
  tenantId: string;
  legalHold: boolean;
  auditPolicyBusy: boolean;
  auditPolicyCaption: string;
  allowExternalCollab: boolean;
  maxParticipants: number;
  collabPolicyCaption: string;
  collabPolicyBusy: boolean;
  allowedApiStack: string;
  allowedWebStack: string;
  stackPolicyCaption: string;
  stackPolicyBusy: boolean;
  onLegalHoldChange: (enabled: boolean) => void;
  onAllowExternalCollabChange: (enabled: boolean) => void;
  onMaxParticipantsChange: (n: number) => void;
  onSaveCollabPolicy: () => void;
  onAllowedApiStackChange: (v: string) => void;
  onAllowedWebStackChange: (v: string) => void;
  onSaveStackPolicy: () => void;
};

export function FleetTenantPoliciesPanel({
  tenantId,
  legalHold,
  auditPolicyBusy,
  auditPolicyCaption,
  allowExternalCollab,
  maxParticipants,
  collabPolicyCaption,
  collabPolicyBusy,
  allowedApiStack,
  allowedWebStack,
  stackPolicyCaption,
  stackPolicyBusy,
  onLegalHoldChange,
  onAllowExternalCollabChange,
  onMaxParticipantsChange,
  onSaveCollabPolicy,
  onAllowedApiStackChange,
  onAllowedWebStackChange,
  onSaveStackPolicy,
}: FleetTenantPoliciesPanelProps) {
  return (
    <>
      <section class="panel" data-testid="admin-fleet-audit-policy">
        <h4>Audit retention policy</h4>
        {auditPolicyCaption ? <p class="muted">{auditPolicyCaption}</p> : null}
        <label data-testid="admin-fleet-legal-hold-toggle">
          <input
            type="checkbox"
            checked={legalHold}
            disabled={auditPolicyBusy}
            onChange={(ev) => onLegalHoldChange((ev.target as HTMLInputElement).checked)}
          />
          Legal hold — block event-store purge for this tenant
        </label>
        <p class="muted">
          When enabled, <code>purge_event_store_retention.py</code> skips deletes. Env{" "}
          <code>NIMBUSWARE_EVENT_STORE_LEGAL_HOLD=1</code> also blocks purge globally.
        </p>
      </section>
      <section class="panel" data-testid="admin-fleet-collab-policy">
        <h4>Collab guest policy</h4>
        {collabPolicyCaption ? <p class="muted">{collabPolicyCaption}</p> : null}
        <label data-testid="admin-fleet-allow-external-toggle">
          <input
            type="checkbox"
            checked={allowExternalCollab}
            disabled={collabPolicyBusy || !tenantId}
            onChange={(ev) => onAllowExternalCollabChange((ev.target as HTMLInputElement).checked)}
          />
          Allow external collaborators via invite link (ADR 023)
        </label>
        <label>
          Max session participants{" "}
          <input
            type="number"
            min={1}
            max={500}
            value={maxParticipants}
            disabled={!tenantId}
            onInput={(e) =>
              onMaxParticipantsChange(Number((e.target as HTMLInputElement).value) || 1)
            }
            data-testid="admin-fleet-max-participants"
          />
        </label>
        <button
          type="button"
          class="secondary"
          disabled={collabPolicyBusy || !tenantId}
          onClick={() => onSaveCollabPolicy()}
          data-testid="admin-fleet-save-collab-policy"
        >
          Save collab policy
        </button>
        <p class="muted">
          When external guests are disabled, users must be added from the org directory; token link
          joins return 403.
        </p>
      </section>
      <section class="panel" data-testid="admin-fleet-stack-policy">
        <h4>Regulated stack allowlist</h4>
        {stackPolicyCaption ? <p class="muted">{stackPolicyCaption}</p> : null}
        <label>
          API stack{" "}
          <input
            type="text"
            value={allowedApiStack}
            placeholder="fastapi_python"
            disabled={!tenantId}
            onInput={(e) => onAllowedApiStackChange((e.target as HTMLInputElement).value)}
            data-testid="admin-fleet-stack-api"
          />
        </label>{" "}
        <label>
          Web stack{" "}
          <input
            type="text"
            value={allowedWebStack}
            placeholder="react_vite"
            disabled={!tenantId}
            onInput={(e) => onAllowedWebStackChange((e.target as HTMLInputElement).value)}
            data-testid="admin-fleet-stack-web"
          />
        </label>{" "}
        <button
          type="button"
          class="secondary"
          disabled={stackPolicyBusy || !tenantId}
          onClick={() => onSaveStackPolicy()}
          data-testid="admin-fleet-save-stack-policy"
        >
          Save stack policy
        </button>
        <p class="muted">
          Discovery recommendations clamp to these stacks for the selected tenant (fo2344).
        </p>
      </section>
    </>
  );
}
