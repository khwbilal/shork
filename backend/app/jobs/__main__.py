"""python -m app.jobs <job>: run one scheduled job and exit with its code."""

from __future__ import annotations

import sys

from . import JOBS, run_job


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(f"usage: python -m app.jobs <job>   (jobs: {', '.join(sorted(JOBS))})", file=sys.stderr)
        return 2
    return run_job(args[0])


if __name__ == "__main__":
    sys.exit(main())
