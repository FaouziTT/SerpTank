"""JSON-LD validation against Google's rich-result requirements.

Only properties Google marks *required* for a rich result produce a finding; we report
recommended properties separately at low severity. Types Google no longer shows as rich
results are flagged as informational. Microdata/RDFa are detected but not validated.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from serptank.modules.audit.models import Severity
from serptank.modules.audit.rules import Finding, rule
from serptank.modules.audit.site import Site

REF = "https://developers.google.com/search/docs/appearance/structured-data/search-gallery"

# type -> (required properties, recommended properties). "a|b" = at least one of.
REQUIREMENTS: dict[str, tuple[list[str], list[str]]] = {
    "Article": ([], ["headline", "image", "datePublished", "author"]),
    "NewsArticle": ([], ["headline", "image", "datePublished", "author"]),
    "BlogPosting": ([], ["headline", "image", "datePublished", "author"]),
    "Product": (["name", "offers|review|aggregateRating"], ["image", "description", "brand"]),
    "Offer": (["price|priceSpecification"], ["priceCurrency", "availability"]),
    "BreadcrumbList": (["itemListElement"], []),
    "FAQPage": (["mainEntity"], []),
    "Recipe": (["name", "image"], ["author", "datePublished", "recipeIngredient"]),
    "Event": (["name", "startDate", "location"], ["endDate", "image", "description"]),
    "JobPosting": (
        [
            "title",
            "description",
            "datePosted",
            "hiringOrganization",
            "jobLocation|applicantLocationRequirements",
        ],
        ["validThrough", "employmentType", "baseSalary"],
    ),
    "LocalBusiness": (["name", "address"], ["telephone", "openingHoursSpecification", "geo"]),
    "Organization": ([], ["name", "url", "logo"]),
    "VideoObject": (
        ["name", "thumbnailUrl", "uploadDate"],
        ["description", "duration", "contentUrl|embedUrl"],
    ),
    "Review": (["itemReviewed", "author", "reviewRating"], []),
    "AggregateRating": (["ratingValue", "ratingCount|reviewCount"], []),
    "SoftwareApplication": (
        ["name", "offers|aggregateRating|review"],
        ["applicationCategory", "operatingSystem"],
    ),
    "Course": (["name", "description"], ["provider"]),
}
DEPRECATED = {
    "HowTo": "HowTo rich results were removed from Google Search in 2023.",
    "FAQPage": "FAQ rich results only show for well-known government and health sites.",
}


def _types(node: dict[str, Any]) -> list[str]:
    raw = node.get("@type")
    values = raw if isinstance(raw, list) else [raw]
    return [str(v).rsplit("/", 1)[-1] for v in values if isinstance(v, str)]


def _nodes(value: Any, depth: int = 0) -> Iterator[dict[str, Any]]:
    """Every JSON-LD object (including @graph members and nested entities)."""
    if depth > 8:  # noqa: PLR2004
        return
    if isinstance(value, list):
        for item in value[:200]:
            yield from _nodes(item, depth + 1)
    elif isinstance(value, dict):
        if "@type" in value:
            yield value
        for key, child in value.items():
            if key != "@context" and isinstance(child, (dict, list)):
                yield from _nodes(child, depth + 1)


def _has(node: dict[str, Any], spec: str) -> bool:
    return any(node.get(name) not in (None, "", [], {}) for name in spec.split("|"))


def _breadcrumb_problems(node: dict[str, Any]) -> list[str]:
    items = node.get("itemListElement")
    if not isinstance(items, list) or not items:
        return ["itemListElement"]
    problems = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"itemListElement[{index}]")
            continue
        if "position" not in item:
            problems.append(f"itemListElement[{index}].position")
        if not (item.get("name") or isinstance(item.get("item"), dict)):
            problems.append(f"itemListElement[{index}].name")
        if index < len(items) - 1 and not item.get("item"):
            problems.append(f"itemListElement[{index}].item")
    return problems


def _analyse(
    page_json_ld: list[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    required: list[dict[str, Any]] = []
    recommended: list[dict[str, Any]] = []
    types: set[str] = set()
    for node in _nodes(page_json_ld):
        for type_name in _types(node):
            types.add(type_name)
            spec = REQUIREMENTS.get(type_name)
            if spec is None:
                continue
            missing = [p for p in spec[0] if not _has(node, p)]
            if type_name == "BreadcrumbList" and not missing:
                missing = _breadcrumb_problems(node)
            if missing:
                required.append({"type": type_name, "missing": missing})
            soft = [p for p in spec[1] if not _has(node, p)]
            if soft:
                recommended.append({"type": type_name, "missing": soft})
    return required, recommended, types


@rule(
    "structured_data_invalid_json",
    title="Structured data that isn't valid JSON",
    category="structured_data",
    severity=Severity.MEDIUM,
    description="Google ignores JSON-LD blocks that fail to parse.",
    fix="Fix the JSON syntax (validate with the Rich Results Test).",
    effort=1,
    reference=REF,
)
def invalid_json(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        errors = int(page.data.get("json_ld_errors") or 0)
        if errors:
            yield Finding(page.url, {"blocks": errors})


@rule(
    "structured_data_missing_required",
    title="Structured data missing required properties",
    category="structured_data",
    severity=Severity.HIGH,
    description="These items lack properties Google requires, so they aren't eligible for "
    "rich results.",
    fix="Add the listed properties, then re-test with the Rich Results Test.",
    reference=REF,
)
def missing_required(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        required, _, _ = _analyse(page.data.get("json_ld") or [])
        if required:
            yield Finding(page.url, {"items": required[:10]})


@rule(
    "structured_data_missing_recommended",
    title="Structured data missing recommended properties",
    category="structured_data",
    severity=Severity.LOW,
    description="Recommended properties make rich results more complete and more likely to show.",
    fix="Add the listed recommended properties where the information exists.",
    effort=1,
    reference=REF,
)
def missing_recommended(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        _, recommended, _ = _analyse(page.data.get("json_ld") or [])
        if recommended:
            yield Finding(page.url, {"items": recommended[:10]})


@rule(
    "structured_data_limited_types",
    title="Structured data types with limited or no rich results",
    category="structured_data",
    severity=Severity.INFO,
    description="Some schema types no longer produce rich results in Google for most sites.",
    fix="Keep the markup if it's accurate, but don't expect rich results from it.",
    effort=1,
    reference=REF,
)
def limited_types(site: Site) -> Iterator[Finding]:
    for page in site.html_pages:
        _, _, types = _analyse(page.data.get("json_ld") or [])
        notes = {t: DEPRECATED[t] for t in types if t in DEPRECATED}
        if notes:
            yield Finding(page.url, {"types": notes})
