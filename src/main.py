"""Orchestrate the job-engine pipeline: fetch, score, and build dashboard."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fetch import fetch_jobs
from src.score import score_jobs
from src.build_dashboard import build_dashboard


def main():
    fetch_jobs()
    score_jobs()
    build_dashboard()


if __name__ == "__main__":
    main()
