#!/usr/bin/env python3
"""Test if Saxo tokens are properly configured."""

import os


def check_token_setup():
    """Check if access tokens are properly configured."""

    # Check for access_token file
    if os.path.isfile("access_token"):
        with open("access_token", "r") as f:
            content = f.read().strip()
            lines = content.split("\n")

        if len(lines) >= 2 and lines[0] and lines[1]:
            print("✅ Token file exists and appears valid")
            print(f"   - Access token length: {len(lines[0])} chars")
            print(f"   - Refresh token length: {len(lines[1])} chars")
            return True
        else:
            print("❌ Token file exists but format is incorrect")
            print("   File should contain:")
            print("   Line 1: access_token")
            print("   Line 2: refresh_token")
            return False
    else:
        print("❌ No access_token file found")
        print("   Run: poetry run k-order auth --write y")
        return False


if __name__ == "__main__":
    if check_token_setup():
        print("\n✅ Tokens are configured. Backend will use real Saxo API.")
    else:
        print("\n⚠️  No tokens configured. Backend will use mock data.")
