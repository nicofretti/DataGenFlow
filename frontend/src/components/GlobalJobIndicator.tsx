import { Box, Text, Spinner } from "@primer/react";
import { useJob } from "../contexts/JobContext";

export default function GlobalJobIndicator() {
  const { currentJob } = useJob();

  if (!currentJob || currentJob.status !== "running") return null;

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
      <Spinner size="small" />
      <Text sx={{ fontSize: 1, color: "fg.muted" }}>
        Generating... {Math.round(currentJob.progress * 100)}%
      </Text>
    </Box>
  );
}
