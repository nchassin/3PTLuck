from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

from build_career_rates import build_career_rates
from nba_stats import write_json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/career_rates.json")
    parser.add_argument("--max-age-days", type=int, default=14)
    args = parser.parse_args()

    out_path = Path(args.out)
    refresh = True

    if out_path.exists():
        mtime = datetime.utcfromtimestamp(out_path.stat().st_mtime)
        if datetime.utcnow() - mtime < timedelta(days=args.max_age_days):
            refresh = False

    if refresh:
        payload = build_career_rates(None)
        write_json(args.out, payload)


if __name__ == "__main__":
    main()
