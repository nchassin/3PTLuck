# NBA 3PT Coverage-Adjusted Scores

Prototype that estimates what each game’s score would be if every 3-point attempt went in at each player’s **career rate by defender distance** (very tight, tight, open, wide open).

## What It Does
- Pulls **NBA.com tracking splits** by defender distance for each game day.
- Normalizes each player’s 3PA by their **career defender-distance rates**.
- Computes an adjusted score per team:
  - `adjusted = actual_pts - actual_3PM * 3 + expected_3PM * 3`

## Data Flow
1. `scripts/refresh_career_rates.py`
   - Builds career defender-distance rates using `leaguedashplayerptshot` across seasons.
   - Caches results to `data/career_rates.json` and refreshes if the file is older than 14 days.
2. `scripts/update_scores.py`
   - Reads scoreboard for a date.
   - Fetches team box scores for actual 3PM.
   - Fetches tracking splits for defender distance.
   - Writes `public/data/latest.json` for the frontend.

## Local Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/refresh_career_rates.py --out data/career_rates.json
python scripts/update_scores.py --career data/career_rates.json --out public/data/latest.json --days-back 2
```

Open `public/index.html` in a browser (or use any static file server).

## Hosting (GitHub Pages)
1. Push this repo to GitHub.
2. Enable GitHub Pages for the `main` branch and `/public` folder.
3. The GitHub Actions workflow (`.github/workflows/update.yml`) runs hourly and commits new data.

## Notes & Caveats
- NBA tracking data often lags box scores by a few minutes to a few hours.
- The NBA Stats endpoints are **unofficial and rate-limited**; headers are required.
- Tracking splits may not cover 100% of 3PA; in that case the adjusted score is still anchored to actual 3PM.

## Configuration
- Defender distance buckets are in `scripts/constants.py`.
- Update cadence is controlled in `.github/workflows/update.yml`.
