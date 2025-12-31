#!/usr/bin/env python3
"""
Script to automatically create a Firefly III personal access token for testing.
This script registers a user and creates an API token programmatically.
"""

import os
import re
import sys
import time
from typing import Optional

import requests


def waitForFirefly(base_url: str, timeout: int = 120) -> bool:
    """Wait for Firefly III server to be ready."""
    print("Waiting for Firefly III to be ready...")
    start_time = time.time()
    attempt = 0

    while time.time() - start_time < timeout:
        try:
            response = requests.get(base_url, timeout=5)
            if response.status_code in [200, 302]:
                print("Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        attempt += 1
        if attempt % 10 == 0:
            elapsed = int(time.time() - start_time)
            print(f"Waiting for server... ({elapsed}/{timeout}s)")
        time.sleep(2)

    return False


def extractCsrfToken(html_content: str) -> Optional[str]:
    """Extract CSRF token from HTML content."""
    # Try to find CSRF token in input field
    match = re.search(r'name="_token"\s+value="([^"]+)"', html_content)
    if match:
        return match.group(1)

    # Try meta tag
    match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html_content)
    if match:
        return match.group(1)

    return None


def registerUser(base_url: str, email: str, password: str, session: requests.Session) -> bool:
    """Register a new user (if registration is enabled)."""
    try:
        print("Attempting to register user...")

        # First, get the registration page to extract CSRF token
        reg_page = session.get(f"{base_url}/register", timeout=10)
        if reg_page.status_code != 200:
            print(f"Could not access registration page: {reg_page.status_code}")
            return False

        # Extract CSRF token from registration page
        csrf_token = extractCsrfToken(reg_page.text)
        if not csrf_token:
            print("Could not find CSRF token in registration page")
            return False

        # Now post with CSRF token
        response = session.post(
            f"{base_url}/register",
            data={
                "_token": csrf_token,
                "email": email,
                "password": password,
                "password_confirmation": password,
            },
            allow_redirects=True,
            timeout=10,
        )

        # Check if registration was successful
        if response.status_code == 200:
            print("Registration successful!")
            return True
        elif response.status_code == 302:
            print("Registration redirected (might be successful)")
            return True
        else:
            print(f"Registration failed with status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Registration failed (user might already exist): {e}")
        return False


def login(base_url: str, email: str, password: str) -> Optional[requests.Session]:
    """Login and get authenticated session."""
    print("Logging in...")
    session = requests.Session()

    try:
        # First, get the login page to get CSRF token
        login_page = session.get(f"{base_url}/login", timeout=10)

        # Extract CSRF token from login page
        csrf_token = extractCsrfToken(login_page.text)
        if not csrf_token:
            print("Could not find CSRF token in login page")
            return None

        # Attempt login with CSRF token
        response = session.post(
            f"{base_url}/login",
            data={
                "_token": csrf_token,
                "email": email,
                "password": password,
            },
            allow_redirects=True,
            timeout=10,
        )

        # Fail fast if the login POST itself failed
        if response.status_code not in (200, 302):
            print(f"Login failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

        # If we are sent back to the login page, credentials were rejected
        if "/login" in response.url and extractCsrfToken(response.text):
            print("Login rejected - still on login page after POST")
            return None

        # Check if we're logged in by trying to access profile
        # The app might still be initializing, so retry with backoff
        max_profile_attempts = 30
        for attempt in range(max_profile_attempts):
            try:
                profile = session.get(f"{base_url}/profile", timeout=10, allow_redirects=True)

                # If we get a 200 with profile content, we're definitely logged in
                if profile.status_code == 200 and "profile" in profile.text.lower():
                    print("Login successful!")
                    return session

                # If we got redirected back to login, credentials were rejected
                if "/login" in profile.url and profile.status_code == 200:
                    print("Login rejected - redirected back to login page")
                    return None

                # If we get a 500 error, app is still initializing
                if profile.status_code == 500:
                    if attempt < max_profile_attempts - 1:
                        print(f"Attempt {attempt + 1}/{max_profile_attempts}: App still initializing (500 error), retrying...")
                        time.sleep(2)
                        continue
                    else:
                        print("App still returning 500 errors after retries")
                        return None

                # Any other status code after a few retries, assume success
                if attempt > 5:
                    print("Login successful (assuming after retries)!")
                    return session

                if attempt < max_profile_attempts - 1:
                    print(f"Attempt {attempt + 1}/{max_profile_attempts}: Status {profile.status_code}, retrying...")
                    time.sleep(1)

            except requests.exceptions.RequestException as e:
                if attempt < max_profile_attempts - 1:
                    print(f"Attempt {attempt + 1}/{max_profile_attempts}: Profile access failed ({e}), retrying...")
                    time.sleep(2)
                else:
                    print(f"Profile access failed after {max_profile_attempts} attempts: {e}")
                    return None

        print("Login failed - could not access profile after retries")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Login error: {e}")
        return None


def getCsrfToken(session: requests.Session, base_url: str) -> Optional[str]:
    """Get CSRF token from profile page for OAuth token creation."""
    try:
        print("Getting CSRF token...")
        response = session.get(f"{base_url}/profile", timeout=10)

        csrf_token = extractCsrfToken(response.text)
        if not csrf_token:
            print("Could not find CSRF token in page")
            return None

        return csrf_token

    except requests.exceptions.RequestException as e:
        print(f"Error getting CSRF token: {e}")
        return None


def createToken(session: requests.Session, base_url: str, csrf_token: str) -> Optional[str]:
    """Create a personal access token."""
    try:
        print("Creating personal access token...")
        response = session.post(
            f"{base_url}/oauth/personal-access-tokens",
            headers={
                "Content-Type": "application/json",
                "X-CSRF-TOKEN": csrf_token,
                "Accept": "application/json",
            },
            json={"name": f"Test Token {int(time.time())}"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("accessToken")
            if token:
                return token

        print(f"Token creation failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Error creating token: {e}")
        return None


def main():
    """Main function to orchestrate token creation."""
    base_url = os.getenv("FIREFLY_URL", "http://localhost")
    email = os.getenv("FIREFLY_EMAIL", "test@example.com")
    password = os.getenv("FIREFLY_PASSWORD", "vC\}N}5p=#`9'J1b")

    print("=" * 50)
    print("Firefly III Token Setup")
    print("=" * 50)
    print(f"URL: {base_url}")
    print(f"Email: {email}")
    print("=" * 50)
    print()

    # Wait for server to be ready
    if not waitForFirefly(base_url):
        print("Error: Firefly III server did not become ready in time")
        sys.exit(1)

    # Create a persistent session for CSRF token management
    session = requests.Session()

    # Try to register (might fail if user exists, which is fine)
    registerUser(base_url, email, password, session)

    # Login
    session = login(base_url, email, password)
    if not session:
        print("\nError: Could not login. Please:")
        print(f"1. Register manually at {base_url}/register")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print("2. Then run this script again")
        sys.exit(1)

    # Get CSRF token
    csrf_token = getCsrfToken(session, base_url)
    if not csrf_token:
        print("Error: Could not get CSRF token")
        sys.exit(1)

    # Create token
    access_token = createToken(session, base_url, csrf_token)
    if not access_token:
        print("Error: Could not create access token")
        sys.exit(1)

    # Success!
    print()
    print("=" * 50)
    print("Access token created successfully!")
    print("=" * 50)
    print()
    print(f'export TEST_API_TOKEN="{access_token}"')
    print()
    print("To use this token, run:")
    print(f'  export TEST_API_TOKEN="{access_token}"')
    print()
    print("Or save it to a .env file in the repository root:")
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    print(f"  echo 'TEST_API_TOKEN=\"{access_token}\"' > {env_file}")
    print()

    # Optionally write to .env file
    if "--save" in sys.argv or "-s" in sys.argv:
        try:
            with open(env_file, "w") as f:
                f.write(f'TEST_API_TOKEN="{access_token}"\n')
            print(f"✓ Token saved to {env_file}")
        except Exception as e:
            print(f"Could not save to .env file: {e}")


if __name__ == "__main__":
    main()
