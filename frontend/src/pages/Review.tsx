import { useEffect, useState, useCallback, useRef } from "react";
import {
  Box,
  Heading,
  Button,
  Text,
  SegmentedControl,
  CounterLabel,
  FormControl,
  Select,
  ActionMenu,
  ActionList,
} from "@primer/react";
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  TrashIcon,
  DownloadIcon,
  GearIcon,
  KebabHorizontalIcon,
} from "@primer/octicons-react";
import ConfigureFieldsModal from "../components/ConfigureFieldsModal";
import SingleRecordView from "../components/SingleRecordView";
import TableRecordView from "../components/TableRecordView";
import RecordDetailsModal from "../components/RecordDetailsModal";
import KeyboardShortcut from "../components/KeyboardShortcut";
import { useJob } from "../contexts/JobContext";
import type { RecordData, Pipeline, Job } from "../types";
import { toast } from "sonner";
import { usePersistedState } from "../hooks/usePersistedState";
import { recordsApi } from "../services/recordsApi";

const POLL_INTERVAL_MS = 2000;

export default function Review() {
  const { currentJob } = useJob();
  const [records, setRecords] = useState<RecordData[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [filterStatus, setFilterStatus] = useState<"pending" | "accepted" | "rejected">("pending");
  const [stats, setStats] = useState({ pending: 0, accepted: 0, rejected: 0 });
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null);
  const [currentPipeline, setCurrentPipeline] = useState<Pipeline | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [viewMode, setViewMode] = usePersistedState<"single" | "table">(
    "review_view_mode",
    "table"
  );
  const [currentPage, setCurrentPage] = useState(1);
  const [recordsPerPage, setRecordsPerPage] = useState(10);
  const [selectedRecordForDetails, setSelectedRecordForDetails] = useState<RecordData | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_isExpanded, setIsExpanded] = useState(false);
  const startEditingRef = useRef<(() => void) | null>(null);
  const currentRecordIdRef = useRef<number | null>(null);

  const currentRecord = records[currentIndex] || null;

  useEffect(() => {
    if (currentRecord && viewMode === "single") {
      currentRecordIdRef.current = currentRecord.id;
    }
  }, [currentRecord, viewMode]);

  const loadPipelines = useCallback(async () => {
    try {
      const res = await fetch("/api/pipelines");
      if (!res.ok) {
        throw new Error(`http ${res.status}`);
      }
      const data = await res.json();
      setPipelines(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load pipelines:", err);
      toast.error(`Failed to load pipelines: ${message}`);
    }
  }, []);

  const loadCurrentPipeline = useCallback(async (pipelineId: number) => {
    try {
      const res = await fetch(`/api/pipelines/${pipelineId}`);
      if (!res.ok) {
        throw new Error(`http ${res.status}`);
      }
      const data = await res.json();
      setCurrentPipeline(data);
      if (!data.validation_config) {
        setShowConfigModal(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load pipeline details:", err);
      toast.error(`Failed to load pipeline details: ${message}`);
    }
  }, []);

  const loadJobs = useCallback(async (pipelineId: number) => {
    try {
      const res = await fetch(`/api/jobs?pipeline_id=${pipelineId}`);
      if (!res.ok) {
        throw new Error(`http ${res.status}`);
      }
      const data = await res.json();
      const jobsWithRecords = data.filter((job: Job) => job.records_generated > 0);
      setJobs(jobsWithRecords);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load jobs:", err);
      toast.error(`Failed to load jobs: ${message}`);
    }
  }, []);

  const loadRecords = useCallback(async () => {
    if (!selectedPipeline) {
      setRecords([]);
      return;
    }

    try {
      const data = await recordsApi.getRecords({
        status: filterStatus,
        limit: 100,
        pipelineId: selectedPipeline,
        jobId: selectedJob || undefined,
      });
      setRecords(data);

      if (viewMode === "single" && currentRecordIdRef.current !== null) {
        const newIndex = data.findIndex((r: RecordData) => r.id === currentRecordIdRef.current);
        if (newIndex !== -1) {
          setCurrentIndex(newIndex);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load records:", err);
      toast.error(`Failed to load records: ${message}`);
    }
  }, [filterStatus, selectedJob, selectedPipeline, viewMode]);

  const loadStats = useCallback(async () => {
    if (!selectedPipeline) {
      setStats({ pending: 0, accepted: 0, rejected: 0 });
      return;
    }

    try {
      const [pending, accepted, rejected] = await Promise.all([
        recordsApi.getRecordsByStatus("pending", selectedPipeline, selectedJob || undefined),
        recordsApi.getRecordsByStatus("accepted", selectedPipeline, selectedJob || undefined),
        recordsApi.getRecordsByStatus("rejected", selectedPipeline, selectedJob || undefined),
      ]);
      setStats({
        pending: pending.length,
        accepted: accepted.length,
        rejected: rejected.length,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to load stats:", err);
      toast.error(`Failed to load stats: ${message}`);
    }
  }, [selectedJob, selectedPipeline]);

  const updateStatus = useCallback(
    async (id: number, status: string) => {
      try {
        await recordsApi.updateRecord(id, { status });
        await loadRecords();
        await loadStats();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        console.error("failed to update record status:", err);
        toast.error(`Failed to update record: ${message}`);
      }
    },
    [loadRecords, loadStats]
  );

  useEffect(() => {
    loadPipelines();
  }, [loadPipelines]);

  useEffect(() => {
    loadRecords();
    loadStats();
  }, [filterStatus, selectedJob, loadRecords, loadStats]);

  useEffect(() => {
    if (selectedPipeline) {
      loadCurrentPipeline(selectedPipeline);
      loadJobs(selectedPipeline);
    } else {
      setCurrentPipeline(null);
      setJobs([]);
      setSelectedJob(null);
    }
  }, [selectedPipeline, loadCurrentPipeline, loadJobs]);

  useEffect(() => {
    setCurrentIndex(0);
    setIsExpanded(false);
  }, [filterStatus]);

  useEffect(() => {
    if (records.length === 0) {
      setCurrentIndex(0);
    } else if (currentIndex >= records.length) {
      setCurrentIndex(records.length - 1);
    }
  }, [records.length, currentIndex]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filterStatus, selectedJob]);

  useEffect(() => {
    if (currentJob && currentJob.status === "running" && !selectedPipeline) {
      setSelectedPipeline(currentJob.pipeline_id);
    }
  }, [currentJob, selectedPipeline]);

  useEffect(() => {
    if (
      currentJob &&
      currentJob.status === "running" &&
      selectedPipeline === currentJob.pipeline_id &&
      selectedJob === null
    ) {
      setSelectedJob(currentJob.id);
    }
  }, [currentJob, selectedPipeline, selectedJob]);

  useEffect(() => {
    if (!currentJob || currentJob.status !== "running" || !selectedPipeline) {
      return;
    }

    if (currentJob.pipeline_id !== selectedPipeline) {
      return;
    }

    let mounted = true;
    const controller = new AbortController();

    const poll = () => {
      if (mounted && !controller.signal.aborted) {
        loadRecords();
        loadStats();
      }
    };

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      mounted = false;
      controller.abort();
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentJob, selectedPipeline]);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }

      if (e.key === "a" && currentRecord) {
        updateStatus(currentRecord.id, "accepted");
      } else if (e.key === "r" && currentRecord) {
        updateStatus(currentRecord.id, "rejected");
      } else if (e.key === "u" && currentRecord) {
        updateStatus(currentRecord.id, "pending");
      } else if (e.key === "e" && currentRecord && viewMode === "single") {
        startEditingRef.current?.();
      } else if (e.key === "n" && currentIndex < records.length - 1) {
        setCurrentIndex(currentIndex + 1);
        setIsExpanded(false);
      } else if (e.key === "p" && currentIndex > 0) {
        setCurrentIndex(currentIndex - 1);
        setIsExpanded(false);
      }
    };

    window.addEventListener("keydown", handleKeyPress);
    return () => window.removeEventListener("keydown", handleKeyPress);
  }, [currentRecord, currentIndex, records.length, updateStatus, viewMode]);

  const goToNext = () => {
    if (currentIndex < records.length - 1) {
      setCurrentIndex(currentIndex + 1);
      setIsExpanded(false);
    }
  };

  const goToPrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setIsExpanded(false);
    }
  };

  const deleteAllRecords = async () => {
    const confirmMessage = selectedJob
      ? `Delete all records for this job? This cannot be undone.`
      : `Delete all ${filterStatus} records? This cannot be undone.`;

    if (!confirm(confirmMessage)) return;

    try {
      await recordsApi.deleteAllRecords(selectedJob || undefined);
      toast.success("All records deleted successfully");
      if (selectedJob && selectedPipeline) {
        setSelectedJob(null);
        await loadJobs(selectedPipeline);
      }
      loadRecords();
      loadStats();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      console.error("failed to delete records:", err);
      toast.error(`Failed to delete records: ${message}`);
    }
  };

  const exportAll = () => {
    const url = selectedJob ? `/api/export/download?job_id=${selectedJob}` : `/api/export/download`;
    window.location.href = url;
  };

  const getCurrentPageRecords = () => {
    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    return records.slice(start, end);
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Box>
          <Heading sx={{ mb: 2, color: "fg.default" }}>Review Records</Heading>
          <Text sx={{ color: "fg.default" }}>
            Review and validate generated Q&A pairs • Use keyboard shortcuts
          </Text>
        </Box>

        <Box sx={{ display: "flex", gap: 2 }}>
          {selectedPipeline && (
            <>
              <Button onClick={() => setViewMode(viewMode === "single" ? "table" : "single")}>
                {viewMode === "single" ? "Table View" : "Single View"}
              </Button>
              <ActionMenu>
                <ActionMenu.Anchor>
                  <Button leadingVisual={KebabHorizontalIcon} aria-label="More options" />
                </ActionMenu.Anchor>
                <ActionMenu.Overlay>
                  <ActionList>
                    <ActionList.Item onSelect={() => setShowConfigModal(true)}>
                      <ActionList.LeadingVisual>
                        <GearIcon />
                      </ActionList.LeadingVisual>
                      Configure Layout
                    </ActionList.Item>
                    <ActionList.Item onSelect={exportAll}>
                      <ActionList.LeadingVisual>
                        <DownloadIcon />
                      </ActionList.LeadingVisual>
                      Export All
                    </ActionList.Item>
                    <ActionList.Divider />
                    <ActionList.Item variant="danger" onSelect={deleteAllRecords}>
                      <ActionList.LeadingVisual>
                        <TrashIcon />
                      </ActionList.LeadingVisual>
                      Delete All Records
                    </ActionList.Item>
                  </ActionList>
                </ActionMenu.Overlay>
              </ActionMenu>
            </>
          )}
        </Box>
      </Box>

      {/* Filter by Pipeline and Job */}
      <Box sx={{ mb: 3, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 3 }}>
        <FormControl>
          <FormControl.Label>Filter by Pipeline</FormControl.Label>
          <Select
            value={selectedPipeline?.toString() || ""}
            onChange={(e) => {
              const value = e.target.value;
              setSelectedPipeline(value ? Number(value) : null);
              setSelectedJob(null);
            }}
          >
            <Select.Option value="">All Pipelines</Select.Option>
            {pipelines.map((pipeline) => (
              <Select.Option key={pipeline.id} value={pipeline.id.toString()}>
                {pipeline.definition.name}
              </Select.Option>
            ))}
          </Select>
          <FormControl.Caption>Filter records by pipeline</FormControl.Caption>
        </FormControl>

        <FormControl>
          <FormControl.Label>Filter by Job (Optional)</FormControl.Label>
          <Select
            value={selectedJob?.toString() || ""}
            onChange={(e) => {
              const value = e.target.value;
              setSelectedJob(value ? Number(value) : null);
            }}
            disabled={!selectedPipeline || jobs.length === 0}
          >
            <Select.Option value="">All Jobs</Select.Option>
            {jobs.map((job) => (
              <Select.Option key={job.id} value={job.id.toString()}>
                Job #{job.id} - {job.status} - {job.records_generated} records (
                {new Date(job.started_at).toLocaleString()})
              </Select.Option>
            ))}
          </Select>
          <FormControl.Caption>
            {selectedPipeline ? "Optionally filter by a specific job" : "Select a pipeline first"}
          </FormControl.Caption>
        </FormControl>
      </Box>

      <Box sx={{ mb: 3, display: "flex", justifyContent: "center" }}>
        <SegmentedControl
          aria-label="Filter by status"
          onChange={(index) => {
            const statuses = ["pending", "accepted", "rejected"] as const;
            setFilterStatus(statuses[index]);
          }}
        >
          <SegmentedControl.Button {...({} as any)} selected={filterStatus === "pending"}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "fg.default" }}>
              <ClockIcon size={16} />
              <Text>Pending</Text>
              <CounterLabel>{stats.pending}</CounterLabel>
            </Box>
          </SegmentedControl.Button>
          <SegmentedControl.Button {...({} as any)} selected={filterStatus === "accepted"}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "fg.default" }}>
              <CheckCircleIcon size={16} />
              <Text>Accepted</Text>
              <CounterLabel>{stats.accepted}</CounterLabel>
            </Box>
          </SegmentedControl.Button>
          <SegmentedControl.Button {...({} as any)} selected={filterStatus === "rejected"}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "fg.default" }}>
              <XCircleIcon size={16} fill="fg.danger" />
              <Text>Rejected</Text>
              <CounterLabel>{stats.rejected}</CounterLabel>
            </Box>
          </SegmentedControl.Button>
        </SegmentedControl>
      </Box>

      {/* keyboard shortcuts hint - only in single view */}
      {viewMode === "single" && selectedPipeline && records.length > 0 && (
        <Box
          sx={{
            my: 3,
            display: "flex",
            gap: 3,
            fontSize: 1,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <KeyboardShortcut shortcut="A" label="Accept" />
          <KeyboardShortcut shortcut="R" label="Reject" />
          <KeyboardShortcut shortcut="U" label="Set Pending" />
          <KeyboardShortcut shortcut="E" label="Edit" />
          <KeyboardShortcut shortcut="N" label="Next" />
          <KeyboardShortcut shortcut="P" label="Previous" />
        </Box>
      )}

      {!selectedPipeline ? (
        <Box
          sx={{
            textAlign: "center",
            py: 6,
            border: "1px dashed",
            borderColor: "border.default",
            borderRadius: 2,
          }}
        >
          <Text sx={{ color: "fg.muted", fontSize: 2 }}>
            Please select a pipeline to view records
          </Text>
        </Box>
      ) : records.length === 0 ? (
        <Box
          sx={{
            textAlign: "center",
            py: 6,
            border: "1px dashed",
            borderColor: "border.default",
            borderRadius: 2,
          }}
        >
          <Text sx={{ color: "fg.default" }}>No {filterStatus} records found</Text>
        </Box>
      ) : viewMode === "table" ? (
        <TableRecordView
          records={getCurrentPageRecords()}
          validationConfig={currentPipeline?.validation_config || null}
          currentPage={currentPage}
          recordsPerPage={recordsPerPage}
          totalRecords={records.length}
          onAccept={(id) => updateStatus(id, "accepted")}
          onReject={(id) => updateStatus(id, "rejected")}
          onSetPending={(id) => updateStatus(id, "pending")}
          onViewDetails={(record) => setSelectedRecordForDetails(record)}
          onPageChange={setCurrentPage}
          onRecordsPerPageChange={(perPage) => {
            setRecordsPerPage(perPage);
            setCurrentPage(1);
          }}
        />
      ) : currentRecord ? (
        <SingleRecordView
          record={currentRecord}
          validationConfig={currentPipeline?.validation_config || null}
          currentIndex={currentIndex}
          totalRecords={records.length}
          onNext={goToNext}
          onPrevious={goToPrevious}
          onAccept={() => updateStatus(currentRecord.id, "accepted")}
          onReject={() => updateStatus(currentRecord.id, "rejected")}
          onSetPending={() => updateStatus(currentRecord.id, "pending")}
          onEdit={async (updates) => {
            try {
              await recordsApi.updateRecord(currentRecord.id, updates);
              await loadRecords();
              await loadStats();
            } catch (err) {
              const message = err instanceof Error ? err.message : "Unknown error";
              console.error("failed to update record:", err);
              toast.error(`Failed to update record: ${message}`);
            }
          }}
          onRegisterStartEditing={(fn) => {
            startEditingRef.current = fn;
          }}
          isPending={filterStatus === "pending"}
        />
      ) : null}

      {/* Configuration Modal */}
      {showConfigModal && selectedPipeline && (
        <ConfigureFieldsModal
          pipelineId={selectedPipeline}
          onClose={() => setShowConfigModal(false)}
          onSave={() => {
            setShowConfigModal(false);
            loadCurrentPipeline(selectedPipeline);
            toast.success("Field configuration saved successfully");
          }}
        />
      )}

      {/* Record Details Modal */}
      {selectedRecordForDetails && (
        <RecordDetailsModal
          record={selectedRecordForDetails}
          validationConfig={currentPipeline?.validation_config || null}
          onClose={() => setSelectedRecordForDetails(null)}
          onAccept={async () => {
            await updateStatus(selectedRecordForDetails.id, "accepted");
            setSelectedRecordForDetails(null);
          }}
          onReject={async () => {
            await updateStatus(selectedRecordForDetails.id, "rejected");
            setSelectedRecordForDetails(null);
          }}
          onSetPending={async () => {
            await updateStatus(selectedRecordForDetails.id, "pending");
            setSelectedRecordForDetails(null);
          }}
          onEdit={async (updates) => {
            try {
              await recordsApi.updateRecord(selectedRecordForDetails.id, updates);
              await loadRecords();
              await loadStats();
              setSelectedRecordForDetails(null);
            } catch (err) {
              const message = err instanceof Error ? err.message : "Unknown error";
              console.error("failed to update record:", err);
              toast.error(`Failed to update record: ${message}`);
            }
          }}
        />
      )}
    </Box>
  );
}
