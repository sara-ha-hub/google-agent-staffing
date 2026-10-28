"""World Bank Global Economic Prospects GDP growth.

The series is the one behind https://databank.worldbank.org/id/5cb6b81 :
source 27, indicator NYGDPMKTPKDZ. These are outside projections, not our
eligible sign-up forecast.
"""

import json
import urllib.error
import urllib.request

from genai.forecast_view import canonicalize, known_countries

INDICATOR = "NYGDPMKTPKDZ"
SOURCE_ID = 27
SOURCE_LABEL = "World Bank Global Economic Prospects (DataBank 5cb6b81)"
NOTE = "Outside GDP projection. This is not the eligible sign-up forecast."

# GEP publishes these economies only inside a group, not as their own series.
GROUP = {
    "Germany": ("Euro Area", "XC"),
    "France": ("Euro Area", "XC"),
    "Italy": ("Euro Area", "XC"),
    "Spain": ("Euro Area", "XC"),
    "UK": ("Advanced economies", "1E"),
    "Australia": ("Advanced economies", "1E"),
    "Canada": ("Advanced economies", "1E"),
    "South Korea": ("Advanced economies", "1E"),
}

# Project country name to the World Bank ISO3 code.
ISO3 = {
    "USA": "USA",
    "UK": "GBR",
    "Germany": "DEU",
    "India": "IND",
    "Brazil": "BRA",
    "Japan": "JPN",
    "Australia": "AUS",
    "Canada": "CAN",
    "France": "FRA",
    "Mexico": "MEX",
    "China": "CHN",
    "Italy": "ITA",
    "Spain": "ESP",
    "Poland": "POL",
    "South Korea": "KOR",
    "South Africa": "ZAF",
    "Vietnam": "VNM",
    "Argentina": "ARG",
    "Turkey": "TUR",
    "Indonesia": "IDN",
    "Thailand": "THA",
    "UAE": "ARE",
}


def gdp_growth(country: str | None = None, year: int = 2026) -> dict:
    """Real GDP growth, in percent, for one project country or all of them."""
    if year < 1990 or year > 2100:
        raise ValueError("year is out of range")
    names = [canonicalize(country)] if country else known_countries()
    missing = [name for name in names if name not in ISO3]
    if missing:
        raise ValueError(f"No World Bank code for {', '.join(missing)}")
    codes = [ISO3[name] for name in names]
    if any(name in GROUP for name in names):
        codes.extend(sorted({group_id for _, group_id in GROUP.values()}))
    by_code = _fetch(codes, year)
    points = []
    for name in names:
        code = ISO3[name]
        found = by_code.get(code)
        point = {
            "country": name,
            "iso3": code,
            "year": year,
            "gdp_growth_percent": None if found is None else found["value"],
            "indicator": INDICATOR,
            "source": SOURCE_LABEL,
            "note": NOTE,
        }
        if found is None and name in GROUP:
            label, group_id = GROUP[name]
            group = by_code.get(group_id)
            group_value = None if group is None else group["value"]
            point["group_name"] = label
            point["group_gdp_growth_percent"] = group_value
            shown = "unavailable" if group_value is None else f"{group_value}%"
            point["note"] = (
                "Global Economic Prospects does not publish a separate series for this country. "
                f"The published group is {label} at {shown}. "
                "That group figure is not this country's growth. "
                + NOTE
            )
        points.append(point)
    return {"year": year, "indicator": INDICATOR, "source": SOURCE_LABEL, "note": NOTE, "points": points}


def _fetch(codes: list[str], year: int) -> dict[str, dict]:
    joined = ";".join(codes)
    url = (
        "https://api.worldbank.org/v2/country/"
        f"{joined}/indicator/{INDICATOR}"
        f"?source={SOURCE_ID}&format=json&date={year}:{year}&per_page=300"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "google-agent-staffing/genai"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ValueError(f"World Bank request failed: {exc}") from exc
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("World Bank returned an unexpected payload")
    rows = payload[1] if isinstance(payload[1], list) else []
    found: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = row.get("countryiso3code")
        country = row.get("country") or {}
        country_id = country.get("id")
        value = row.get("value")
        entry = {"value": None if value is None else float(value)}
        if code:
            found[code] = entry
        if country_id:
            found[country_id] = entry
    return found
