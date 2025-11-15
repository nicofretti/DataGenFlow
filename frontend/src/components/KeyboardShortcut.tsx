import { Box, Text } from "@primer/react";

interface KeyboardShortcutProps {
  shortcut: string;
  label: string;
}

export default function KeyboardShortcut({ shortcut, label }: KeyboardShortcutProps) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Box
        as="kbd"
        sx={{
          padding: "2px 6px",
          border: "1px solid",
          borderColor: "border.default",
          borderRadius: "3px",
          fontSize: "11px",
          fontFamily: "monospace",
          color: "fg.default",
          bg: "canvas.subtle",
        }}
      >
        {shortcut}
      </Box>
      <Text sx={{ color: "fg.default" }}>{label}</Text>
    </Box>
  );
}
