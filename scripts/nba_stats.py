import json
import time
import random
from typing import Dict, Any

import requests

NBA_STATS_BASE = "https://stats.nba.com/stats"

# NBA stats site blocks generic clients; use common browser headers.
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "Connection": "keep-alive",
}


def request_json(endpoint: str, params: Dict[str, Any], retries: int = 6, sleep_s: float = 1.5) -> Dict[str, Any]:
    url = f"{NBA_STATS_BASE}/{endpoint}"
    last_exc = None
    for attempt in range(retries):
        try:
            # Longer timeout and backoff to handle stats.nba.com slowness.
            resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=(10, 90))
            if resp.status_code == 429:
                time.sleep(sleep_s * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            # Exponential backoff with small jitter.
            base = sleep_s * (2 ** attempt)
            jitter = random.uniform(0, 0.5)
            time.sleep(base + jitter)
    raise RuntimeError(f"NBA stats request failed after {retries} attempts: {endpoint} {params}") from last_exc


def result_set_to_rows(data: Dict[str, Any], set_name: str) -> list[Dict[str, Any]]:
    result_sets = []
    if isinstance(data.get("resultSets"), list):
        result_sets.extend(data.get("resultSets", []))
    if isinstance(data.get("resultSet"), dict):
        result_sets.append(data.get("resultSet"))

    for rs in result_sets:
        if isinstance(rs, dict) and rs.get("name") == set_name:
            headers = rs.get("headers", [])
            rows = []
            for row in rs.get("rowSet", []):
                rows.append({headers[i]: row[i] for i in range(len(headers))})
            return rows
    raise KeyError(f"Result set not found: {set_name}")


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2, sort_keys=True)
