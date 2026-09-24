"""Export the OpenAPI schema (``python -m serptank.openapi_export > openapi.json``).

The frontend generates its typed API client from this file; CI fails if the committed
copy drifts from the backend (see .github/workflows/ci.yml).
"""

from __future__ import annotations

import json
import sys

from serptank.core.config import Environment, Settings
from serptank.main import create_app


def main() -> int:
    app = create_app(Settings(environment=Environment.TEST, log_json=True))
    sys.stdout.write(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
