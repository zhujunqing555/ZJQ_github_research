#!/usr/bin/env python3
"""Read public GitHub discovery/metadata/star history; persist honest local baselines."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UTC = dt.timezone.utc
API = "https://api.github.com"
API_VERSION = "2026-03-10"
CODEX_HOME = Path(os.environ["CODEX_HOME"]).expanduser() if os.environ.get("CODEX_HOME") else Path.home() / ".codex"
DEFAULT_STATE = CODEX_HOME / "skill-radars" / "zjq-github-research" / "state" / "star_snapshots.json"


def timestamp(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).netloc != "api.github.com":
            raise urllib.error.URLError("Refused redirect outside public GitHub API")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class GitHub:
    def __init__(self):
        self.opener = urllib.request.build_opener(PublicRedirect())
        self.rate_limits = []
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.blocked = None

    def get(self, path, parameters=None):
        if self.blocked:
            return None, {"endpoint": path, "reason": "request skipped after API limit/auth block", **self.blocked}
        url = API + path
        if parameters:
            url += "?" + urllib.parse.urlencode(parameters)
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION,
                   "User-Agent": "ZJQ-github-research-readonly"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self.opener.open(request, timeout=20) as response:
                data = json.load(response)
                observed = {"endpoint": path, "http_date": response.headers.get("Date"),
                            "remaining": response.headers.get("X-RateLimit-Remaining"),
                            "reset_epoch": response.headers.get("X-RateLimit-Reset")}
                self.rate_limits.append(observed)
                return data, None
        except urllib.error.HTTPError as error:
            if error.code in (401, 429) or (error.code == 403 and error.headers.get("X-RateLimit-Remaining") == "0"):
                self.blocked = {"http_status": error.code, "rate_reset_epoch": error.headers.get("X-RateLimit-Reset")}
            return None, {"endpoint": path, "http_status": error.code,
                          "rate_remaining": error.headers.get("X-RateLimit-Remaining"),
                          "rate_reset_epoch": error.headers.get("X-RateLimit-Reset"),
                          "retry_after": error.headers.get("Retry-After"),
                          "reason": "public API request failed; not retried"}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            return None, {"endpoint": path, "reason": "network/JSON failure", "error_type": type(error).__name__}


def aggregate_history(rows, as_of):
    """Aggregate supplied bins only. Missing rows never become zero-star days."""
    result = {"source": "github_stargazers_history", "metric": "stars_created_gross",
              "timezone_boundaries": "GitHub calendar boundaries unspecified; UTC labels are approximations",
              "exact_168_hours": False, "status": "unavailable", "weeks": []}
    if not isinstance(rows, list) or not rows:
        result["reason"] = "empty or invalid history; missing data is not zero"
        return result
    bins = {}
    try:
        for row in rows:
            week, days, total = row["week"], row["days"], row["total"]
            if not isinstance(week, int) or len(days) != 7 or any(type(n) is not int or n < 0 for n in days):
                raise ValueError("invalid weekly row")
            start = dt.datetime.fromtimestamp(week, UTC)
            if any((start.date() + dt.timedelta(days=i)) in bins for i in range(7)):
                raise ValueError("overlapping weekly rows")
            for i, count in enumerate(days):
                bins[start.date() + dt.timedelta(days=i)] = count
            result["weeks"].append({"week_epoch": week, "utc_label_start": start.date().isoformat(),
                                    "total": total, "days_sunday_first": days,
                                    "sum_matches_total": sum(days) == total})
    except (KeyError, TypeError, ValueError, OverflowError):
        result["reason"] = "history schema invalid; no heat asserted"
        return result
    end = as_of.date() - dt.timedelta(days=1)
    dates = [end - dt.timedelta(days=i) for i in range(6, -1, -1)]
    supplied = [date for date in dates if date in bins]
    result["trailing_daily_bins"] = {
        "start_utc_label": dates[0].isoformat(), "end_utc_label": dates[-1].isoformat(),
        "covered_days": len(supplied), "requested_days": 7,
        "count": sum(bins[date] for date in supplied) if len(supplied) == 7 else None,
        "status": "complete_bins_boundary_caveat" if len(supplied) == 7 else "incomplete",
        "note": "7 supplied calendar bins ending yesterday by UTC labels; not exact local days or rolling168h",
        "daily": [{"utc_label": date.isoformat(), "count": bins.get(date)} for date in dates]}
    complete = [row for row in result["weeks"]
                if dt.datetime.fromtimestamp(row["week_epoch"], UTC) + dt.timedelta(days=7) <= as_of]
    if complete:
        latest = max(complete, key=lambda row: row["week_epoch"])
        result["latest_completed_reported_week"] = {
            "start_utc_label": latest["utc_label_start"], "week_epoch": latest["week_epoch"],
            "count": sum(latest["days_sunday_first"]),
            "note": "latest fully elapsed API calendar week; Sunday first, provider boundary timezone unspecified"}
    result["status"] = "available" if len(supplied) == 7 else "partial"
    return result


def snapshot_growth(history, repository, current_count, as_of):
    valid = []
    for record in history:
        try:
            observed = timestamp(record["observed_at"])
            if record["repository"].lower() == repository.lower() and type(record["stars"]) is int:
                if observed <= as_of - dt.timedelta(days=7):
                    valid.append((observed, record["stars"]))
        except (KeyError, ValueError, TypeError):
            continue
    if not valid:
        return {"source": "local_total_snapshots", "metric": "net_total_change", "status": "baseline_pending",
                "count": None, "reason": "no observed baseline at least7days old; total stars cannot prove weekly heat"}
    observed, count = max(valid)
    days = (as_of - observed).total_seconds() / 86400
    return {"source": "local_total_snapshots", "metric": "net_total_change", "status": "observed",
            "start": iso(observed), "end": iso(as_of), "elapsed_days": round(days, 3),
            "start_total": count, "end_total": current_count, "count": current_count - count,
            "weekly_comparable": 7 <= days <= 8,
            "note": "net total change includes removals; interval is displayed and must not be called gross stars created"}


def metadata(repo):
    keys = ("id", "full_name", "html_url", "description", "stargazers_count", "forks_count", "open_issues_count",
            "created_at", "updated_at", "pushed_at", "language", "topics", "archived", "disabled", "fork",
            "default_branch", "homepage", "license")
    return {key: repo.get(key) for key in keys}


def collect(args):
    client, as_of = GitHub(), dt.datetime.now(UTC)
    report = {"schema_version": 1, "generated_at": iso(as_of), "report_date": args.report_date,
              "api_version": API_VERSION, "scope": "bounded public candidates, not all GitHub",
              "discovery": [], "repositories": [], "errors": []}
    found = {}
    for query in args.query:
        response, error = client.get("/search/repositories", {"q": query, "sort": args.sort,
                                                               "order": "desc", "per_page": args.limit})
        if error:
            report["errors"].append(error)
            report["discovery"].append({"query": query, "status": "failed"})
            continue
        report["discovery"].append({"query": query, "status": "ok", "total_count": response.get("total_count"),
                                    "incomplete_results": response.get("incomplete_results"),
                                    "returned_count": len(response.get("items", [])), "page_limit": args.limit})
        for repo in response.get("items", []):
            if not repo.get("private"):
                key = repo["full_name"].lower()
                found.setdefault(key, {"name": repo["full_name"], "queries": []})["queries"].append(query)
    for name in args.repo:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            report["errors"].append({"repository": name, "reason": "invalid owner/repo"})
        else:
            found.setdefault(name.lower(), {"name": name, "queries": []})
    snapshots = []
    if args.state.exists():
        try:
            snapshots = json.loads(args.state.read_text(encoding="utf-8"))
            if not isinstance(snapshots, list):
                raise ValueError("invalid snapshot state")
        except (OSError, ValueError):
            report["errors"].append({"reason": "snapshot state unreadable; will not overwrite it", "state": str(args.state)})
            snapshots = None
    for discovered in found.values():
        name = discovered["name"]
        base = "/repos/" + name
        repo, error = client.get(base)
        if error:
            report["errors"].append(error)
            report["repositories"].append({"full_name": name, "status": "metadata_failed", "error": error})
            continue
        if repo.get("private"):
            report["errors"].append({"repository": name, "reason": "not a public repository; skipped"})
            continue
        record = metadata(repo)
        record.update({"status": "ok", "observed_at": iso(dt.datetime.now(UTC)), "discovered_by": discovered["queries"]})
        history, history_error = client.get(base + "/stargazers/history", {"per_page": 3, "page": 1})
        heat = aggregate_history(history, as_of)
        if history_error:
            heat["request_error"] = history_error
            report["errors"].append(history_error)
        record["heat"] = heat
        record["snapshot_net_growth"] = snapshot_growth(snapshots or [], record["full_name"], record["stargazers_count"], as_of)
        if heat["status"] != "available":
            record["heat_fallback"] = record["snapshot_net_growth"]
        report["repositories"].append(record)
        if snapshots is not None:
            snapshots.append({"repository": record["full_name"], "observed_at": record["observed_at"],
                              "stars": record["stargazers_count"]})
    if snapshots is not None:
        cutoff = as_of - dt.timedelta(days=400)
        retained = []
        for record in snapshots:
            try:
                if timestamp(record["observed_at"]) >= cutoff:
                    retained.append(record)
            except (KeyError, TypeError, ValueError):
                continue
        save_json(args.state, retained)
    report["rate_limits"] = client.rate_limits
    succeeded = any(row.get("status") == "ok" for row in report["repositories"])
    report["status"] = "failed" if not succeeded else ("partial" if report["errors"] else "ok")
    save_json(args.output, report)
    print(json.dumps({"output": str(args.output), "status": report["status"],
                      "repositories": len(report["repositories"]), "errors": len(report["errors"])}, ensure_ascii=False))
    return 0 if succeeded else 2


def inventory(args):
    records, errors = [], []
    for root in args.root:
        if not root.exists():
            errors.append({"root": str(root), "reason": "missing root"})
            continue
        for path in sorted(root.rglob("SKILL.md")):
            try:
                content = path.read_text(encoding="utf-8-sig")
                frontmatter = content.split("---", 2)[1] if content.startswith("---") else ""
                name = re.search(r"^name:\s*(.+)$", frontmatter, re.M)
                description = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
                records.append({"path": str(path.resolve()), "name": name.group(1).strip(" \"'") if name else path.parent.name,
                                "description": description.group(1).strip(" \"'") if description else None})
            except (OSError, IndexError) as error:
                errors.append({"path": str(path), "reason": type(error).__name__})
    save_json(args.output, {"generated_at": iso(dt.datetime.now(UTC)), "skills": records, "errors": errors})
    print(json.dumps({"output": str(args.output), "skills": len(records), "errors": len(errors)}))
    return 0 if records else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("collect", help="Collect bounded public candidates and real heat evidence")
    p.add_argument("--query", action="append", default=[])
    p.add_argument("--repo", action="append", default=[])
    p.add_argument("--limit", type=int, default=10, choices=range(1, 101))
    p.add_argument("--sort", choices=("stars", "updated"), default="stars")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--state", type=Path, default=DEFAULT_STATE)
    p.add_argument("--report-date", help="Client date label only; never overrides actual observation timestamps")
    p.set_defaults(run=collect)
    p = commands.add_parser("inventory", help="Read local SKILL.md names/descriptions without execution")
    p.add_argument("--root", action="append", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(run=inventory)
    args = parser.parse_args()
    if args.command == "collect" and not args.query and not args.repo:
        parser.error("collect requires --query or --repo")
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
