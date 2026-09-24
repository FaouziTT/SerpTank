"""``python -m serptank`` prints the installed version (used as a container smoke test)."""

import sys

from serptank import __version__


def main() -> int:
    """Write the package version to stdout and exit successfully."""
    sys.stdout.write(f"serptank {__version__}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
