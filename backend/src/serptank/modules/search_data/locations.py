"""Country -> location codes (Google Ads geo target IDs, also used by DataForSEO)."""

from __future__ import annotations

# ISO 3166-1 alpha-2 -> Google Ads / DataForSEO country location code.
LOCATION_CODES = {
    "US": 2840, "GB": 2826, "DE": 2276, "FR": 2250, "NL": 2528, "ES": 2724, "IT": 2380,
    "CA": 2124, "AU": 2036, "IN": 2356, "BR": 2076, "JP": 2392, "MX": 2484, "BE": 2056,
    "CH": 2756, "AT": 2040, "SE": 2752, "NO": 2578, "DK": 2208, "FI": 2246, "PL": 2616,
    "PT": 2620, "IE": 2372, "NZ": 2554, "ZA": 2710, "SG": 2702, "KR": 2410, "CN": 2156,
    "RU": 2643, "CZ": 2203, "TR": 2792, "AR": 2032, "CL": 2152, "CO": 2170, "UA": 2804,
}  # fmt: skip


def location_code(country: str) -> int | None:
    return LOCATION_CODES.get(country.upper())
