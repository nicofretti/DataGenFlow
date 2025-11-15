import { useState, useEffect } from "react";
import { Box, Heading, Text, Button } from "@primer/react";
import { ChevronUpIcon, ChevronDownIcon, XIcon } from "@primer/octicons-react";
import { toast } from "sonner";

interface ConfigureFieldsModalProps {
  pipelineId: number;
  onClose: () => void;
  onSave: () => void;
}

export default function ConfigureFieldsModal({
  pipelineId,
  onClose,
  onSave,
}: ConfigureFieldsModalProps) {
  const [primaryFields, setPrimaryFields] = useState<string[]>([]);
  const [secondaryFields, setSecondaryFields] = useState<string[]>([]);
  const [hiddenFields, setHiddenFields] = useState<string[]>([]);
  const [draggedField, setDraggedField] = useState<string | null>(null);
  const [draggedFrom, setDraggedFrom] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAvailableFields();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipelineId]);

  const loadAvailableFields = async () => {
    try {
      // load available fields schema
      const schemaRes = await fetch(`/api/pipelines/${pipelineId}/accumulated_state_schema`);
      if (!schemaRes.ok) {
        throw new Error(`http ${schemaRes.status}`);
      }
      const schemaData = await schemaRes.json();
      const fields = schemaData.fields || [];

      // load existing validation_config from pipeline
      const pipelineRes = await fetch(`/api/pipelines/${pipelineId}`);
      if (!pipelineRes.ok) {
        throw new Error(`http ${pipelineRes.status}`);
      }
      const pipelineData = await pipelineRes.json();

      if (pipelineData.validation_config?.field_order) {
        // use existing configuration
        setPrimaryFields(pipelineData.validation_config.field_order.primary || []);
        setSecondaryFields(pipelineData.validation_config.field_order.secondary || []);
        setHiddenFields(pipelineData.validation_config.field_order.hidden || []);
      } else {
        // set default: primary = assistant, secondary = rest, hidden = none
        const assistant = fields.filter((f: string) => f === "assistant");
        const others = fields.filter((f: string) => f !== "assistant");
        setPrimaryFields(assistant);
        setSecondaryFields(others);
        setHiddenFields([]);
      }

      setLoading(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load available fields:", err);
      toast.error(`Failed to load field configuration: ${message}`);
      setLoading(false);
    }
  };

  const handleDragStart = (field: string, from: string) => {
    setDraggedField(field);
    setDraggedFrom(from);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (to: string) => {
    if (!draggedField || !draggedFrom) return;

    // if dropping in same section, do nothing
    if (draggedFrom === to) {
      setDraggedField(null);
      setDraggedFrom(null);
      return;
    }

    // remove from source
    if (draggedFrom === "primary") {
      setPrimaryFields(primaryFields.filter((f) => f !== draggedField));
    } else if (draggedFrom === "secondary") {
      setSecondaryFields(secondaryFields.filter((f) => f !== draggedField));
    } else if (draggedFrom === "hidden") {
      setHiddenFields(hiddenFields.filter((f) => f !== draggedField));
    }

    // add to target
    if (to === "primary") {
      setPrimaryFields([...primaryFields, draggedField]);
    } else if (to === "secondary") {
      setSecondaryFields([...secondaryFields, draggedField]);
    } else if (to === "hidden") {
      setHiddenFields([...hiddenFields, draggedField]);
    }

    setDraggedField(null);
    setDraggedFrom(null);
  };

  const handleDropOnField = (targetField: string, targetSection: string) => {
    if (!draggedField || !draggedFrom || draggedField === targetField) return;

    // get the appropriate fields array
    const getFieldsArray = (section: string) => {
      if (section === "primary") return primaryFields;
      if (section === "secondary") return secondaryFields;
      return hiddenFields;
    };

    const setFieldsArray = (section: string, fields: string[]) => {
      if (section === "primary") setPrimaryFields(fields);
      else if (section === "secondary") setSecondaryFields(fields);
      else setHiddenFields(fields);
    };

    // if same section, reorder
    if (draggedFrom === targetSection) {
      const fields = getFieldsArray(targetSection);
      const draggedIndex = fields.indexOf(draggedField);
      const targetIndex = fields.indexOf(targetField);

      const newFields = [...fields];
      newFields.splice(draggedIndex, 1);
      newFields.splice(targetIndex, 0, draggedField);

      setFieldsArray(targetSection, newFields);
    } else {
      // move between sections - insert before target
      const sourceFields = getFieldsArray(draggedFrom);
      const targetFields = getFieldsArray(targetSection);
      const targetIndex = targetFields.indexOf(targetField);

      setFieldsArray(
        draggedFrom,
        sourceFields.filter((f) => f !== draggedField)
      );

      const newTargetFields = [...targetFields];
      newTargetFields.splice(targetIndex, 0, draggedField);
      setFieldsArray(targetSection, newTargetFields);
    }

    setDraggedField(null);
    setDraggedFrom(null);
  };

  const moveField = (field: string, from: string, direction: "up" | "down") => {
    // move between sections
    if (from === "primary" && direction === "down") {
      setPrimaryFields(primaryFields.filter((f) => f !== field));
      setSecondaryFields([field, ...secondaryFields]);
    } else if (from === "secondary" && direction === "up") {
      setSecondaryFields(secondaryFields.filter((f) => f !== field));
      setPrimaryFields([...primaryFields, field]);
    } else if (from === "secondary" && direction === "down") {
      setSecondaryFields(secondaryFields.filter((f) => f !== field));
      setHiddenFields([field, ...hiddenFields]);
    } else if (from === "hidden" && direction === "up") {
      setHiddenFields(hiddenFields.filter((f) => f !== field));
      setSecondaryFields([...secondaryFields, field]);
    }
  };

  const handleSave = async () => {
    try {
      const validationConfig = {
        field_order: {
          primary: primaryFields,
          secondary: secondaryFields,
          hidden: hiddenFields,
        },
      };

      const res = await fetch(`/api/pipelines/${pipelineId}/validation_config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(validationConfig),
      });

      if (!res.ok) {
        throw new Error("Failed to save configuration");
      }

      onSave();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to save field configuration:", err);
      toast.error(`Failed to save field configuration: ${message}`);
    }
  };

  const renderFieldList = (
    fields: string[],
    section: string,
    title: string,
    description: string
  ) => (
    <Box
      sx={{
        border: "2px dashed",
        borderColor: "border.default",
        borderRadius: 2,
        p: 3,
        minHeight: "150px",
        bg: "canvas.subtle",
      }}
      onDragOver={handleDragOver}
      onDrop={() => handleDrop(section)}
    >
      <Text sx={{ fontSize: 1, fontWeight: "bold", mb: 1, color: "fg.default", display: "block" }}>
        {title}
      </Text>
      <Text sx={{ fontSize: 0, color: "fg.muted", mb: 2, display: "block" }}>{description}</Text>

      {fields.length === 0 ? (
        <Text sx={{ fontSize: 1, color: "fg.muted", fontStyle: "italic" }}>
          Drag fields here or use arrow buttons
        </Text>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {fields.map((field) => (
            <Box
              key={field}
              draggable
              onDragStart={() => handleDragStart(field, section)}
              onDragOver={handleDragOver}
              onDrop={(e: React.DragEvent) => {
                e.stopPropagation();
                handleDropOnField(field, section);
              }}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                p: 2,
                bg: "canvas.default",
                border: "1px solid",
                borderColor: "border.default",
                borderRadius: 1,
                cursor: "grab",
                "&:active": {
                  cursor: "grabbing",
                },
              }}
            >
              <Text sx={{ fontSize: 1, color: "fg.default", fontFamily: "mono" }}>{field}</Text>
              <Box sx={{ display: "flex", gap: 1 }}>
                {section !== "primary" && (
                  <Button
                    size="small"
                    leadingVisual={ChevronUpIcon}
                    onClick={() => moveField(field, section, "up")}
                    aria-label="Move up"
                  />
                )}
                {section !== "hidden" && (
                  <Button
                    size="small"
                    leadingVisual={ChevronDownIcon}
                    onClick={() => moveField(field, section, "down")}
                    aria-label="Move down"
                  />
                )}
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );

  if (loading) {
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
        }}
      >
        <Box
          sx={{
            bg: "canvas.default",
            borderRadius: 2,
            p: 4,
            maxWidth: "600px",
            border: "1px solid",
            borderColor: "border.default",
          }}
        >
          <Text sx={{ color: "fg.default" }}>Loading available fields...</Text>
        </Box>
      </Box>
    );
  }

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
      }}
      onClick={onClose}
    >
      <Box
        sx={{
          bg: "canvas.default",
          borderRadius: 2,
          p: 4,
          maxWidth: "800px",
          width: "90%",
          maxHeight: "90vh",
          overflow: "auto",
          border: "1px solid",
          borderColor: "border.default",
        }}
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Box>
            <Heading sx={{ mb: 1, color: "fg.default" }}>Configure Field Layout</Heading>
            <Text sx={{ fontSize: 1, color: "fg.muted" }}>
              Drag fields or use arrow buttons to organize how they appear
            </Text>
          </Box>
          <Button leadingVisual={XIcon} onClick={onClose} aria-label="Close" />
        </Box>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mb: 4 }}>
          {renderFieldList(
            primaryFields,
            "primary",
            "Primary Fields",
            "Large, prominent display. Main content for review."
          )}
          {renderFieldList(
            secondaryFields,
            "secondary",
            "Secondary Fields",
            "Smaller, less prominent. Supporting information."
          )}
          {renderFieldList(
            hiddenFields,
            "hidden",
            "Hidden Fields",
            "Not displayed in review. Available in trace."
          )}
        </Box>

        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSave}>
            Save Configuration
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
