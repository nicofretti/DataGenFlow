import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Heading,
  Button,
  Label,
  Text,
  Textarea,
  SegmentedControl,
  CounterLabel,
  Flash,
  FormControl,
  Select,
} from "@primer/react";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CommentIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  TrashIcon,
  DownloadIcon,
  GearIcon,
} from "@primer/octicons-react";
import ConfigureFieldsModal from "../components/ConfigureFieldsModal";
import SingleRecordView from "../components/SingleRecordView";
import TableRecordView from "../components/TableRecordView";
import RecordDetailsModal from "../components/RecordDetailsModal";

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
  error?: string;
}

interface Pipeline {
  id: number;
  name: string;
  definition: {
    name: string;
    blocks: any[];
  };
  validation_config?: {
    field_order: {
      primary: string[];
      secondary: string[];
      hidden: string[];
    };
  } | null;
}

interface Job {
  id: number;
  pipeline_id: number;
  status: string;
  records_generated: number;
  records_failed: number;
  started_at: string;
}

export default function Review() {
  const [records, setRecords] = useState<Record[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);
  const [filterStatus, setFilterStatus] = useState<"pending" | "accepted" | "rejected">("pending");
  const [stats, setStats] = useState({ pending: 0, accepted: 0, rejected: 0 });
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<number | null>(null);
  const [currentPipeline, setCurrentPipeline] = useState<Pipeline | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [viewMode, setViewMode] = useState<"single" | "table">("single");
  const [currentPage, setCurrentPage] = useState(1);
  const [recordsPerPage, setRecordsPerPage] = useState(10);
  const [selectedRecordForDetails, setSelectedRecordForDetails] = useState<Record | null>(null);

  const currentRecord = records[currentIndex] || null;

  const loadPipelines = useCallback(async () => {
    try {
      const res = await fetch("/api/pipelines");
      const data = await res.json();
      setPipelines(data);
    } catch {
      // silent fail - pipelines filter is optional
    }
  }, []);

  const loadCurrentPipeline = useCallback(async (pipelineId: number) => {
    try {
      const res = await fetch(`/api/pipelines/${pipelineId}`);
      const data = await res.json();
      setCurrentPipeline(data);

      // show config modal if validation_config is null
      if (!data.validation_config) {
        setShowConfigModal(true);
      }
    } catch {
      // silent fail - pipeline is optional
    }
  }, []);

  const loadJobs = useCallback(async (pipelineId: number) => {
    try {
      const res = await fetch(`/api/jobs?pipeline_id=${pipelineId}`);
      const data = await res.json();
      // only show jobs that have generated records
      const jobsWithRecords = data.filter((job: Job) => job.records_generated > 0);
      setJobs(jobsWithRecords);
    } catch {
      // silent fail - jobs filter is optional
    }
  }, []);

  const loadRecords = useCallback(async () => {
    // don't load records if no pipeline selected
    if (!selectedPipeline) {
      setRecords([]);
      return;
    }

    let url = `/api/records?status=${filterStatus}&limit=100`;
    if (selectedJob) {
      url += `&job_id=${selectedJob}`;
    }
    const res = await fetch(url);
    const data = await res.json();
    setRecords(data);
  }, [filterStatus, selectedJob, selectedPipeline]);

  const loadStats = useCallback(async () => {
    // don't load stats if no pipeline selected
    if (!selectedPipeline) {
      setStats({ pending: 0, accepted: 0, rejected: 0 });
      return;
    }

    // fetch records to get accurate counts, filtered by job if selected
    const jobParam = selectedJob ? `&job_id=${selectedJob}` : "";
    const [pending, accepted, rejected] = await Promise.all([
      fetch(`/api/records?status=pending${jobParam}`).then((r) => r.json()),
      fetch(`/api/records?status=accepted${jobParam}`).then((r) => r.json()),
      fetch(`/api/records?status=rejected${jobParam}`).then((r) => r.json()),
    ]);
    setStats({
      pending: pending.length,
      accepted: accepted.length,
      rejected: rejected.length,
    });
  }, [selectedJob, selectedPipeline]);

  const updateStatus = useCallback(
    async (id: number, status: string) => {
      await fetch(`/api/records/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      // reload records and stats after update
      await loadRecords();
      await loadStats();
    },
    [loadRecords, loadStats]
  );

  // get final output from record
  const getFinalOutput = (record: Record): string => {
    return record.output || "";
  };

  const startEditing = useCallback(() => {
    if (!currentRecord) return;
    setIsEditing(true);
    setEditValue(getFinalOutput(currentRecord));
    setIsExpanded(true); // expand when editing
  }, [currentRecord]);

  const saveEdit = async () => {
    if (!currentRecord) return;
    await fetch(`/api/records/${currentRecord.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ output: editValue, status: "edited" }),
    });
    setIsEditing(false);
    loadRecords();
    loadStats();
  };

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

  // reset index when changing filter
  useEffect(() => {
    setCurrentIndex(0);
    setIsEditing(false);
    setIsExpanded(false);
  }, [filterStatus]);

  // keep currentIndex in valid range when records change
  useEffect(() => {
    if (records.length === 0) {
      setCurrentIndex(0);
    } else if (currentIndex >= records.length) {
      setCurrentIndex(records.length - 1);
    }
  }, [records.length, currentIndex]);

  // reset page when changing filters
  useEffect(() => {
    setCurrentPage(1);
  }, [filterStatus, selectedJob]);

  // keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (isEditing) return; // disable shortcuts while editing

      if (e.key === "a" && currentRecord) {
        updateStatus(currentRecord.id, "accepted");
      } else if (e.key === "r" && currentRecord) {
        updateStatus(currentRecord.id, "rejected");
      } else if (e.key === "u" && currentRecord) {
        updateStatus(currentRecord.id, "pending");
      } else if (e.key === "e" && currentRecord) {
        startEditing();
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
  }, [currentRecord, currentIndex, records.length, isEditing, updateStatus, startEditing]);

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
      const url = selectedJob ? `/api/records?job_id=${selectedJob}` : `/api/records`;
      await fetch(url, { method: "DELETE" });
      setMessage({ type: "success", text: "Records deleted successfully" });

      if (selectedJob && selectedPipeline) {
        setSelectedJob(null);
        await loadJobs(selectedPipeline);
      }

      loadRecords();
      loadStats();
    } catch (error) {
      setMessage({ type: "error", text: `Error: ${error}` });
    }
  };

  const exportAccepted = () => {
    const url = selectedJob
      ? `/api/export/download?status=accepted&job_id=${selectedJob}`
      : `/api/export/download?status=accepted`;
    window.location.href = url;
  };

  // pagination helpers
  const getCurrentPageRecords = () => {
    const start = (currentPage - 1) * recordsPerPage;
    const end = start + recordsPerPage;
    return records.slice(start, end);
  };

  // bulk operations
  const handleBulkAccept = async () => {
    const visibleRecords = getCurrentPageRecords();
    await Promise.all(
      visibleRecords.map((r) => updateStatus(r.id, "accepted"))
    );
  };

  const handleBulkReject = async () => {
    const visibleRecords = getCurrentPageRecords();
    await Promise.all(
      visibleRecords.map((r) => updateStatus(r.id, "rejected"))
    );
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "pending":
        return "attention";
      case "accepted":
        return "success";
      case "rejected":
        return "danger";
      case "edited":
        return "accent";
      default:
        return "default";
    }
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
              <Button
                variant={viewMode === "single" ? "primary" : "default"}
                onClick={() => setViewMode("single")}
              >
                Single View
              </Button>
              <Button
                variant={viewMode === "table" ? "primary" : "default"}
                onClick={() => setViewMode("table")}
              >
                Table View
              </Button>
              <Button
                leadingVisual={GearIcon}
                onClick={() => setShowConfigModal(true)}
                disabled={!currentPipeline}
              >
                Configure Layout
              </Button>
            </>
          )}
          <Button
            variant="primary"
            leadingVisual={DownloadIcon}
            onClick={exportAccepted}
            disabled={stats.accepted === 0}
          >
            Export Accepted
          </Button>
          <Button
            variant="danger"
            leadingVisual={TrashIcon}
            onClick={deleteAllRecords}
            disabled={records.length === 0}
          >
            Delete {selectedJob ? "Job" : "All"}
          </Button>
        </Box>
      </Box>

      {message && (
        <Flash variant={message.type === "error" ? "danger" : "success"} sx={{ mb: 3 }}>
          {message.text}
        </Flash>
      )}

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

      {/* keyboard shortcuts hint */}
      <Box sx={{ mb: 3, display: "flex", gap: 3, fontSize: 1, alignItems: "center" }}>
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
            A
          </Box>
          <Text sx={{ color: "fg.default" }}>Accept</Text>
        </Box>
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
            R
          </Box>
          <Text sx={{ color: "fg.default" }}>Reject</Text>
        </Box>
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
            U
          </Box>
          <Text sx={{ color: "fg.default" }}>Set Pending</Text>
        </Box>
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
            E
          </Box>
          <Text sx={{ color: "fg.default" }}>Edit</Text>
        </Box>
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
            N
          </Box>
          <Text sx={{ color: "fg.default" }}>Next</Text>
        </Box>
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
            P
          </Box>
          <Text sx={{ color: "fg.default" }}>Previous</Text>
        </Box>
      </Box>

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
          onBulkAccept={handleBulkAccept}
          onBulkReject={handleBulkReject}
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
            await fetch(`/api/records/${currentRecord.id}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(updates),
            });
            loadRecords();
            loadStats();
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
            setMessage({ type: "success", text: "Field layout saved successfully" });
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
            await fetch(`/api/records/${selectedRecordForDetails.id}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(updates),
            });
            await loadRecords();
            await loadStats();
            setSelectedRecordForDetails(null);
          }}
        />
      )}
    </Box>
  );
}
