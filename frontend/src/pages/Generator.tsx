import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Heading,
  FormControl,
  Button,
  Flash,
  Text,
  Select,
  Spinner,
  ProgressBar,
  Label,
} from "@primer/react";
import { PlayIcon, XIcon, UploadIcon } from "@primer/octicons-react";
import { useJob } from "../contexts/JobContext";
import type { Pipeline } from "../types";
import { getElapsedTime } from "../utils/format";
import { getStatusColor } from "../utils/status";
import { toast } from "sonner";

interface SeedData {
  repetitions?: number;
  metadata: Record<string, unknown>;
}

export default function Generator() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { currentJob, setCurrentJob } = useJob();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null);
  const [isMultiplierPipeline, setIsMultiplierPipeline] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  } | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const validateSeeds = useCallback(
    async (seedsData: SeedData[]) => {
      if (!selectedPipeline) {
        return;
      }

      setIsValidating(true);
      try {
        const res = await fetch("/api/seeds/validate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            pipeline_id: selectedPipeline,
            seeds: seedsData,
          }),
        });

        if (!res.ok) {
          console.error("Validation request failed:", res.status);
          toast.error("Failed to validate seeds");
          setValidationResult(null);
          return;
        }

        const result = await res.json();
        setValidationResult(result);

        if (result.valid) {
          toast.success("All seeds are valid. Ready to generate!");
        } else {
          toast.error("Seed validation failed");
        }

        if (result.warnings && result.warnings.length > 0) {
          result.warnings.forEach((warning: string) => {
            toast.warning(`⚠️ ${warning}`);
          });
        }
      } catch (err) {
        console.error("Validation failed:", err);
        toast.error("Validation error occurred");
        setValidationResult(null);
      } finally {
        setIsValidating(false);
      }
    },
    [selectedPipeline]
  );

  useEffect(() => {
    fetchPipelines();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;

    const fetchPipelineDetails = async () => {
      if (!selectedPipeline) {
        if (mounted) {
          setIsMultiplierPipeline(false);
          setValidationResult(null);
        }
        return;
      }

      try {
        const res = await fetch(`/api/pipelines/${selectedPipeline}`, {
          signal: controller.signal,
        });
        const data = await res.json();
        const isMultiplier = data.first_block_is_multiplier || false;

        if (!mounted) return;

        if (file) {
          const isMarkdown = file.name.endsWith(".md");
          const isJson = file.name.endsWith(".json");

          if ((isMultiplier && isJson) || (!isMultiplier && isMarkdown)) {
            setFile(null);
            setValidationResult(null);
          }
        }

        setIsMultiplierPipeline(isMultiplier);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          console.error("Failed to load pipeline details:", err);
          if (mounted) setIsMultiplierPipeline(false);
        }
      }
    };

    fetchPipelineDetails();

    return () => {
      mounted = false;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPipeline]);

  useEffect(() => {
    const revalidate = async () => {
      if (file && selectedPipeline) {
        try {
          const text = await file.text();
          const data = JSON.parse(text);
          const seeds = Array.isArray(data) ? data : [data];
          await validateSeeds(seeds);
        } catch {
          setValidationResult(null);
        }
      } else {
        setValidationResult(null);
      }
    };
    revalidate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPipeline, file]);

  // update generating state based on job status
  useEffect(() => {
    if (currentJob) {
      setGenerating(currentJob.status === "running");
    } else {
      setGenerating(false);
    }
  }, [currentJob]);

  const fetchPipelines = async () => {
    try {
      const res = await fetch("/api/pipelines");
      const data = await res.json();
      setPipelines(data);
    } catch {
      // silent fail - will show empty pipeline list
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      const isJson = droppedFile.type === "application/json" || droppedFile.name.endsWith(".json");
      const isMarkdown = droppedFile.name.endsWith(".md");

      const isValidFile = isMultiplierPipeline ? isMarkdown : isJson;

      if (isValidFile) {
        const input = fileInputRef.current;
        if (input) {
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(droppedFile);
          input.files = dataTransfer.files;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
      } else {
        const expected = isMultiplierPipeline ? "Markdown (.md) file" : "JSON (.json) file";
        toast.error(`Please drop a ${expected}`);
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;

    const selectedFile = e.target.files[0];
    const isMarkdown = selectedFile.name.endsWith(".md");
    const isJson = selectedFile.name.endsWith(".json");

    if (isMultiplierPipeline && isJson) {
      toast.error("Please upload a Markdown (.md) file for this pipeline.");
      return;
    }

    if (!isMultiplierPipeline && isMarkdown) {
      toast.error("Please upload a JSON (.json) file for this pipeline.");
      return;
    }

    if (isMarkdown) {
      const text = await selectedFile.text();
      if (!text.trim()) {
        toast.error("Empty file: The markdown file is empty.");
        return;
      }

      setFile(selectedFile);
      setValidationResult(null);
      return;
    }

    try {
      const text = await selectedFile.text();
      const data = JSON.parse(text);

      const seeds = Array.isArray(data) ? data : [data];
      if (seeds.length === 0) {
        toast.error(
          "Empty file: The file contains no seeds. Please add at least one seed with metadata."
        );
        return;
      }

      for (let i = 0; i < seeds.length; i++) {
        if (!seeds[i].metadata) {
          toast.error(`Invalid seed: Seed ${i + 1} is missing the required 'metadata' field.`);
          return;
        }
      }

      setFile(selectedFile);
    } catch (e) {
      toast.error(
        e instanceof Error
          ? `Invalid JSON: ${e.message}`
          : "The file is not valid JSON. Please check your file syntax."
      );
      setValidationResult(null);
    }
  };

  const handleGenerate = async () => {
    if (!file || !selectedPipeline) return;

    if (generating) {
      toast.error(
        "Job already running: A generation job is already in progress. Cancel it first or wait for completion."
      );
      return;
    }

    setGenerating(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("pipeline_id", selectedPipeline.toString());

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const error = await res.json();
        toast.error(
          `Generation failed: ${error.detail || error.message || "Unknown error occurred."}`
        );
        setGenerating(false);
        return;
      }

      const { job_id } = await res.json();

      // fetch initial job status
      const jobRes = await fetch(`/api/jobs/${job_id}`);
      const job = await jobRes.json();
      setCurrentJob(job);

      // the useEffect will handle setting generating state based on job status
    } catch (error) {
      const message = error instanceof Error ? error.message : "Network error occurred";
      toast.error(`Generation failed: ${message}`);
      setGenerating(false);
    }
  };

  const handleCancel = async () => {
    if (!currentJob) return;

    try {
      await fetch(`/api/jobs/${currentJob.id}`, { method: "DELETE" });
      setCurrentJob(null);
      setGenerating(false);
      toast.success("Job cancelled successfully");
    } catch (error) {
      toast.error(`Failed to cancel: ${error}`);
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Heading sx={{ mb: 2, color: "fg.default" }}>Generate Records</Heading>
        <Text sx={{ color: "fg.default" }}>
          Upload a JSON seed file with input data. Each seed will be executed through your pipeline
          multiple times based on repetitions.
        </Text>
      </Box>

      {/* Job Progress Section */}
      {currentJob && (
        <Box
          sx={{
            p: 4,
            borderRadius: 2,
            bg: currentJob.status === "running" ? "accent.subtle" : "canvas.subtle",
            border: "2px solid",
            borderColor: currentJob.status === "running" ? "accent.emphasis" : "border.default",
            mb: 4,
          }}
        >
          <Box
            sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}
          >
            <Heading sx={{ fontSize: 2, color: "fg.default" }}>Job Progress</Heading>
            <Label variant={getStatusColor(currentJob.status)}>{currentJob.status}</Label>
          </Box>

          <ProgressBar
            barSize="large"
            progress={currentJob.status === "running" ? currentJob.progress * 100 : 100}
            sx={{ mb: 3 }}
          />

          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 3, mb: 3 }}>
            <Box sx={{ textAlign: "center" }}>
              <Text sx={{ fontSize: 3, fontWeight: "bold", color: "fg.default", display: "block" }}>
                {currentJob.current_seed} / {currentJob.total_seeds}
              </Text>
              <Text sx={{ fontSize: 1, color: "fg.muted" }}>Seed in Processing</Text>
            </Box>
            <Box sx={{ textAlign: "center" }}>
              <Text sx={{ fontSize: 3, fontWeight: "bold", color: "success.fg", display: "block" }}>
                {currentJob.records_generated}
              </Text>
              <Text sx={{ fontSize: 1, color: "fg.muted" }}>Generated</Text>
            </Box>
            <Box sx={{ textAlign: "center" }}>
              <Text sx={{ fontSize: 3, fontWeight: "bold", color: "danger.fg", display: "block" }}>
                {currentJob.records_failed}
              </Text>
              <Text sx={{ fontSize: 1, color: "fg.muted" }}>Failed</Text>
            </Box>
          </Box>

          {currentJob.status === "running" &&
            (currentJob.current_block || currentJob.current_step) && (
              <Box
                sx={{
                  p: 2,
                  bg: "accent.muted",
                  borderRadius: 1,
                  mb: 2,
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                }}
              >
                <Spinner size="small" />
                <Text sx={{ fontSize: 1, color: "fg.default" }}>
                  {currentJob.current_block || "Processing..."}
                  {currentJob.current_step && ` • ${currentJob.current_step}`}
                </Text>
              </Box>
            )}

          {currentJob.status === "running" && currentJob.started_at && (
            <Text sx={{ fontSize: 1, color: "fg.muted", mb: 2, display: "block" }}>
              Running for {getElapsedTime(currentJob.started_at)}
            </Text>
          )}

          {currentJob.error && (
            <Flash variant="danger" sx={{ mb: 2 }}>
              {currentJob.error}
            </Flash>
          )}

          <Box sx={{ display: "flex", gap: 2 }}>
            {currentJob.status === "running" && (
              <Button variant="danger" onClick={handleCancel} leadingVisual={XIcon}>
                Cancel Job
              </Button>
            )}
          </Box>
        </Box>
      )}

      <Box sx={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 4 }}>
        {/* Upload Section */}
        <Box>
          <Box
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => !generating && fileInputRef.current?.click()}
            sx={{
              border: "2px dashed",
              borderColor: dragActive ? "accent.emphasis" : "border.default",
              borderRadius: 2,
              p: 6,
              textAlign: "center",
              cursor: generating ? "not-allowed" : "pointer",
              bg: dragActive ? "accent.subtle" : "canvas.subtle",
              transition: "all 0.2s",
              opacity: generating ? 0.5 : 1,
              "&:hover": {
                borderColor: generating ? "border.default" : "accent.fg",
                bg: generating ? "canvas.subtle" : "accent.subtle",
              },
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={isMultiplierPipeline ? ".md" : ".json"}
              onChange={handleFileChange}
              style={{ display: "none" }}
            />

            <Box sx={{ display: "flex", justifyContent: "center", color: "fg.muted" }}>
              <UploadIcon size={48} />
            </Box>
            <Heading as="h3" sx={{ fontSize: 2, mt: 3, mb: 2, color: "fg.default" }}>
              {file
                ? file.name
                : isMultiplierPipeline
                  ? "Drop Markdown file here or click to browse"
                  : "Drop JSON seed file here or click to browse"}
            </Heading>
            <Text sx={{ color: "fg.default", fontSize: 1 }}>
              {file
                ? `Size: ${(file.size / 1024).toFixed(2)} KB`
                : isMultiplierPipeline
                  ? "Markdown (.md) format"
                  : 'Format: {"repetitions": N, "metadata": {...}}'}
            </Text>

            {file && (
              <Button
                variant="invisible"
                leadingVisual={XIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                sx={{ mt: 2 }}
                disabled={generating}
              >
                Remove file
              </Button>
            )}
          </Box>

          {/* Validation Results */}
          {file && selectedPipeline && (
            <Box sx={{ mt: 3 }}>
              {isValidating && (
                <Box
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    bg: "canvas.subtle",
                    border: "1px solid",
                    borderColor: "border.default",
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                  }}
                >
                  <Spinner size="small" />
                  <Text sx={{ color: "fg.default" }}>Validating seeds...</Text>
                </Box>
              )}

              {!isValidating && validationResult && !validationResult.valid && (
                <Box
                  sx={{
                    p: 3,
                    borderRadius: 2,
                    bg: "danger.subtle",
                    border: "1px solid",
                    borderColor: "danger.emphasis",
                  }}
                >
                  {validationResult.errors.map((error, i) => (
                    <Text key={i} sx={{ fontSize: 1, color: "danger.fg", display: "block", mb: 1 }}>
                      • {error}
                    </Text>
                  ))}
                </Box>
              )}
            </Box>
          )}
        </Box>

        {/* Configuration Panel */}
        <Box
          sx={{
            border: "1px solid",
            borderColor: "border.default",
            borderRadius: 2,
            p: 3,
            bg: "canvas.subtle",
          }}
        >
          <Heading as="h3" sx={{ fontSize: 2, mb: 3, color: "fg.default" }}>
            Configuration
          </Heading>

          <FormControl sx={{ mb: 4 }} required disabled={generating}>
            <FormControl.Label>Pipeline</FormControl.Label>
            <Select
              value={selectedPipeline?.toString() || ""}
              onChange={(e) => setSelectedPipeline(Number(e.target.value) || null)}
            >
              <Select.Option value="">Select a pipeline...</Select.Option>
              {pipelines.map((pipeline) => (
                <Select.Option key={pipeline.id} value={pipeline.id.toString()}>
                  {pipeline.name} ({pipeline.definition.blocks.length} blocks)
                </Select.Option>
              ))}
            </Select>
            <FormControl.Caption>Select pipeline to execute for each seed</FormControl.Caption>
          </FormControl>

          <Button
            variant="primary"
            size="large"
            block
            leadingVisual={generating ? undefined : PlayIcon}
            onClick={handleGenerate}
            disabled={
              !file ||
              !selectedPipeline ||
              generating ||
              isValidating ||
              (validationResult !== null && !validationResult.valid)
            }
          >
            {generating ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Spinner size="small" />
                <span>Generating...</span>
              </Box>
            ) : (
              "Generate Records"
            )}
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
