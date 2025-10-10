import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
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
import ErrorModal from "../components/ErrorModal";

interface Pipeline {
  id: number;
  name: string;
  definition: {
    name: string;
    blocks: any[];
  };
}

export default function Generator() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { currentJob, setCurrentJob } = useJob();
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null);
  const [errorModal, setErrorModal] = useState<{ title: string; message: string } | null>(null);

  useEffect(() => {
    fetchPipelines();
  }, []);

  // update generating state based on job status
  useEffect(() => {
    if (currentJob) {
      setGenerating(currentJob.status === "running");
    } else {
      setGenerating(false);
    }
  }, [currentJob?.status]);

  const fetchPipelines = async () => {
    try {
      const res = await fetch("/api/pipelines");
      const data = await res.json();
      setPipelines(data);
    } catch (error) {
      console.error("Failed to fetch pipelines:", error);
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
      if (droppedFile.type === "application/json") {
        setFile(droppedFile);
      } else {
        setMessage({ type: "error", text: "Please drop a JSON file" });
      }
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;

    const selectedFile = e.target.files[0];

    // validate JSON
    try {
      const text = await selectedFile.text();
      const data = JSON.parse(text);

      // check not empty
      const seeds = Array.isArray(data) ? data : [data];
      if (seeds.length === 0) {
        setErrorModal({
          title: "Empty File",
          message: "The file contains no seeds. Please add at least one seed with metadata.",
        });
        return;
      }

      // check basic structure
      for (let i = 0; i < seeds.length; i++) {
        if (!seeds[i].metadata) {
          setErrorModal({
            title: "Invalid Seed",
            message: `Seed ${i + 1} is missing the required 'metadata' field.`,
          });
          return;
        }
      }

      // validation passed
      setFile(selectedFile);
      setMessage(null);
    } catch (e) {
      setErrorModal({
        title: "Invalid JSON",
        message:
          e instanceof Error
            ? e.message
            : "The file is not valid JSON. Please check your file syntax.",
      });
    }
  };

  const handleGenerate = async () => {
    if (!file || !selectedPipeline) return;

    if (generating) {
      setErrorModal({
        title: "Job Already Running",
        message: "A generation job is already in progress. Cancel it first or wait for completion.",
      });
      return;
    }

    setGenerating(true);
    setMessage(null);

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
        setErrorModal({
          title: "Generation Failed",
          message: error.detail || "Failed to start generation. Please try again.",
        });
        return;
      }

      const { job_id } = await res.json();

      // fetch initial job status
      const jobRes = await fetch(`/api/jobs/${job_id}`);
      const job = await jobRes.json();
      setCurrentJob(job);
    } catch (error) {
      setErrorModal({
        title: "Network Error",
        message:
          error instanceof Error
            ? error.message
            : "Failed to connect to server. Please check your connection.",
      });
    } finally {
      // always reset generating if there's no active job
      if (!currentJob || currentJob.status !== "running") {
        setGenerating(false);
      }
    }
  };

  const handleCancel = async () => {
    if (!currentJob) return;

    try {
      await fetch(`/api/jobs/${currentJob.id}`, { method: "DELETE" });
      setCurrentJob(null);
      setGenerating(false);
      setMessage({ type: "success", text: "Job cancelled" });
    } catch (error) {
      setMessage({ type: "error", text: `Failed to cancel: ${error}` });
    }
  };

  const getStatusColor = (status: string) => {
    if (status === "completed") return "success";
    if (status === "failed" || status === "cancelled") return "danger";
    return "accent";
  };

  const getElapsedTime = (startTime: string) => {
    const start = new Date(startTime);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000);

    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  return (
    <Box>
      <ErrorModal
        isOpen={errorModal !== null}
        onClose={() => setErrorModal(null)}
        title={errorModal?.title || ""}
        message={errorModal?.message || ""}
      />

      <Box sx={{ mb: 4 }}>
        <Heading sx={{ mb: 2, color: "fg.default" }}>Generate Records</Heading>
        <Text sx={{ color: "fg.default" }}>
          Upload a JSON seed file with input data. Each seed will be executed through your pipeline
          multiple times based on repetitions.
        </Text>
      </Box>

      {message && (
        <Flash variant={message.type === "error" ? "danger" : "success"} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

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
              <Text sx={{ fontSize: 1, color: "fg.muted" }}>Seeds Processed</Text>
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

          {currentJob.status === "running" && currentJob.created_at && (
            <Text sx={{ fontSize: 1, color: "fg.muted", mb: 2, display: "block" }}>
              Running for {getElapsedTime(currentJob.created_at)}
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

            {currentJob.status === "completed" && (
              <Button variant="primary" onClick={() => navigate("/review")}>
                View Results
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
              accept=".json"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />

            <Box sx={{ color: "fg.muted" }}>
              <UploadIcon size={48} />
            </Box>
            <Heading as="h3" sx={{ fontSize: 2, mt: 3, mb: 2, color: "fg.default" }}>
              {file ? file.name : "Drop JSON seed file here or click to browse"}
            </Heading>
            <Text sx={{ color: "fg.default", fontSize: 1 }}>
              {file
                ? `Size: ${(file.size / 1024).toFixed(2)} KB`
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

          <FormControl sx={{ mb: 4 }} required>
            <FormControl.Label>Pipeline</FormControl.Label>
            <Select
              value={selectedPipeline?.toString() || ""}
              onChange={(e) => setSelectedPipeline(Number(e.target.value) || null)}
              disabled={generating}
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
            disabled={!file || !selectedPipeline || generating}
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
