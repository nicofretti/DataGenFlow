import { createContext, useContext, useState, useEffect, ReactNode } from "react";

interface Job {
  id: number;
  pipeline_id: number;
  status: string;
  progress: number;
  current_seed: number;
  total_seeds: number;
  current_block: string | null;
  current_step: string | null;
  records_generated: number;
  records_failed: number;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

interface JobContextType {
  currentJob: Job | null;
  setCurrentJob: (job: Job | null) => void;
  refreshJob: () => Promise<void>;
}

const JobContext = createContext<JobContextType | undefined>(undefined);

export function JobProvider({ children }: { children: ReactNode }) {
  const [currentJob, setCurrentJob] = useState<Job | null>(null);

  // poll for active job every 2 seconds
  useEffect(() => {
    const pollActiveJob = async () => {
      try {
        const res = await fetch("/api/jobs/active");
        if (res.ok) {
          const job = await res.json();
          setCurrentJob(job);

          // stop polling if job is not running
          if (job.status !== "running") {
            return true; // signal to stop polling
          }
        } else {
          setCurrentJob(null);
        }
      } catch (error) {
        console.error("Failed to poll job:", error);
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

    return () => clearInterval(interval);
  }, []);

  // refresh job status manually
  const refreshJob = async () => {
    if (!currentJob) return;

    try {
      const res = await fetch(`/api/jobs/${currentJob.id}`);
      if (res.ok) {
        const job = await res.json();
        setCurrentJob(job);
      }
    } catch (error) {
      console.error("Failed to refresh job:", error);
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
