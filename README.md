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

[bills]
directory = "./bills"
report_path = "./bills-report.md"

[llm]
base_url = "http://127.0.0.1:1234/v1"
model = "your-local-model"
```

The `[bills]` and `[llm]` sections are optional. Bill-aware enrichment is off until a bills directory is set, either with `--bills_directory` or as `directory` in `[bills]`; other `[bills]` settings alone do not change the transfer behaviour.

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
- `--bills_directory`: Directory of bill documents to map onto the transferred transactions (see [Bill-aware enrichment](#bill-aware-enrichment))
- `--dry_run`: Enrich and report without transferring or archiving anything.

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

### Bill-aware enrichment

Bills (PDF invoices, receipts, scans or photos) dropped into a folder can be matched one-to-one to imported transactions. When a transaction has a matching bill, a local OpenAI-compatible LLM reads the bill and sets the transaction's category, tags and notes.

Bills are matched to **withdrawal** transactions by exact amount, a date window and vendor similarity. A bill that matches no transaction, matches several, or cannot be read is skipped and listed in the report; the rest of the import continues. Transactions without a bill are transferred unchanged.

The category and every tag must already exist in Firefly III. The LLM is only offered the existing names; anything outside that set is dropped and reported. Extractions below the confidence threshold get neither category nor tags. A marker tag (`bill-matched` by default) and a note pointing at the source file are always written so the enrichment stays traceable.

You need a local model served over an OpenAI-compatible API (for example `llama-server` from llama.cpp). Scanned bills are sent to the model as images, so the model must support vision for photos; digital PDFs are read from their text layer.

```bash
cash transfer common --bills_directory ./bills --dry_run
```

Run with `--dry_run` first: it reads the bills, prints the enrichment and writes the report without transferring transactions or archiving bills. When the result looks right, drop `--dry_run`.

```toml
[bills]
directory = "./bills"              # folder with the bills; setting this enables enrichment
date_window_days = 14              # max day gap between bill and transaction dates
amount_tolerance = 0.0             # allowed difference between bill total and amount
vendor_threshold = 0.6             # minimum vendor similarity for a match
confidence_threshold = 0.5         # below this, category and tags are left empty
marker_tag = "bill-matched"        # audit tag written onto enriched transactions
move_processed = true              # archive applied bills after a run
processed_subdir = "processed"     # subfolder applied bills are moved into
report_path = "./bills-report.md"  # where the Markdown report is written
vision = true                      # allow sending bills to the vision model
max_pages = 1                      # PDF pages considered for text extraction

[llm]
base_url = "http://127.0.0.1:1234/v1"
model = "your-local-model"
timeout_s = 120
```

**Note:** do not combine bill-aware enrichment with `--apply_rule_groups`. The enrichment relies on the LLM output, and rule groups would overwrite the category and tags it writes.

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
