"""Fetch job listings from configured sources and save raw results to data/."""

import json
import logging
import os
from pathlib import Path

import requests
from dateutil import parser as dateparser

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

TIMEOUT = 20
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _parse_date(raw):
    if not raw:
        return ""
    try:
        return dateparser.parse(str(raw)).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return ""


def fetch_remotive():
    try:
        resp = requests.get("https://remotive.com/api/remote-jobs", timeout=TIMEOUT)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except Exception as exc:
        log.warning("remotive failed: %s", exc)
        return []

    out = []
    for j in jobs:
        out.append({
            "source": "remotive",
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("candidate_required_location", "") or "",
            "url": j.get("url", ""),
            "date": _parse_date(j.get("publication_date")),
            "tags": [j["category"].lower()] if j.get("category") else [],
            "description": j.get("description", ""),
            "remote": True,
        })
    return out


def fetch_remoteok():
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "job-engine/1.0"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("remoteok failed: %s", exc)
        return []

    out = []
    for j in data[1:]:
        if not isinstance(j, dict):
            continue
        tags_raw = j.get("tags") or []
        out.append({
            "source": "remoteok",
            "title": j.get("position", ""),
            "company": j.get("company", ""),
            "location": j.get("location", "") or "",
            "url": j.get("url", ""),
            "date": _parse_date(j.get("date")),
            "tags": [t.lower() for t in tags_raw] if isinstance(tags_raw, list) else [],
            "description": j.get("description", ""),
            "remote": True,
        })
    return out


def fetch_arbeitnow():
    try:
        resp = requests.get("https://www.arbeitnow.com/api/job-board-api", timeout=TIMEOUT)
        resp.raise_for_status()
        jobs = resp.json().get("data", [])
    except Exception as exc:
        log.warning("arbeitnow failed: %s", exc)
        return []

    out = []
    for j in jobs:
        tags_raw = j.get("tags") or []
        out.append({
            "source": "arbeitnow",
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": j.get("location", "") or "",
            "url": j.get("url", ""),
            "date": _parse_date(j.get("created_at")),
            "tags": [t.lower() for t in tags_raw] if isinstance(tags_raw, list) else [],
            "description": j.get("description", ""),
            "remote": bool(j.get("remote")),
        })
    return out


def fetch_jobs():
    all_jobs = []
    all_jobs.extend(fetch_remotive())
    all_jobs.extend(fetch_remoteok())
    all_jobs.extend(fetch_arbeitnow())

    seen_urls = set()
    deduped = []
    for job in all_jobs:
        if job["url"] and job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            deduped.append(job)
        elif not job["url"]:
            deduped.append(job)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "raw_jobs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    log.info("Saved %d jobs to %s", len(deduped), out_path)
    return deduped


if __name__ == "__main__":
    jobs = fetch_jobs()
    from collections import Counter
    counts = Counter(j["source"] for j in jobs)
    print(f"\nTotal jobs fetched: {len(jobs)}")
    for src in ("remotive", "remoteok", "arbeitnow"):
        print(f"  {src}: {counts.get(src, 0)}")
    print(f"\nFirst 5 jobs:")
    for j in jobs[:5]:
        print(f"  [{j['source']}] {j['title']} — {j['company']} ({j['location']})")
