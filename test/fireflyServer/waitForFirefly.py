#!/usr/bin/env python3
"""Wait for Firefly III to be ready before running tests."""
import requests
import time
import sys

max_attempts = 120  # 2 minutes timeout
for attempt in range(max_attempts):
    try:
        response = requests.get('http://127.0.0.1/login', timeout=5)
        if response.status_code == 200:
            print(f"✓ Firefly III is ready! (attempt {attempt+1})")
            sys.exit(0)
    except requests.exceptions.RequestException:
        if attempt % 10 == 0:
            print(f"Waiting for Firefly III... ({attempt+1}/{max_attempts})")
    time.sleep(1)

print("✗ Firefly III failed to start after 2 minutes")
sys.exit(1)
