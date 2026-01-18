# Firefly Cash Converter

A Python tool for converting financial transaction data from various sources (Barclays, PayPal, Trade Republic, etc.) and transferring them to [Firefly III](https://www.firefly-iii.org/) personal finance manager.

## Prerequisites

- Python >= 3.11
- A running Firefly III instance (for the `transfer` command)

## Installation

Install directly from the GitHub repository:

```bash
pip install git+https://github.com/phdorp/gnucash-convert.git@main
```

or from [PyPI](https://pypi.org/project/firefly-cash-converter/)

```bash
pip install firefly-cash-converter
```

This will install the `cash` command-line tool for converting and transferring financial transactions.

## Configuration

For the `transfer` command, you need a `config.toml` file with your Firefly III instance details. Create one based on this template:

```toml
[firefly_interface]
base_url = "http://your-firefly-instance"
api_token = "your-api-token-here"
duplicate_transaction = "ignore"  # options: "error", "ignore"
```

See the `examples/config.toml` file for reference.

## Usage

The tool provides two main commands: `convert` and `transfer`.

### Supported Sources

| Source | Convert | Transfer |
|--------|---------|----------|
| `barclays` | ✓ | ✓ |
| `paypal` | ✓ | ✓ |
| `trade_republic` | ✓ | ✓ |
| `common` | ✗ | ✓ |

### Convert

The `convert` command converts transaction data from various sources to a common CSV format compatible with Firefly III:

```bash
cash convert <source> <input_file> [options]
```

**Options:**

- `source`: Source format (choices: `barclays`, `paypal`, `trade_republic`)
- `input_file`: Path to the input file to be converted (without file extension)
- `--output`: Output directory (default: current directory)
- `--file_name`: Output file name without extension (default: `transactions`)
- `--account_name`: Name of the account to assign to transactions
- `--filter_query`: Optional pandas query to filter transactions (see [Filter Queries](#filter-queries))

**Example:**

Change directory to the `examples` directory.
The following command transforms the transactions stored in `tmp/trade_republic.csv` to the common Firefly representation.
Only transactions after the date `2025-07-01` are converted.

```bash
cash convert trade_republic tmp/trade_republic --account_name "My Trading Account" --filter_query "date >= '2025-07-01'"
```

### Transfer

The `transfer` command loads transaction data and directly transfers it to your Firefly III instance via API:

```bash
cash transfer <source> [options]
```

**Options:**

- `source`: Source format (choices: `barclays`, `paypal`, `trade_republic`, `common`)
- `--config_path`: Path to configuration file (default: `./config.toml`)
- `--account_name`: Name of the account to assign to transactions
- `--input_directory`: Directory containing input files (default: `tmp`)
- `--input_name`: Name of the input file (defaults to source name)
- `--filter_query`: Optional pandas query to filter transactions (see [Filter Queries](#filter-queries))
- `--apply_rule_groups`: List of rule group titles to apply after transferring transactions.

**Example with manual file:**

Change directory to the `examples` directory and launch your Firefly server.
Adapt the file `config.toml` to your needs.
The following command transfers transactions after the date `2025-07-01` to your Firefly server:

```bash
cash transfer trade_republic --account_name "My Trading Account" --filter_query "date >= '2025-07-01'"
```

**Example with Pytr (Trade Republic):**

If you own a Trade Republic account, you can download your transaction data with the [pytr](https://github.com/pytr-org/pytr) package:

```bash
pip install pytr
```

The following command enables an almost automated transfer of your transaction data (2FA code must be entered manually):

```bash
pytr export_transactions tmp/trade_republic.csv --store_credentials --format csv
cash transfer trade_republic --account_name "My Trading Account"
```

### Filter Queries

The `--filter_query` option accepts pandas query expressions for filtering transactions. Common examples:

- Filter by date: `"date >= '2025-07-01'"`
- Date range: `"date >= '2025-01-01' and date <= '2025-12-31'"`
- Amount filters: `"amount > 100"` or `"amount < 0"` (negative for expenses)
- Combine conditions: `"date >= '2025-01-01' and amount > 50"`

For more complex queries, refer to the [pandas query documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html).

## Tests

The tests of the firefly interface rely on a local Firefly III server.

### 1. Start the Test Server

Launch the Firefly III server using Docker Compose:

```bash
cd ./test/fireflyServer
sudo docker compose up
```

Wait for the server to be ready (this may take a minute on first run).

### 2. Create an API Token

Run the token creation script:

```bash
bash test/fireflyServer/createToken.sh
```

This script initializes Laravel Passport, creates a test user with owner permissions (user_role_id = 21), generates a personal access token, and saves it to the `.env` file.

### 3. Run Tests

Once the test server is running and the API token is configured in the `.env` file, install the package with dev dependencies and run the tests:

```bash
# Install package with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest --cov=fireflyConverter test/
```

**Note:** The `.env` file is automatically loaded by the test suite using `python-dotenv` (included in dev dependencies).
