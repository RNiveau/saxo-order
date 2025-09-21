#!/usr/bin/env python
"""
Development server for the Saxo Order API.
Run with: poetry run python run_api.py [--prod]
"""

import os
import sys

import uvicorn


def main():
    """Main entry point for the API server."""
    # Check for --prod flag
    if "--prod" in sys.argv:
        os.environ["CONFIG_FILE"] = "prod_config.yml"
        print("Starting API with production configuration")
    else:
        os.environ.setdefault("CONFIG_FILE", "config.yml")
        print(f"Starting API with configuration: {os.environ['CONFIG_FILE']}")

    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
