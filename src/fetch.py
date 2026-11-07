"""Fetch job listings from configured sources and save raw results to data/."""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from dateutil import parser as dateparser

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

TIMEOUT = 20
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AGGREGATOR_MARKERS = ["jobgether", "huzzle", "linkup.com"]


def _is_aggregator(company, url):
    haystack = (company + " " + url).lower()
    return any(m in haystack for m in AGGREGATOR_MARKERS)


def _normalize_key(text):
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _parse_date(raw):
    if not raw:
        return ""
    try:
        if isinstance(raw, (int, float)) or (isinstance(raw, str) and raw.isdigit()):
            return datetime.fromtimestamp(int(raw), tz=timezone.utc).date().isoformat()
        return dateparser.parse(str(raw)).date().isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
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
        company = j.get("company_name", "")
        url = j.get("url", "")
        out.append({
            "source": "remotive",
            "title": j.get("title", ""),
            "company": company,
            "location": j.get("candidate_required_location", "") or "",
            "url": url,
            "date": _parse_date(j.get("publication_date")),
            "tags": [j["category"].lower()] if j.get("category") else [],
            "description": j.get("description", ""),
            "remote": True,
            "via_aggregator": _is_aggregator(company, url),
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
        company = j.get("company", "")
        url = j.get("url", "")
        out.append({
            "source": "remoteok",
            "title": j.get("position", ""),
            "company": company,
            "location": j.get("location", "") or "",
            "url": url,
            "date": _parse_date(j.get("date")),
            "tags": [t.lower() for t in tags_raw] if isinstance(tags_raw, list) else [],
            "description": j.get("description", ""),
            "remote": True,
            "via_aggregator": _is_aggregator(company, url),
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
        company = j.get("company_name", "")
        url = j.get("url", "")
        out.append({
            "source": "arbeitnow",
            "title": j.get("title", ""),
            "company": company,
            "location": j.get("location", "") or "",
            "url": url,
            "date": _parse_date(j.get("created_at")),
            "tags": [t.lower() for t in tags_raw] if isinstance(tags_raw, list) else [],
            "description": j.get("description", ""),
            "remote": bool(j.get("remote")),
            "via_aggregator": _is_aggregator(company, url),
        })
    return out


def fetch_jobs():
    all_jobs = []
    all_jobs.extend(fetch_remotive())
    all_jobs.extend(fetch_remoteok())
    all_jobs.extend(fetch_arbeitnow())

    seen_urls = set()
    seen_title_company = set()
    deduped = []
    for job in all_jobs:
        if job["url"] and job["url"] in seen_urls:
            continue
        tc_key = (_normalize_key(job["title"]), _normalize_key(job["company"]))
        if tc_key in seen_title_company:
            continue
        if job["url"]:
            seen_urls.add(job["url"])
        seen_title_company.add(tc_key)
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
