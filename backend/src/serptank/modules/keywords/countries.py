"""ISO 3166-1 alpha-2 -> alpha-3 (Search Console reports countries as lower alpha-3)."""

from __future__ import annotations

ALPHA3 = {
    "US": "usa", "GB": "gbr", "DE": "deu", "FR": "fra", "NL": "nld", "ES": "esp", "IT": "ita",
    "CA": "can", "AU": "aus", "IN": "ind", "BR": "bra", "JP": "jpn", "MX": "mex", "BE": "bel",
    "CH": "che", "AT": "aut", "SE": "swe", "NO": "nor", "DK": "dnk", "FI": "fin", "PL": "pol",
    "PT": "prt", "IE": "irl", "NZ": "nzl", "ZA": "zaf", "SG": "sgp", "KR": "kor", "CN": "chn",
    "RU": "rus", "CZ": "cze", "TR": "tur", "AR": "arg", "CL": "chl", "CO": "col", "UA": "ukr",
}  # fmt: skip


def gsc_country(alpha2: str) -> str | None:
    return ALPHA3.get(alpha2.upper())
