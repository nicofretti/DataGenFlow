import { useState, useCallback, useEffect, useMemo } from "react";
import { Box, Text, Button, Label, Textarea } from "@primer/react";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  XCircleIcon,
  SquareCircleIcon,
  ArrowLeftIcon,
} from "@primer/octicons-react";
import type { RecordData, ValidationConfig } from "../types";
import { getStatusVariant } from "../utils/status";

interface SingleRecordViewProps {
  record: RecordData;
  validationConfig: ValidationConfig | null;
  currentIndex: number;
  totalRecords: number;
  onNext: () => void;
  onPrevious: () => void;
  onAccept: () => void;
  onReject: () => void;
  onSetPending: () => void;
  onEdit: (updates: Record<string, any>) => void;
  onRegisterStartEditing?: (fn: () => void) => void;
  isPending: boolean;
}

export default function SingleRecordView({
  record,
  validationConfig,
  currentIndex,
  totalRecords,
  onNext,
  onPrevious,
  onAccept,
  onReject,
  onSetPending,
  onEdit,
  onRegisterStartEditing,
  isPending: _isPending,
}: SingleRecordViewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [isExpanded, setIsExpanded] = useState(false);

  // get final accumulated state from trace
  const finalState = useMemo(
    () =>
      record.trace && record.trace.length > 0
        ? record.trace[record.trace.length - 1].accumulated_state || {}
        : {},
    [record.trace]
  );

  // determine field order
  const primaryFields = useMemo(
    () => validationConfig?.field_order.primary || ["assistant"],
    [validationConfig?.field_order.primary]
  );
  const secondaryFields = useMemo(
    () => validationConfig?.field_order.secondary || [],
    [validationConfig?.field_order.secondary]
  );

  const startEditing = useCallback(() => {
    const initial: Record<string, string> = {};
    primaryFields.forEach((field) => {
      const value = finalState[field];
      initial[field] = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    });
    setEditValues(initial);
    setIsEditing(true);
    setIsExpanded(true);
  }, [primaryFields, finalState]);

  // register startEditing function with parent
  useEffect(() => {
    onRegisterStartEditing?.(startEditing);
  }, [startEditing, onRegisterStartEditing]);

  const saveEdit = async () => {
    await onEdit(editValues);
    setIsEditing(false);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setIsExpanded(false);
  };

  const renderFieldValue = (value: unknown, isLarge: boolean = false) => {
    const valueStr = typeof value === "string" ? value : JSON.stringify(value, null, 2) || "";
    const maxLength = isLarge ? 500 : 200;

    return (
      <Box>
        <Box
          sx={{
            maxHeight: isExpanded ? "none" : isLarge ? "300px" : "150px",
            overflow: isExpanded ? "visible" : "hidden",
            position: "relative",
          }}
        >
          <Text
            as="div"
            sx={{
              fontSize: isLarge ? 2 : 1,
              whiteSpace: "pre-wrap",
              lineHeight: 1.6,
              color: "fg.default",
              fontFamily: typeof value === "object" ? "mono" : "normal",
            }}
          >
            {valueStr}
          </Text>
          {!isExpanded && valueStr.length > maxLength && (
            <Box
              sx={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: "60px",
                background: "linear-gradient(transparent, var(--bgColor-default))",
              }}
            />
          )}
        </Box>
        {valueStr.length > maxLength && (
          <Button
            size="small"
            variant="invisible"
            onClick={() => setIsExpanded(!isExpanded)}
            sx={{ mt: 2 }}
          >
            {isExpanded ? "Show less" : "Show more"}
          </Button>
        )}
      </Box>
    );
  };

  return (
    <Box>
      {/* progress and navigation */}
      <Box sx={{ mb: 3, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Text sx={{ fontSize: 1, color: "fg.default" }}>
          Record {currentIndex + 1} of {totalRecords}
        </Text>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button
            size="small"
            leadingVisual={ChevronLeftIcon}
            onClick={onPrevious}
            disabled={currentIndex === 0}
          >
            Previous
          </Button>
          <Button
            size="small"
            trailingVisual={ChevronRightIcon}
            onClick={onNext}
            disabled={currentIndex === totalRecords - 1}
          >
            Next
          </Button>
        </Box>
      </Box>

      {/* record card */}
      <Box
        sx={{
          border: "1px solid",
          borderColor: "border.default",
          borderRadius: 2,
          p: 4,
          bg: "canvas.subtle",
        }}
      >
        {/* header with id and status */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
          <Text sx={{ fontWeight: "bold", color: "fg.default", fontSize: 1 }}>#{record.id}</Text>
          <Label variant={getStatusVariant(record.status)}>{record.status}</Label>
        </Box>

        {/* metrics section */}
        {record.metrics && Object.keys(record.metrics).length > 0 && (
          <Box
            sx={{
              border: "1px solid",
              borderColor: "border.default",
              borderRadius: 2,
              p: 3,
              bg: "canvas.default",
              mb: 3,
            }}
          >
            <Text as="div" sx={{ fontSize: 1, fontWeight: "semibold", mb: 2, color: "fg.default" }}>
              Quality Metrics
            </Text>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: 2,
              }}
            >
              {Object.entries(record.metrics).map(([key, value]) => (
                <Box
                  key={key}
                  sx={{
                    border: "1px solid",
                    borderColor: "border.muted",
                    borderRadius: 1,
                    p: 2,
                    bg: "canvas.subtle",
                  }}
                >
                  <Text
                    as="div"
                    sx={{ fontSize: 0, color: "fg.muted", mb: 1, textTransform: "capitalize" }}
                  >
                    {key}
                  </Text>
                  <Text as="div" sx={{ fontSize: 2, fontWeight: "bold", color: "fg.default" }}>
                    {value.toFixed(2)}
                  </Text>
                </Box>
              ))}
            </Box>
          </Box>
        )}

        {/* algorithm info */}
        {record.algorithm && (
          <Box sx={{ mb: 3 }}>
            <Text sx={{ fontSize: 1, color: "fg.muted" }}>
              Generated using:{" "}
              <Label variant="accent" size="small">
                {record.algorithm}
              </Label>
            </Text>
          </Box>
        )}

        {/* primary fields - large and prominent */}
        {primaryFields.length > 0 && (
          <Box sx={{ mb: 4 }}>
            {primaryFields.map((field) => (
              <Box key={field} sx={{ mb: 3 }}>
                <Text
                  as="div"
                  sx={{ fontSize: 1, fontWeight: "semibold", mb: 2, color: "fg.default" }}
                >
                  {field}
                </Text>
                {isEditing ? (
                  <Textarea
                    value={editValues[field] || ""}
                    onChange={(e) => setEditValues({ ...editValues, [field]: e.target.value })}
                    rows={12}
                    sx={{
                      width: "100%",
                      fontFamily: "mono",
                      fontSize: 1,
                      color: "fg.default",
                      bg: "canvas.default",
                      borderColor: "border.default",
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      border: "1px solid",
                      borderColor: "border.default",
                      borderRadius: 2,
                      p: 3,
                      bg: "canvas.default",
                    }}
                  >
                    {renderFieldValue(finalState[field], true)}
                  </Box>
                )}
              </Box>
            ))}
          </Box>
        )}

        {/* secondary fields - smaller and less prominent */}
        {secondaryFields.length > 0 && !isEditing && (
          <Box sx={{ mb: 3 }}>
            <Text as="div" sx={{ fontSize: 1, fontWeight: "semibold", mb: 2, color: "fg.muted" }}>
              Additional Fields
            </Text>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {secondaryFields.map((field) => (
                <Box
                  key={field}
                  sx={{
                    border: "1px solid",
                    borderColor: "border.muted",
                    borderRadius: 1,
                    p: 2,
                    bg: "canvas.inset",
                  }}
                >
                  <Text
                    as="div"
                    sx={{ fontSize: 0, fontWeight: "semibold", mb: 1, color: "fg.muted" }}
                  >
                    {field}
                  </Text>
                  {renderFieldValue(finalState[field], false)}
                </Box>
              ))}
            </Box>
          </Box>
        )}

        {/* final accumulated state - collapsible */}
        {record.trace && record.trace.length > 0 && (
          <Box
            sx={{
              border: "1px solid",
              borderColor: "border.muted",
              borderRadius: 2,
              p: 3,
              bg: "canvas.inset",
              mb: 3,
            }}
          >
            <details>
              <summary
                style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  marginBottom: "12px",
                  color: "inherit",
                }}
              >
                <Box
                  component="span"
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 1,
                    color: "fg.default",
                  }}
                >
                  <Text sx={{ fontSize: 1, fontWeight: "semibold", color: "fg.default" }}>
                    Full Accumulated State
                  </Text>
                </Box>
              </summary>

              <Box sx={{ mt: 2 }}>
                <Box
                  sx={{
                    fontFamily: "mono",
                    fontSize: 0,
                    p: 2,
                    bg: "canvas.default",
                    borderRadius: 1,
                    overflow: "auto",
                    maxHeight: "400px",
                    color: "fg.default",
                  }}
                >
                  <pre style={{ margin: 0 }}>{JSON.stringify(finalState, null, 2)}</pre>
                </Box>
              </Box>
            </details>
          </Box>
        )}

        {/* execution trace - collapsible */}
        {record.trace && record.trace.length > 0 && (
          <Box
            sx={{
              border: "1px solid",
              borderColor: "border.muted",
              borderRadius: 2,
              p: 3,
              bg: "canvas.inset",
            }}
          >
            <details>
              <summary
                style={{
                  cursor: "pointer",
                  fontWeight: 600,
                  marginBottom: "12px",
                  color: "inherit",
                }}
              >
                <Box
                  component="span"
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 1,
                    color: "fg.default",
                  }}
                >
                  <Text sx={{ fontSize: 1, fontWeight: "semibold", color: "fg.default" }}>
                    Execution Trace ({record.trace.length} blocks)
                  </Text>
                </Box>
              </summary>

              <Box sx={{ mt: 2 }}>
                {record.trace.map((step, index) => (
                  <Box
                    key={index}
                    sx={{
                      mb: 3,
                      pb: 3,
                      borderBottom: index < record.trace!.length - 1 ? "1px solid" : "none",
                      borderColor: step.error ? "danger.emphasis" : "border.muted",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
                      <Text
                        as="div"
                        sx={{
                          fontSize: 1,
                          fontWeight: "semibold",
                          color: step.error ? "danger.fg" : "fg.default",
                        }}
                      >
                        {index + 1}. {step.block_type}
                      </Text>
                      {step.error && (
                        <Label variant="danger" sx={{ fontSize: 0 }}>
                          Failed
                        </Label>
                      )}
                    </Box>
                    {step.error && (
                      <Box
                        sx={{
                          mb: 2,
                          fontSize: 0,
                          p: 2,
                          bg: "danger.subtle",
                          border: "1px solid",
                          borderColor: "danger.muted",
                          borderRadius: 2,
                          color: "danger.fg",
                        }}
                      >
                        {step.error}
                      </Box>
                    )}
                    <Box
                      sx={{
                        fontFamily: "mono",
                        fontSize: 0,
                        p: 2,
                        bg: "canvas.default",
                        borderRadius: 1,
                        overflow: "auto",
                        maxHeight: "200px",
                        color: "fg.default",
                      }}
                    >
                      <pre style={{ margin: 0 }}>
                        {JSON.stringify({ input: step.input, output: step.output }, null, 2)}
                      </pre>
                    </Box>
                  </Box>
                ))}
              </Box>
            </details>
          </Box>
        )}

        {/* action buttons */}
        {isEditing ? (
          <Box sx={{ display: "flex", gap: 2, mt: 4 }}>
            <Button size="medium" variant="primary" onClick={saveEdit}>
              Save
            </Button>
            <Button size="medium" onClick={cancelEdit}>
              Cancel
            </Button>
          </Box>
        ) : record.status === "pending" ? (
          <Box sx={{ display: "flex", gap: 2, mt: 4 }}>
            <Button
              variant="primary"
              size="medium"
              leadingVisual={CheckCircleIcon}
              onClick={onAccept}
            >
              Accept <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>A</kbd>
            </Button>
            <Button variant="danger" size="medium" leadingVisual={XCircleIcon} onClick={onReject}>
              Reject <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>R</kbd>
            </Button>
            <Button size="medium" leadingVisual={SquareCircleIcon} onClick={startEditing}>
              Edit <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>E</kbd>
            </Button>
          </Box>
        ) : record.status === "accepted" ? (
          <Box sx={{ display: "flex", gap: 2, mt: 4 }}>
            <Button size="medium" leadingVisual={ArrowLeftIcon} onClick={onSetPending}>
              Set Pending <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>U</kbd>
            </Button>
            <Button variant="danger" size="medium" leadingVisual={XCircleIcon} onClick={onReject}>
              Reject <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>R</kbd>
            </Button>
            <Button size="medium" leadingVisual={SquareCircleIcon} onClick={startEditing}>
              Edit
            </Button>
          </Box>
        ) : record.status === "rejected" ? (
          <Box sx={{ display: "flex", gap: 2, mt: 4 }}>
            <Button
              variant="primary"
              size="medium"
              leadingVisual={CheckCircleIcon}
              onClick={onAccept}
            >
              Accept <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>A</kbd>
            </Button>
            <Button size="medium" leadingVisual={ArrowLeftIcon} onClick={onSetPending}>
              Set Pending <kbd style={{ marginLeft: "8px", opacity: 0.6 }}>U</kbd>
            </Button>
            <Button size="medium" onClick={startEditing}>
              Edit
            </Button>
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
