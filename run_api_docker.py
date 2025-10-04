#!/usr/bin/env python
"""
Docker server for the Saxo Order API.
Run with: python run_api_docker.py
"""

import os

import uvicorn


def main():
    """Main entry point for the API server in Docker."""
    os.environ.setdefault("CONFIG_FILE", "config.yml")
    print(f"Starting API with configuration: {os.environ['CONFIG_FILE']}")

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",  # Bind to all interfaces for Docker
        port=8000,
        reload=False,  # Disable reload in Docker
        log_level="info",
    )


if __name__ == "__main__":
    main()
