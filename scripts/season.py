from datetime import date


def season_for_date(d: date) -> str:
    # NBA season label, e.g. 2024-25
    if d.month >= 10:
        start_year = d.year
    else:
        start_year = d.year - 1
    end_year = (start_year + 1) % 100
    return f"{start_year}-{end_year:02d}"


def season_strings(start_year: int, end_year: int) -> list[str]:
    seasons = []
    for y in range(start_year, end_year + 1):
        end = (y + 1) % 100
        seasons.append(f"{y}-{end:02d}")
    return seasons
