import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useState } from "react";
import { api, type JobStatus } from "../api";
import { fmtWhen } from "../lib/format";

const DAY_MS = 24 * 3600 * 1000;

/** How long after its last start a job counts as overdue: 26 hours for daily jobs (WL-048). */
function overdueAfter(schedule: string): number {
  return /week/i.test(schedule) ? 7 * DAY_MS + 2 * 3600 * 1000 : 26 * 3600 * 1000;
}

type Problem = { job: JobStatus; reason: string };

export function jobProblem(job: JobStatus, now: number = Date.now()): string | null {
  if (job.exit_code !== null && job.exit_code !== undefined && job.exit_code !== 0) {
    return `failed with exit code ${String(job.exit_code)}`;
  }
  if (!job.started_at) return "has never run";
  const started = new Date(job.started_at).getTime();
  if (Number.isNaN(started)) return "has an unreadable start time";
  if (now - started > overdueAfter(job.schedule)) return `is overdue (last start ${fmtWhen(job.started_at) ?? job.started_at})`;
  return null;
}

/** The scheduled jobs' health from GET /api/jobs, in the rail foot. A failing or overdue job shows an error state. */
export default function JobsStatus({ folded }: Readonly<{ folded: boolean }>) {
  const [jobs, setJobs] = useState<JobStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .jobs()
      .then((res) => {
        setJobs(res.jobs);
        setError(null);
      })
      .catch((err: unknown) => setError((err as Error).message));
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, [load]);

  const problems: Problem[] = [];
  for (const job of jobs ?? []) {
    const reason = jobProblem(job);
    if (reason) problems.push({ job, reason });
  }

  let glyph = "○";
  let label = "Jobs: checking…";
  let color = "text.secondary";
  if (error) {
    glyph = "!";
    label = "Jobs: status unavailable";
    color = "warning.main";
  } else if (jobs && problems.length) {
    glyph = "✕";
    label = problems.length === 1 ? `Job ${problems[0].job.job} failing` : `${String(problems.length)} jobs failing`;
    color = "error.main";
  } else if (jobs) {
    glyph = "✓";
    label = jobs.length ? `Jobs ok · ${String(jobs.length)}` : "No jobs recorded";
  }

  const tooltip = (
    <Box sx={{ py: 0.5 }}>
      {error ? <Typography variant="caption" component="div">GET /api/jobs failed: {error}</Typography> : null}
      {(jobs ?? []).map((j) => {
        const p = jobProblem(j);
        return (
          <Box key={j.job} sx={{ mb: 0.75 }}>
            <Typography variant="caption" component="div" sx={{ fontWeight: 700 }}>
              {p ? "✕" : "✓"} {j.job} · {j.schedule}
            </Typography>
            <Typography variant="caption" component="div">
              {p ? `This job ${p}.` : `Last run ${fmtWhen(j.started_at ?? undefined) ?? "unknown"}, exit ${String(j.exit_code ?? "unknown")}.`}
            </Typography>
            {j.message ? (
              <Typography variant="caption" component="div" sx={{ opacity: 0.85, overflowWrap: "anywhere" }}>
                {j.message}
              </Typography>
            ) : null}
          </Box>
        );
      })}
    </Box>
  );

  return (
    <Tooltip title={tooltip} placement="right">
      <ButtonBase
        onClick={load}
        aria-label={`${label}. Select to refresh.`}
        sx={{
          width: "100%",
          justifyContent: folded ? "center" : "flex-start",
          gap: 1,
          px: folded ? 0 : 1.5,
          minHeight: 40,
          borderRadius: 1,
          color,
          "&:hover": { bgcolor: "action.hover" },
        }}
      >
        <Box
          component="span"
          aria-hidden
          sx={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            border: 1.5,
            borderColor: "currentColor",
            display: "grid",
            placeItems: "center",
            fontSize: "0.7rem",
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {glyph}
        </Box>
        {folded ? null : (
          <Typography variant="caption" noWrap sx={{ fontWeight: 600 }}>
            {label}
          </Typography>
        )}
      </ButtonBase>
    </Tooltip>
  );
}
