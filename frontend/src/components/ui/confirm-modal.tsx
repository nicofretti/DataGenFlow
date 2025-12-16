import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cva } from "class-variance-authority";
import { AlertTriangle, Info, AlertCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";
import { toast } from "sonner";

const overlayVariants = cva(
  "fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0"
);

const contentVariants = cva(
  "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-border bg-card p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] rounded-lg"
);

interface ConfirmModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void | Promise<void>;
  variant?: "danger" | "warning" | "info";
  confirmText?: string;
  cancelText?: string;
}

const iconMap = {
  danger: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const iconColorMap = {
  danger: "text-destructive",
  warning: "text-amber-600 dark:text-amber-400",
  info: "text-blue-600 dark:text-blue-400",
};

export function ConfirmModal({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  variant = "danger",
  confirmText = "Confirm",
  cancelText = "Cancel",
}: ConfirmModalProps) {
  const [loading, setLoading] = React.useState(false);
  const Icon = iconMap[variant];

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (error) {
      console.error("confirm action failed:", error);
      const message = error instanceof Error ? error.message : "Action failed. Please try again.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className={overlayVariants()} />
        <DialogPrimitive.Content className={contentVariants()}>
          <div className="flex gap-4 items-start">
            <div className={cn("shrink-0 mt-0.5", iconColorMap[variant])}>
              <Icon className="size-5" />
            </div>
            <div className="flex-1 min-w-0 pr-6">
              <DialogPrimitive.Title className="text-lg font-semibold text-card-foreground mb-2">
                {title}
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="text-sm text-muted-foreground">
                {description}
              </DialogPrimitive.Description>
            </div>
            <DialogPrimitive.Close
              className="shrink-0 rounded-sm opacity-70 text-muted-foreground ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none"
              aria-label="Close"
            >
              <X className="size-4" />
            </DialogPrimitive.Close>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
              className="min-w-[80px]"
            >
              {cancelText}
            </Button>
            <Button
              variant={variant === "danger" ? "destructive" : "default"}
              onClick={handleConfirm}
              disabled={loading}
              className="min-w-[100px]"
            >
              {loading ? "Loading..." : confirmText}
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
