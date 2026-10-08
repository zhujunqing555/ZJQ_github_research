#!/usr/bin/env python3
"""Initialize radar templates without overwriting existing local state."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SKILL_ID = "zjq-github-research"
TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
FILES = ("config.json", "tasks.json", "sources.json", "candidates.json", "feedback.json")


def codex_home():
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def activation_date(explicit, timezone):
    if explicit:
        return dt.date.fromisoformat(explicit)
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        if timezone == "Asia/Shanghai":
            zone = dt.timezone(dt.timedelta(hours=8))
        elif timezone in ("UTC", "Etc/UTC"):
            zone = dt.timezone.utc
        else:
            raise ValueError("Timezone data unavailable; provide --date YYYY-MM-DD or install tzdata")
    return dt.datetime.now(zone).date()


def initialize(state_dir, activated_on, timezone, templates=TEMPLATES):
    state_dir = Path(state_dir).expanduser()
    prepared = {}
    for name in FILES:
        prepared[name] = json.loads((templates / name).read_text(encoding="utf-8-sig"))
    config = prepared["config.json"]
    config.update(activated_on=activated_on.isoformat(), timezone=timezone,
                  bootstrap_until_inclusive=(activated_on + dt.timedelta(days=config["bootstrap_days"] - 1)).isoformat(),
                  continuous_from=(activated_on + dt.timedelta(days=config["bootstrap_days"])).isoformat())
    state_dir.mkdir(parents=True, exist_ok=True)
    created, preserved = [], []
    for name, value in prepared.items():
        path = state_dir / name
        try:
            # Exclusive creation protects user edits and concurrent initialization.
            with path.open("x", encoding="utf-8", newline="\n") as destination:
                destination.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            created.append(name)
        except FileExistsError:
            preserved.append(name)
    for directory in ("runs", "reports", "state"):
        (state_dir / directory).mkdir(exist_ok=True)
    # Never replace a malformed existing config with a fresh one.
    current = json.loads((state_dir / "config.json").read_text(encoding="utf-8-sig"))
    return {"state_dir": str(state_dir.resolve()), "created": created, "preserved": preserved,
            "activated_on": current.get("activated_on"), "automation_id": current.get("automation_id")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="First activation date; does not alter an existing config")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    try:
        activated_on = activation_date(args.date, args.timezone)
        state_dir = args.state_dir or codex_home() / "skill-radars" / SKILL_ID
        result = initialize(state_dir, activated_on, args.timezone)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
