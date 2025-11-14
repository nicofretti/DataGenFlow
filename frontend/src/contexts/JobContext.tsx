import { createContext, useContext, useState, useEffect, useRef, ReactNode } from "react";
import type { Job } from "../types";

interface JobContextType {
  currentJob: Job | null;
  setCurrentJob: (job: Job | null) => void;
  refreshJob: () => Promise<void>;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

export function JobProvider({ children }: { children: ReactNode }) {
  const [currentJob, setCurrentJob] = useState<Job | null>(null);

  // currentJobRef: allows polling logic to access latest job state without causing effect re-runs.
  // this prevents the polling interval from restarting every time job state updates (e.g., progress changes)
  const currentJobRef = useRef<Job | null>(null);

  // pollingJobIdRef: tracks which job ID is currently being polled to prevent duplicate polling.
  // when a job completes and a new one starts, this ensures we don't poll the same job twice
  const pollingJobIdRef = useRef<number | null>(null);

  // keep ref in sync with state
  useEffect(() => {
    currentJobRef.current = currentJob;
  }, [currentJob]);

  // poll for active job every 2 seconds
  //
  // dependency array uses [currentJob?.id, currentJob?.status] instead of [currentJob]:
  // - using [currentJob] would restart polling on EVERY state update (progress, step, etc.) → excessive requests
  // - using [] would never restart polling after first job completes → UI stuck on "Processing..."
  // - using [id, status] restarts only when job changes or transitions between states → correct behavior
  useEffect(() => {
    // determine if we should poll
    // polling starts when:
    // 1. no job exists (null) - to detect when new jobs are created
    // 2. new running job appears with different ID - to track new job progress
    const currentJobState = currentJobRef.current;
    const shouldPoll =
      !currentJobState || // no job - poll to detect new ones
      (currentJobState.status === "running" && pollingJobIdRef.current !== currentJobState.id); // new running job

    if (!shouldPoll) {
      // don't poll if job is completed/failed/cancelled and we're already tracking it
      return;
    }

    // mark this job as being polled to prevent duplicate intervals
    if (currentJobState) {
      pollingJobIdRef.current = currentJobState.id;
    }

    let isStopped = false;

    const pollActiveJob = async () => {
      if (isStopped) return true;

      try {
        const res = await fetch("/api/jobs/active");
        if (res.ok) {
          const job = await res.json();
          setCurrentJob(job);

          // stop polling if job is not running (completed/failed/cancelled)
          if (job.status !== "running") {
            // CRITICAL: clear pollingJobIdRef so new jobs can be polled
            // without this, a new job with different ID would never start polling
            pollingJobIdRef.current = null;
            isStopped = true;
            return true; // signal to stop polling
          }
        } else {
          // no active job exists on server
          const jobInState = currentJobRef.current;
          if (jobInState && jobInState.status === "running") {
            // edge case: job was running but /api/jobs/active now returns 404
            // this happens when job just finished - fetch final status directly
            try {
              const finalRes = await fetch(`/api/jobs/${jobInState.id}`);
              if (finalRes.ok) {
                const finalJob = await finalRes.json();
                setCurrentJob(finalJob);
              }
            } catch {
              // keep existing state if final fetch fails
            }
          }
          // CRITICAL: always stop polling when there's no active job
          // without this, polling would continue infinitely even after job fails/completes
          // clear pollingJobIdRef so that when a new job starts, polling can resume
          pollingJobIdRef.current = null;
          isStopped = true;
          return true;
        }
      } catch {
        // silent fail - polling will retry
      }
      return false;
    };

    // initial check
    pollActiveJob();

    // setup interval
    const interval = setInterval(async () => {
      const shouldStop = await pollActiveJob();
      if (shouldStop) {
        clearInterval(interval);
      }
    }, 2000);

    return () => {
      isStopped = true;
      clearInterval(interval);
    };
  }, [currentJob?.id, currentJob?.status]); // eslint-disable-line react-hooks/exhaustive-deps
  // Intentionally not including full currentJob to avoid re-running on every state update

  // refresh job status manually
  const refreshJob = async () => {
    if (!currentJob) return;

    try {
      const res = await fetch(`/api/jobs/${currentJob.id}`);
      if (res.ok) {
        const job = await res.json();
        setCurrentJob(job);
      }
    } catch {
      // silent fail - refresh is optional
    }
  };

  return (
    <JobContext.Provider value={{ currentJob, setCurrentJob, refreshJob }}>
      {children}
    </JobContext.Provider>
  );
}

export function useJob() {
  const context = useContext(JobContext);
  if (context === undefined) {
    throw new Error("useJob must be used within a JobProvider");
  }
  return context;
}
