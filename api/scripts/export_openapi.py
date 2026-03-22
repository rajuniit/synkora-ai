#!/usr/bin/env python3
"""
Export OpenAPI schema from FastAPI application.

Usage:
    python scripts/export_openapi.py
    python scripts/export_openapi.py --output ../docs/static/openapi.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.app import app


def export_openapi(output_path: str = "openapi.json") -> None:
    """Export OpenAPI schema to JSON file."""
    openapi_schema = app.openapi()

    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "https://api.synkora.io",
            "description": "Production server",
        },
        {
            "url": "http://localhost:5001",
            "description": "Local development server",
        },
    ]

    # Write to file
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema exported to: {output.absolute()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema")
    parser.add_argument(
        "--output",
        "-o",
        default="openapi.json",
        help="Output file path (default: openapi.json)",
    )
    args = parser.parse_args()

    export_openapi(args.output)


if __name__ == "__main__":
    main()
