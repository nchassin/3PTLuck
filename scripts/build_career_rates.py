from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date

from nba_stats import request_json, result_set_to_rows, write_json
from constants import DEFENDER_DISTANCE_RANGES, SEASON_START_YEAR
from season import season_for_date, season_strings


def base_params() -> dict:
    return {
        "LeagueID": "00",
        "PerMode": "Totals",
        "SeasonType": "Regular Season",
        "SeasonSegment": "",
        "Season": "",
        "DateFrom": "",
        "DateTo": "",
        "OpponentTeamID": "0",
        "TeamID": "0",
        "LastNGames": "0",
        "Month": "0",
        "Period": "0",
        "GameSegment": "",
        "Location": "",
        "Outcome": "",
        "VsConference": "",
        "VsDivision": "",
        "PORound": "0",
        "ShotClockRange": "",
        "DribbleRange": "",
        "TouchTimeRange": "",
        "CloseDefDistRange": "",
        "GeneralRange": "",
        "OverallRange": "",
        "StarterBench": "",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "PlusMinus": "N",
        "PaceAdjust": "N",
        "Rank": "N",
        "GameScope": "",
    }


def build_career_rates(end_season: str | None) -> dict:
    if end_season is None:
        end_season = season_for_date(date.today())

    end_year = int(end_season.split("-")[0])
    seasons = season_strings(SEASON_START_YEAR, end_year)

    totals = defaultdict(lambda: defaultdict(float))
    attempts = defaultdict(lambda: defaultdict(float))
    player_names = {}

    for season in seasons:
        for dist in DEFENDER_DISTANCE_RANGES:
            params = base_params()
            params["Season"] = season
            params["CloseDefDistRange"] = dist

            data = request_json("leaguedashplayerptshot", params)
            rows = result_set_to_rows(data, "LeagueDashPTShots")

            for row in rows:
                player_id = str(row.get("PLAYER_ID"))
                player_names[player_id] = row.get("PLAYER_NAME")
                fg3a = float(row.get("FG3A", 0) or 0)
                fg3m = float(row.get("FG3M", 0) or 0)
                attempts[player_id][dist] += fg3a
                totals[player_id][dist] += fg3m

    career = {}
    league_totals = defaultdict(float)
    league_attempts = defaultdict(float)

    for player_id, by_dist in attempts.items():
        career[player_id] = {
            "player_id": player_id,
            "player_name": player_names.get(player_id, ""),
            "by_distance": {},
        }
        for dist, fg3a in by_dist.items():
            fg3m = totals[player_id].get(dist, 0.0)
            pct = (fg3m / fg3a) if fg3a > 0 else None
            career[player_id]["by_distance"][dist] = {
                "fg3a": fg3a,
                "fg3m": fg3m,
                "pct": pct,
            }
            league_attempts[dist] += fg3a
            league_totals[dist] += fg3m

    league = {
        dist: {
            "fg3a": league_attempts[dist],
            "fg3m": league_totals[dist],
            "pct": (league_totals[dist] / league_attempts[dist]) if league_attempts[dist] > 0 else None,
        }
        for dist in DEFENDER_DISTANCE_RANGES
    }

    return {
        "seasons": seasons,
        "career": career,
        "league": league,
        "generated_at": date.today().isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end-season", default=None, help="Season string like 2024-25")
    parser.add_argument("--out", default="data/career_rates.json")
    args = parser.parse_args()

    payload = build_career_rates(args.end_season)
    write_json(args.out, payload)


if __name__ == "__main__":
    main()
