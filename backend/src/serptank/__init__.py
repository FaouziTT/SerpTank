"""SerpTank API and worker package.

Google-first SEO and AI-search visibility platform. The package is organised as a
modular monolith (see ``docs/adr/0001-architecture.md``):

* ``serptank.core``    - cross-cutting platform code (config, errors, db, security).
* ``serptank.modules`` - feature modules (identity, tenancy, crawler, rankings, ...).

``core`` must never import from ``modules``; this is enforced by import-linter.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("serptank")
except PackageNotFoundError:  # pragma: no cover - only when running from a raw checkout
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
