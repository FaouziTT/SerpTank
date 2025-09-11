#!/usr/bin/env python3
"""
Generate OpenAPI schema from FastAPI application.

This script extracts the OpenAPI schema from the FastAPI app
and saves it as a JSON file for frontend type generation.
"""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


def generate_openapi_schema():
    """Generate and save OpenAPI schema."""
    # Get OpenAPI schema
    openapi_schema = app.openapi()
    
    # Save to file
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "openapi.json"
    )
    
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"OpenAPI schema saved to: {output_path}")
    
    # Print summary
    paths = openapi_schema.get("paths", {})
    print(f"\nTotal endpoints: {len(paths)}")
    
    # Group by prefix
    endpoints_by_prefix = {}
    for path in paths:
        prefix = path.split("/")[3] if len(path.split("/")) > 3 else "root"
        if prefix not in endpoints_by_prefix:
            endpoints_by_prefix[prefix] = []
        endpoints_by_prefix[prefix].append(path)
    
    print("\nEndpoints by module:")
    for prefix, endpoints in sorted(endpoints_by_prefix.items()):
        print(f"  {prefix}: {len(endpoints)} endpoints")


if __name__ == "__main__":
    generate_openapi_schema()