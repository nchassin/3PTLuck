from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from nba_stats import request_json, result_set_to_rows, write_json
from constants import DEFENDER_DISTANCE_RANGES
from season import season_for_date


def load_career_rates(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def scoreboard_for_date(game_date: date) -> dict:
    params = {
        "LeagueID": "00",
        "DayOffset": "0",
        "GameDate": game_date.strftime("%Y-%m-%d"),
    }
    return request_json("scoreboardv2", params)


def boxscore_team_stats(game_id: str) -> list[dict]:
    params = {
        "GameID": game_id,
        "StartPeriod": "0",
        "EndPeriod": "10",
        "StartRange": "0",
        "EndRange": "28800",
        "RangeType": "0",
    }
    data = request_json("boxscoretraditionalv2", params)
    return result_set_to_rows(data, "TeamStats")


def player_tracking_by_distance(game_date: date, team_id: str, opponent_team_id: str, season: str) -> dict:
    totals = defaultdict(lambda: defaultdict(float))

    for dist in DEFENDER_DISTANCE_RANGES:
        params = {
            "LeagueID": "00",
            "PerMode": "Totals",
            "SeasonType": "Regular Season",
            "Season": season,
            "DateFrom": game_date.strftime("%m/%d/%Y"),
            "DateTo": game_date.strftime("%m/%d/%Y"),
            "TeamID": team_id,
            "OpponentTeamID": opponent_team_id,
            "LastNGames": "0",
            "Month": "0",
            "Period": "0",
            "GameSegment": "",
            "Location": "",
            "Outcome": "",
            "VsConference": "",
            "VsDivision": "",
            "SeasonSegment": "",
            "PORound": "0",
            "ShotClockRange": "",
            "DribbleRange": "",
            "TouchTimeRange": "",
            "CloseDefDistRange": dist,
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

        data = request_json("leaguedashplayerptshot", params)
        rows = result_set_to_rows(data, "LeagueDashPTShots")
        for row in rows:
            player_id = str(row.get("PLAYER_ID"))
            fg3a = float(row.get("FG3A", 0) or 0)
            fg3m = float(row.get("FG3M", 0) or 0)
            totals[player_id][dist] += fg3a
            totals[player_id][f"{dist}__M"] += fg3m

    return totals


def expected_3pm(player_tracking: dict, career_rates: dict) -> tuple[float, dict]:
    league = career_rates["league"]
    career = career_rates["career"]
    by_player = {}
    total_expected = 0.0

    for player_id, by_dist in player_tracking.items():
        expected = 0.0
        detail = {}
        for dist in DEFENDER_DISTANCE_RANGES:
            fg3a = float(by_dist.get(dist, 0.0))
            if fg3a <= 0:
                continue
            player_career = career.get(player_id, {}).get("by_distance", {}).get(dist, {})
            pct = player_career.get("pct")
            if pct is None:
                pct = league.get(dist, {}).get("pct")
            if pct is None:
                pct = 0.0
            expected_dist = fg3a * pct
            expected += expected_dist
            detail[dist] = {
                "fg3a": fg3a,
                "pct": pct,
                "expected_3pm": expected_dist,
            }
        if expected > 0:
            by_player[player_id] = {
                "expected_3pm": expected,
                "by_distance": detail,
            }
        total_expected += expected

    return total_expected, by_player


def compute_for_date(game_date: date, career_rates: dict) -> dict:
    season = season_for_date(game_date)
    scoreboard = scoreboard_for_date(game_date)
    games = result_set_to_rows(scoreboard, "GameHeader")
    lines = result_set_to_rows(scoreboard, "LineScore")

    line_by_game_team = {}
    for line in lines:
        line_by_game_team[(str(line.get("GAME_ID")), str(line.get("TEAM_ID")))] = line

    output_games = []

    for game in games:
        game_id = str(game.get("GAME_ID"))
        home_id = str(game.get("HOME_TEAM_ID"))
        away_id = str(game.get("VISITOR_TEAM_ID"))

        home_line = line_by_game_team.get((game_id, home_id))
        away_line = line_by_game_team.get((game_id, away_id))
        if not home_line or not away_line:
            continue

        team_stats = boxscore_team_stats(game_id)
        stats_by_team = {str(row.get("TEAM_ID")): row for row in team_stats}
        home_stats = stats_by_team.get(home_id, {})
        away_stats = stats_by_team.get(away_id, {})

        # Tracking data by distance
        home_tracking = player_tracking_by_distance(game_date, home_id, away_id, season)
        away_tracking = player_tracking_by_distance(game_date, away_id, home_id, season)

        home_expected, home_players = expected_3pm(home_tracking, career_rates)
        away_expected, away_players = expected_3pm(away_tracking, career_rates)

        home_actual_3pm = float(home_stats.get("FG3M", 0) or 0)
        away_actual_3pm = float(away_stats.get("FG3M", 0) or 0)

        home_pts = float(home_line.get("PTS", 0) or 0)
        away_pts = float(away_line.get("PTS", 0) or 0)

        home_adj = home_pts - (home_actual_3pm * 3.0) + (home_expected * 3.0)
        away_adj = away_pts - (away_actual_3pm * 3.0) + (away_expected * 3.0)

        output_games.append(
            {
                "game_id": game_id,
                "game_status": game.get("GAME_STATUS_TEXT"),
                "game_date": game_date.isoformat(),
                "home": {
                    "team_id": home_id,
                    "team_abbr": home_line.get("TEAM_ABBREVIATION"),
                    "actual_pts": home_pts,
                    "actual_3pm": home_actual_3pm,
                    "expected_3pm": home_expected,
                    "adjusted_pts": home_adj,
                    "player_detail": home_players,
                },
                "away": {
                    "team_id": away_id,
                    "team_abbr": away_line.get("TEAM_ABBREVIATION"),
                    "actual_pts": away_pts,
                    "actual_3pm": away_actual_3pm,
                    "expected_3pm": away_expected,
                    "adjusted_pts": away_adj,
                    "player_detail": away_players,
                },
            }
        )

    return {
        "date": game_date.isoformat(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "games": output_games,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--days-back", type=int, default=1, help="How many days back to compute")
    parser.add_argument("--career", default="data/career_rates.json")
    parser.add_argument("--out", default="public/data/latest.json")
    args = parser.parse_args()

    career_rates = load_career_rates(args.career)
    if career_rates is None:
        # If career rates are missing, emit an empty payload so CI can succeed.
        today = date.today()
        write_json(
            args.out,
            {
                "date": today.isoformat(),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "games": [],
                "note": "career_rates_missing",
            },
        )
        return

    if args.date:
        target_date = date.fromisoformat(args.date)
        payload = compute_for_date(target_date, career_rates)
        write_json(args.out, payload)
    else:
        # If no date specified, compute for the last N days and pick the most recent with games.
        today = date.today()
        selected = None
        for i in range(args.days_back + 1):
            d = today - timedelta(days=i)
            payload = compute_for_date(d, career_rates)
            if payload.get("games"):
                selected = payload
                break
        if selected is None:
            selected = {
                "date": (today - timedelta(days=1)).isoformat(),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "games": [],
            }
        write_json(args.out, selected)


if __name__ == "__main__":
    main()
