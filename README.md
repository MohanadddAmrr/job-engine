# job-engine

Automated daily discovery of remote and Gulf-region AI/ML and contract roles for a Cairo-based data scientist. The pipeline fetches listings, scores them against a personalised profile, and outputs a ranked dashboard hosted via GitHub Pages.

## How it works

A GitHub Actions workflow runs twice daily (08:00 and 18:00 Cairo time). Each run:

1. **Fetches** live job listings from Remotive, RemoteOK, and Arbeitnow.
2. **Scores** every job against `config/profile.yaml` — matching on target titles, tech stack, keywords, remote status, and recency.
3. **Builds** a static dashboard at `docs/index.html` with three tracks: Remote, Relocation (on-site), and Contract (platform targets).
4. **Commits** updated data and dashboard back to the repo. GitHub Pages serves `docs/` automatically.

To tune results, edit `config/profile.yaml` — adjust target titles, stack weights, block terms, or the score threshold.

**Status: active**
