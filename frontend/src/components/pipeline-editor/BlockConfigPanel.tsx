import { useState, useCallback, useEffect } from "react";
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
import { XIcon, StarFillIcon } from "@primer/octicons-react";
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

  // sync formData when node config changes
  useEffect(() => {
    setFormData(config || {});
  }, [node.id, config]);

  const handleChange = useCallback((key: string, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = useCallback(() => {
    onUpdate(node.id, formData);
  }, [node.id, formData, onUpdate]);

  const renderField = (key: string, schema: any) => {
    const value = formData[key] ?? schema.default ?? "";

    // boolean field
    if (schema.type === "boolean") {
      return <Checkbox checked={value} onChange={(e) => handleChange(key, e.target.checked)} />;
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
    // use TextInput with datalist to allow both selection and custom typing
    if (schema.isFieldReference) {
      const datalistId = `datalist-${key}`;
      return (
        <Box>
          <TextInput
            value={value}
            onChange={(e) => handleChange(key, e.target.value)}
            list={datalistId}
            placeholder={
              availableFields.length > 0 ? "Select or type field name" : "Type field name"
            }
            sx={{ width: "100%" }}
          />
          {availableFields.length > 0 && (
            <datalist id={datalistId}>
              {availableFields.map((field) => (
                <option key={field} value={field} />
              ))}
            </datalist>
          )}
        </Box>
      );
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
            height="300px"
            defaultLanguage="json"
            value={jsonValue}
            onChange={(newValue) => {
              // try {
              //   const parsed = JSON.parse(newValue || "{}");
              //   handleChange(key, parsed);
              // } catch {
              //   // keep as string if invalid JSON
              //   handleChange(key, newValue || "");
              // }
              handleChange(key, newValue);
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
        width: "400px",
        borderLeft: "1px solid",
        borderColor: "border.default",
        p: 3,
        overflowY: "auto",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Heading sx={{ fontSize: 2, color: "fg.default" }}>Configure</Heading>
        <Button onClick={onClose} variant="invisible" sx={{ p: 1, minWidth: "auto" }}>
          <XIcon />
        </Button>
      </Box>

      {/* Block name */}
      <Box sx={{ mb: 3 }}>
        <Text sx={{ fontWeight: "bold", display: "block", mb: 2, color: "fg.default" }}>
          {block.name}
        </Text>
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
