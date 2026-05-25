import { ShieldAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { PermissionRequest } from "../types/protocol";

interface Props {
  request: PermissionRequest;
  onAllow: () => void;
  onDeny: () => void;
  onCancelRun: () => void;
}

export function PermissionDialog({ request, onAllow, onDeny, onCancelRun }: Props) {
  return (
    <Dialog open>
      <DialogContent className="max-w-xl" showCloseButton={false}>
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline">Permission required</Badge>
            <Badge variant={request.risk_level === "high" ? "destructive" : "secondary"}>
              {request.risk_level} risk
            </Badge>
          </div>
          <DialogTitle>Allow {request.tool_name} to run?</DialogTitle>
          <DialogDescription>
            The active run is waiting for a decision before this tool call can continue.
          </DialogDescription>
        </DialogHeader>

        {request.reason ? (
          <Alert>
            <ShieldAlertIcon />
            <AlertTitle>Why it asked</AlertTitle>
            <AlertDescription>{request.reason}</AlertDescription>
          </Alert>
        ) : null}

        <div className="space-y-2">
          <p className="text-sm font-medium">Tool input</p>
          <ScrollArea className="max-h-72 rounded-lg border bg-muted/30">
            <pre className="overflow-x-auto p-3 font-mono text-xs leading-5 whitespace-pre-wrap">
              {JSON.stringify(request.tool_input, null, 2)}
            </pre>
          </ScrollArea>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancelRun}>
            Cancel run
          </Button>
          <Button variant="destructive" onClick={onDeny}>
            Deny
          </Button>
          <Button onClick={onAllow}>Allow</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
