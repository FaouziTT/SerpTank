"""robots.txt parsing and per-bot evaluation (RFC 9309 plus engine-specific extensions).

Why our own evaluator: audits must answer "may *Googlebot* fetch this?" and "may
*Bingbot*?" separately - rules often differ - and report engine-specific directives
(``crawl-delay`` is honoured by Bing and Yandex but ignored by Google; ``host`` and
``clean-param`` are Yandex-only). Matching follows RFC 9309 as implemented by Google:

* the group for the most specific matching product token wins (else ``*``); several
  groups naming the same token are merged;
* within a group the longest matching rule wins, and ``allow`` wins ties;
* ``*`` matches any sequence, ``$`` anchors the end; ``/robots.txt`` is always allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote

MAX_ROBOTS_BYTES = 500 * 1024  # Google reads the first 500 KiB

# Product tokens we evaluate. Our own crawler obeys the "serptankbot" group (or "*").
GOOGLEBOT = "googlebot"
BINGBOT = "bingbot"
SERPTANKBOT = "serptankbot"


@dataclass(frozen=True)
class Rule:
    allow: bool
    pattern: str

    def matches(self, path: str) -> bool:
        return _compile(self.pattern).match(path) is not None


@dataclass
class Group:
    agents: list[str] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass
class RobotsTxt:
    groups: list[Group] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)
    # Yandex-only directives, reported as engine deltas.
    yandex_host: str | None = None
    clean_params: list[str] = field(default_factory=list)
    invalid_lines: int = 0

    def _group_for(self, agent: str) -> Group | None:
        """Merged group for ``agent`` (exact product token), else the ``*`` group."""
        agent = agent.lower()
        matching = [g for g in self.groups if agent in g.agents]
        if not matching:
            matching = [g for g in self.groups if "*" in g.agents]
        if not matching:
            return None
        merged = Group(agents=[agent])
        for group in matching:
            merged.rules.extend(group.rules)
            if merged.crawl_delay is None:
                merged.crawl_delay = group.crawl_delay
        return merged

    def is_allowed(self, agent: str, path: str) -> bool:
        if path.split("?", 1)[0] == "/robots.txt":
            return True
        group = self._group_for(agent)
        if group is None:
            return True
        decoded = _normalize_path(path)
        best: Rule | None = None
        for rule in group.rules:
            if not rule.pattern:
                continue  # "Disallow:" (empty) allows everything
            if rule.matches(decoded) and (
                best is None
                or len(rule.pattern) > len(best.pattern)
                or (len(rule.pattern) == len(best.pattern) and rule.allow and not best.allow)
            ):
                best = rule
        return best is None or best.allow

    def crawl_delay(self, agent: str) -> float | None:
        group = self._group_for(agent)
        return group.crawl_delay if group else None


def _normalize_path(path: str) -> str:
    # Compare percent-decoded forms so "/a%20b" and "/a b" match the same rule.
    return unquote(path) or "/"


_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _compile(pattern: str) -> re.Pattern[str]:
    cached = _PATTERN_CACHE.get(pattern)
    if cached is None:
        anchored = pattern.endswith("$")
        body = pattern[:-1] if anchored else pattern
        regex = ".*".join(re.escape(part) for part in _normalize_path(body).split("*"))
        cached = re.compile(regex + ("$" if anchored else ""), re.DOTALL)
        if len(_PATTERN_CACHE) < 10_000:  # noqa: PLR2004
            _PATTERN_CACHE[pattern] = cached
    return cached


def parse_robots(text: str) -> RobotsTxt:  # noqa: PLR0912 - one branch per directive
    robots = RobotsTxt()
    current: Group | None = None
    last_was_agent = False
    for raw_line in text[:MAX_ROBOTS_BYTES].splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        if not sep:
            robots.invalid_lines += 1
            continue
        key, value = key.strip().lower(), value.strip()
        if key in {"user-agent", "useragent"}:
            if current is None or not last_was_agent:
                current = Group()
                robots.groups.append(current)
            current.agents.append(value.lower().split("/", 1)[0].strip() or "*")
            last_was_agent = True
            continue
        last_was_agent = False
        if key == "sitemap":
            if value:
                robots.sitemaps.append(value)
        elif key == "host":
            robots.yandex_host = value or None
        elif key == "clean-param":
            robots.clean_params.append(value)
        elif current is None:
            robots.invalid_lines += 1  # rule outside any group
        elif key in {"allow", "disallow"}:
            current.rules.append(Rule(allow=key == "allow", pattern=value))
        elif key == "crawl-delay":
            try:
                current.crawl_delay = max(0.0, float(value))
            except ValueError:
                robots.invalid_lines += 1
        else:
            robots.invalid_lines += 1
    return robots


ALLOW_ALL = RobotsTxt()
# RFC 9309 §2.3.1.4: an unreachable robots.txt (5xx) means "assume complete disallow".
DISALLOW_ALL = RobotsTxt(groups=[Group(agents=["*"], rules=[Rule(allow=False, pattern="/")])])
