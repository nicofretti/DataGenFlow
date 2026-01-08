import { useState, useCallback, useEffect, useRef } from "react";
import {
  Box,
  Heading,
  Button,
  TextInput,
  Textarea,
  Checkbox,
  Text,
  useTheme,
  Select,
  Tooltip,
} from "@primer/react";
import { XIcon, StarFillIcon, KeyAsteriskIcon } from "@primer/octicons-react";
import { Node } from "reactflow";
import Editor from "@monaco-editor/react";

interface BlockConfigPanelProps {
  node: Node;
  onUpdate: (nodeId: string, config: Record<string, any>) => void;
  onClose: () => void;
  availableFields?: string[];
}

export default function BlockConfigPanel({
  node,
  onUpdate,
  onClose,
  availableFields = [],
}: BlockConfigPanelProps) {
  const { block, config } = node.data;
  const [formData, setFormData] = useState<Record<string, any>>(config || {});
  const { resolvedColorScheme } = useTheme();
  const [wordWrap, setWordWrap] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [panelWidth, setPanelWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);

  // sync formData with parent config changes
  // this ensures that saved config persists when panel is reopened
  //
  // key behaviors:
  // 1. when panel opens: refs are null (from cleanup) → formData syncs with config
  // 2. when switching nodes: node.id changes → formData syncs with new node's config
  // 3. when config saved: config changes for same node → formData syncs with updated config
  // 4. while editing: neither changes → formData preserves user edits
  //
  // why we track both node.id AND config:
  // - node.id alone: won't detect when user saves config and reopens panel for same node
  // - config alone: would reset formData while user is typing if parent re-renders
  //
  // why we reset refs on unmount:
  // - when panel closes and reopens, refs are null → condition triggers → formData syncs
  // - without reset, reopening same node would skip sync (prevNodeIdRef === node.id)
  const prevNodeIdRef = useRef<string | null>(null);
  const prevConfigRef = useRef<Record<string, any> | null>(null);

  useEffect(() => {
    const nodeChanged = prevNodeIdRef.current !== node.id;
    const configChanged = JSON.stringify(prevConfigRef.current) !== JSON.stringify(config);

    if (nodeChanged || configChanged) {
      prevNodeIdRef.current = node.id;
      prevConfigRef.current = config;
      setFormData(config || {});
      setErrors({});
    }
  }, [node.id, config]);

  // reset refs when component unmounts (panel closes)
  useEffect(() => {
    return () => {
      prevNodeIdRef.current = null;
      prevConfigRef.current = null;
    };
  }, []);

  // handle resize
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX;
      setPanelWidth(Math.max(300, Math.min(800, newWidth)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const handleChange = useCallback((key: string, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    // clear error for this field when user starts editing
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[key];
      return newErrors;
    });
  }, []);

  const handleSave = useCallback(() => {
    // validate and parse JSON strings for array/object fields before saving
    const processedData = { ...formData };
    const schema = block.config_schema?.properties || {};
    const validationErrors: Record<string, string> = {};

    Object.entries(schema).forEach(([key, fieldSchema]: [string, any]) => {
      const value = processedData[key];
      if (
        (fieldSchema.type === "array" || fieldSchema.type === "object") &&
        typeof value === "string"
      ) {
        try {
          processedData[key] = JSON.parse(value);
        } catch (e) {
          validationErrors[key] = `Invalid JSON: ${e instanceof Error ? e.message : "parse error"}`;
        }
      }
    });

    // if there are validation errors, show them and don't close panel
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    // validation passed, clear errors, update config and close panel
    setErrors({});
    onUpdate(node.id, processedData);
    onClose();
  }, [node.id, formData, onUpdate, onClose, block.config_schema]);

  const renderField = (key: string, schema: any) => {
    const value = formData[key] ?? schema.default ?? "";

    // boolean field
    if (schema.type === "boolean") {
      return <Checkbox checked={value} onChange={(e) => handleChange(key, e.target.checked)} />;
    }

    // multi-select enum (array with enum items)
    if (schema.type === "array" && schema.items?.enum && Array.isArray(schema.items.enum)) {
      const selectedValues = Array.isArray(value) ? value : [];
      const options = schema.items.enum;

      const handleToggle = (option: string) => {
        const newValues = selectedValues.includes(option)
          ? selectedValues.filter((v) => v !== option)
          : [...selectedValues, option];
        handleChange(key, newValues);
      };

      return (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            p: 2,
            borderRadius: 2,
            bg: "canvas.subtle",
          }}
        >
          {options.map((option: string) => (
            <Box key={option} sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Checkbox
                checked={selectedValues.includes(option)}
                onChange={() => handleToggle(option)}
              />
              <Text
                sx={{
                  color: "fg.default",
                }}
              >
                {option}
              </Text>
            </Box>
          ))}
        </Box>
      );
    }

    // enum dropdown (predefined options)
    if (schema.enum && Array.isArray(schema.enum)) {
      return (
        <Select
          value={value}
          onChange={(e) => handleChange(key, e.target.value)}
          sx={{ width: "100%" }}
        >
          {schema.enum.map((option: string) => (
            <Select.Option key={option} value={option}>
              {option}
            </Select.Option>
          ))}
        </Select>
      );
    }

    // field reference dropdown (references to accumulated_state fields)
    if (schema.isFieldReference) {
      if (availableFields.length > 0) {
        // include current value if not in available fields
        const allOptions =
          value && !availableFields.includes(value) ? [value, ...availableFields] : availableFields;

        return (
          <Select
            value={value}
            onChange={(e) => handleChange(key, e.target.value)}
            sx={{ width: "100%" }}
          >
            {allOptions.map((field) => (
              <Select.Option key={field} value={field}>
                {field}
              </Select.Option>
            ))}
          </Select>
        );
      } else {
        // fallback to text input when no fields available
        return (
          <TextInput
            value={value}
            onChange={(e) => handleChange(key, e.target.value)}
            placeholder="Type field name"
            sx={{ width: "100%" }}
          />
        );
      }
    }

    // number field
    if (schema.type === "number" || schema.type === "integer") {
      return (
        <TextInput
          type="number"
          value={value}
          onChange={(e) => handleChange(key, parseFloat(e.target.value))}
          sx={{ width: "100%" }}
        />
      );
    }

    // detect if field is a template/code field
    const isTemplateField =
      schema.format === "jinja2" ||
      schema.format === "template" ||
      key.toLowerCase().includes("prompt") ||
      key.toLowerCase().includes("template") ||
      key.toLowerCase().includes("instruction");

    // use monaco editor for template fields
    if (isTemplateField) {
      return (
        <Box
          sx={{
            border: "1px solid",
            borderColor: "border.default",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <Editor
            key={`${node.id}-${key}`}
            height="200px"
            defaultLanguage="python"
            value={value}
            onChange={(newValue) => handleChange(key, newValue || "")}
            theme={resolvedColorScheme === "dark" ? "vs-dark" : "light"}
            options={{
              minimap: { enabled: false },
              scrollbar: {
                vertical: "auto",
                horizontal: "auto",
                verticalScrollbarSize: 10,
                horizontalScrollbarSize: 10,
              },
              lineNumbers: "on",
              lineNumbersMinChars: 3,
              glyphMargin: false,
              folding: false,
              lineDecorationsWidth: 5,
              scrollBeyondLastLine: false,
              renderLineHighlight: "none",
              overviewRulerLanes: 0,
              hideCursorInOverviewRuler: true,
              overviewRulerBorder: false,
              insertSpaces: true,
              renderWhitespace: true,
              wordWrap: wordWrap ? "on" : "off",
              fontSize: 13,
              fontFamily:
                "ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace",
              tabSize: 2,
              padding: { top: 8, bottom: 8 },
            }}
          />
        </Box>
      );
    }

    // object or array field - use monaco editor with JSON
    if (schema.type === "object" || schema.type === "array") {
      const jsonValue = typeof value === "string" ? value : JSON.stringify(value, null, 2);
      return (
        <Box
          sx={{
            border: "1px solid",
            borderColor: "border.default",
            borderRadius: 2,
            overflow: "hidden",
          }}
        >
          <Editor
            key={`${node.id}-${key}`}
            height="300px"
            defaultLanguage="json"
            value={jsonValue}
            onChange={(newValue) => {
              // keep as string during editing, will be parsed on save
              handleChange(key, newValue || "");
            }}
            theme={resolvedColorScheme === "dark" ? "vs-dark" : "light"}
            options={{
              minimap: { enabled: false },
              scrollbar: {
                vertical: "auto",
                horizontal: "auto",
                verticalScrollbarSize: 10,
                horizontalScrollbarSize: 10,
              },
              lineNumbers: "on",
              lineNumbersMinChars: 3,
              glyphMargin: false,
              folding: true,
              lineDecorationsWidth: 5,
              scrollBeyondLastLine: false,
              renderLineHighlight: "none",
              overviewRulerLanes: 0,
              hideCursorInOverviewRuler: true,
              overviewRulerBorder: false,
              wordWrap: wordWrap ? "on" : "off",
              fontSize: 13,
              fontFamily:
                "ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace",
              tabSize: 2,
              padding: { top: 8, bottom: 8 },
            }}
          />
        </Box>
      );
    }

    // string field - use textarea for long strings or multiline
    const isLongString = typeof value === "string" && value.length > 100;
    const isMultiline =
      schema.format === "multiline" ||
      schema.format === "text" ||
      key.toLowerCase().includes("description");

    if (isLongString || isMultiline) {
      return (
        <Textarea
          value={value}
          onChange={(e) => handleChange(key, e.target.value)}
          sx={{ width: "100%", fontFamily: "mono", fontSize: 1 }}
          rows={Math.min(Math.max(4, (value.split("\n").length || 1) + 1), 12)}
        />
      );
    }

    // default: short string field
    return (
      <TextInput
        value={value}
        onChange={(e) => handleChange(key, e.target.value)}
        sx={{ width: "100%" }}
      />
    );
  };

  return (
    <Box
      sx={{
        width: `${panelWidth}px`,
        borderLeft: "1px solid",
        borderColor: "border.default",
        p: 3,
        overflowY: "auto",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        position: "relative",
      }}
    >
      {/* Resize handle */}
      <Box
        onMouseDown={() => setIsResizing(true)}
        sx={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: "4px",
          cursor: "col-resize",
          bg: isResizing ? "accent.emphasis" : "transparent",
          "&:hover": {
            bg: "accent.muted",
          },
          transition: "background-color 0.1s ease",
          zIndex: 10,
        }}
      />
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Box sx={{ color: "fg.default" }}>
            <KeyAsteriskIcon />
          </Box>
          <Heading sx={{ fontSize: 2, color: "fg.default" }}>{block.name}</Heading>
        </Box>
        <Button onClick={onClose} variant="invisible" sx={{ p: 1, minWidth: "auto" }}>
          <XIcon />
        </Button>
      </Box>

      {/* Block name */}
      <Box sx={{ mb: 3 }}>
        {block.description && (
          <Text sx={{ fontSize: 0, color: "fg.muted" }}>{block.description}</Text>
        )}
      </Box>

      {/* Config fields */}
      <Box sx={{ flex: 1, mb: 3 }}>
        {Object.entries(block.config_schema?.properties || {})
          .sort(([, schemaA]: [string, any], [, schemaB]: [string, any]) => {
            // fields with descriptions come first
            const hasDescA = !!schemaA.description;
            const hasDescB = !!schemaB.description;
            if (hasDescA && !hasDescB) return -1;
            if (!hasDescA && hasDescB) return 1;
            return 0;
          })
          .map(([key, schema]: [string, any]) => {
            const isTemplateField =
              schema.format === "jinja2" ||
              schema.format === "template" ||
              key.toLowerCase().includes("prompt") ||
              key.toLowerCase().includes("template") ||
              key.toLowerCase().includes("instruction");

            const hasDescription = !!schema.description;

            return (
              <Box key={key} sx={{ mb: 3 }}>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1, gap: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    {hasDescription && (
                      <Tooltip aria-label="Important setting" direction="l">
                        <Box
                          sx={{
                            color: "attention.fg",
                            display: "flex",
                            alignItems: "center",
                            cursor: "help",
                          }}
                        >
                          <StarFillIcon size={14} />
                        </Box>
                      </Tooltip>
                    )}
                    <Text
                      sx={{
                        fontSize: 1,
                        fontWeight: "bold",
                        color: "fg.default",
                      }}
                    >
                      {key}
                      {schema.required && (
                        <Text as="span" sx={{ color: "danger.fg", ml: 1 }}>
                          *
                        </Text>
                      )}
                      {schema.default !== undefined && schema.default !== null && (
                        <Text
                          as="span"
                          sx={{ fontSize: 0, color: "fg.muted", ml: 2, fontWeight: "normal" }}
                        >
                          (default:{" "}
                          {typeof schema.default === "object"
                            ? Array.isArray(schema.default) && schema.default.length === 0
                              ? "[]"
                              : Object.keys(schema.default).length === 0
                                ? "{}"
                                : "see editor"
                            : String(schema.default)}
                          )
                        </Text>
                      )}
                    </Text>
                  </Box>
                  {isTemplateField && (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: "auto" }}>
                      <Checkbox
                        checked={wordWrap}
                        onChange={(e) => setWordWrap(e.target.checked)}
                        id={`wordwrap-${key}`}
                        sx={{ m: 0 }}
                      />
                      <Text
                        as="label"
                        htmlFor={`wordwrap-${key}`}
                        sx={{ fontSize: 0, color: "fg.muted", cursor: "pointer" }}
                      >
                        Wrap
                      </Text>
                    </Box>
                  )}
                </Box>
                {schema.description && (
                  <Text
                    sx={{
                      fontSize: 0,
                      color: "fg.muted",
                      display: "block",
                      mb: 1,
                    }}
                  >
                    {schema.description}
                  </Text>
                )}
                {renderField(key, schema)}
                {errors[key] && (
                  <Text
                    sx={{
                      fontSize: 0,
                      color: "danger.fg",
                      display: "block",
                      mt: 1,
                      fontWeight: "bold",
                    }}
                  >
                    {errors[key]}
                  </Text>
                )}
              </Box>
            );
          })}
      </Box>

      <Box sx={{ display: "flex", gap: 2 }}>
        <Button onClick={handleSave} variant="primary" sx={{ flex: 1 }}>
          Apply Config
        </Button>
        <Button onClick={onClose} sx={{ flex: 1 }}>
          Cancel
        </Button>
      </Box>
    </Box>
  );
}
