import { useEffect } from "react";
import { Box, Button } from "@primer/react";
import { XIcon } from "@primer/octicons-react";
import SingleRecordView from "./SingleRecordView";

interface Record {
  id: number;
  output: string;
  status: string;
  metadata: any;
  trace?: Array<{
    block_type: string;
    input: any;
    output: any;
    accumulated_state?: any;
    error?: string;
  }>;
}

interface ValidationConfig {
  field_order: {
    primary: string[];
    secondary: string[];
    hidden: string[];
  };
}

interface RecordDetailsModalProps {
  record: Record | null;
  validationConfig: ValidationConfig | null;
  onClose: () => void;
  onAccept: () => void;
  onReject: () => void;
  onSetPending: () => void;
  onEdit: (updates: Record<string, any>) => void;
}

export default function RecordDetailsModal({
  record,
  validationConfig,
  onClose,
  onAccept,
  onReject,
  onSetPending,
  onEdit,
}: RecordDetailsModalProps) {
  // close on escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!record) return null;

  return (
    <Box
      sx={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        bg: "rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        overflow: "auto",
        p: 4,
      }}
      onClick={onClose}
    >
      <Box
        sx={{
          bg: "canvas.default",
          borderRadius: 2,
          p: 4,
          maxWidth: "900px",
          width: "100%",
          maxHeight: "90vh",
          overflow: "auto",
          border: "1px solid",
          borderColor: "border.default",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* close button */}
        <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
          <Button leadingVisual={XIcon} onClick={onClose} aria-label="Close" size="small" />
        </Box>

        {/* single record view - no navigation */}
        <SingleRecordView
          record={record}
          validationConfig={validationConfig}
          currentIndex={0}
          totalRecords={1}
          onNext={() => {}}
          onPrevious={() => {}}
          onAccept={onAccept}
          onReject={onReject}
          onSetPending={onSetPending}
          onEdit={onEdit}
          isPending={record.status === "pending"}
        />
      </Box>
    </Box>
  );
}
