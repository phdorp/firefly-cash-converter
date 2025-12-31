#!/bin/bash

# Script to initialize Firefly III Passport and create a test user with API token

set -e

echo "Initializing Laravel Passport..."
docker exec firefly_iii_core php artisan passport:keys --force
docker exec firefly_iii_core php artisan passport:client --personal --name="Test Client" --no-interaction

echo "Creating test user and generating API token..."
docker exec -i firefly_iii_core php < test/fireflyServer/createUserToken.php > /tmp/token_output.txt 2>&1
TOKEN=$(grep "^TOKEN=" /tmp/token_output.txt | cut -d= -f2 | tr -d '\n\r ')

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to create token"
    cat /tmp/token_output.txt
    exit 1
fi

# Save token - use GitHub Actions environment if available, otherwise local .env
if [ -n "$GITHUB_ENV" ]; then
    echo "TEST_API_TOKEN=$TOKEN" >> "$GITHUB_ENV"
    echo "✓ Token created successfully (saved to GitHub environment)"
else
    cd "$(dirname "$0")/../.."
    echo "TEST_API_TOKEN=$TOKEN" > .env
    echo "✓ Token created successfully and saved to .env"
fi
