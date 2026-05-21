import type { PermissionRequest } from "../types/protocol";

interface Props {
  request: PermissionRequest;
  onAllow: () => void;
  onDeny: () => void;
  onCancelRun: () => void;
}

export function PermissionDialog({ request, onAllow, onDeny, onCancelRun }: Props) {
  return (
    <div className="permission-overlay" role="dialog" aria-modal="true">
      <div className="permission-dialog">
        <h2>Permission required</h2>
        <p>
          Tool <strong>{request.tool_name}</strong> ({request.risk_level} risk) wants to run.
        </p>
        {request.reason && <p className="muted">{request.reason}</p>}
        <pre>{JSON.stringify(request.tool_input, null, 2)}</pre>
        <div className="permission-actions">
          <button type="button" className="btn-allow" onClick={onAllow}>
            Allow
          </button>
          <button type="button" className="btn-deny" onClick={onDeny}>
            Deny
          </button>
          <button type="button" className="btn-secondary" onClick={onCancelRun}>
            Cancel run
          </button>
        </div>
      </div>
    </div>
  );
}
