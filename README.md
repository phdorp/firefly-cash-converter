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
Setup the server by invoking in the repository root:

```bash
cd ./test/fireflyServer
sudo docker compose up
```

Register an account at `http://localhost:80` and create a personal access token.
Store the token in the environment variable `API_TOKEN`, e.g., by copying the token string to a `.env` file in the repository root.
