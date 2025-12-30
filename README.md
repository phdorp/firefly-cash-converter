# Firefly Cash

## Usage

### Pytr

```bash
mkdir tmp
pytr export_transactions tmp/trade_republic.csv --store_credentials --format csv
cash transfer trade_republic --account_name <account_name>
```

## Tests

The tests of the firefly interface rely on a local firefly server.

### Setup Test Server

1. Start the Firefly III server:
```bash
cd ./test/fireflyServer
sudo docker compose up
```

2. Create an API token automatically:

**Option A: Using Python script (recommended)**
```bash
# Create token and save to .env file
python3 test/fireflyServer/setupToken.py --save

# Or just display the token
python3 test/fireflyServer/setupToken.py
```

**Option B: Manual setup**
Register an account at `http://localhost:80` and create a personal access token manually in the Profile section. Then store the token:

```bash
echo 'TEST_API_TOKEN="your-token-here"' > .env
```

The automated scripts use these default credentials:

- Email: `test@example.com`
- Password: `password123`

You can customize them with environment variables:

```bash
export FIREFLY_EMAIL="custom@example.com"
export FIREFLY_PASSWORD="custompass"
python3 test/fireflyServer/setupToken.py --save
```
