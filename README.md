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

For iPhone HEIC/HEIF photo support, install the optional extra:

```bash
pip install "firefly-cash-converter[heic]"
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
- `--apply_rules`: Let Firefly III run all of its rules on each transaction while it is imported. Cannot be combined with `--apply_rule_groups`.
- `--bills_directory`: Directory of bill documents to map onto the transferred transactions (see [Bill-aware enrichment](#bill-aware-enrichment))
- `--dry_run`: Enrich and report without transferring or archiving anything.
- `--verbose`: Include raw LLM responses in the bill enrichment report.

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

Bills (PDF invoices, receipts, scans or photos) dropped into a folder can be matched to imported transactions.
Accepted formats: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.heic`, `.heif`. When a transaction has a matching bill, a local OpenAI-compatible LLM reads the bill and sets the transaction's category, account, tags and notes.

Bills are matched to **withdrawal** transactions by exact amount, a date window and vendor similarity. A bill that matches no transaction, matches several, or cannot be read is skipped and listed in the report; the rest of the import continues. Transactions without a bill are transferred unchanged.

Categories, tags and bill counter-accounts must already exist in Firefly III. By default, only active expense accounts are offered; configure `account_types` to allow other Firefly account types. Extractions below the confidence threshold get neither category, account nor tags. A marker tag (`bill-matched` by default) and a note pointing at the source file are always written so the enrichment stays traceable.

After each matched transaction is created, every contributing bill is uploaded and attached to its Firefly III transaction. Image bills are converted to bounded JPEG upload copies; PDFs are uploaded unchanged, and the source files are not modified. If an attachment upload fails, the transfer stops before matched bills are archived.

Multiple bills may cover one transaction when their totals add up to the transaction amount. Each bill becomes a split entry with its own category, tags and note. The split limit is five bills by default; additional matches are reported as ambiguous.

For a single bill, the LLM may also split distinct bill positions into separate transaction entries when that gives a materially better match to the available categories or tags. It prefers the fewest entries possible and combines positions with the same suitable classification.

You can provide few-shot bill examples outside the settings file with `prompt_examples_directory`:

```toml
[bills]
prompt_examples_directory = "./bill-examples"
```

Create `positive/` and `negative/` subdirectories. Each `*.json` file must contain an `input` path (relative to its positive/negative directory) and a `response` object. Positive examples show the desired extraction; negative examples show an extraction pattern the model should avoid. The input may be a `.txt`/`.md` bill description, PDF, or supported image. All examples are included in every bill prompt.

The `response` object uses this format:

```json
{
  "total": 12.0,
  "currency": "EUR",
  "date": "2026-10-01",
  "vendor": "Example Market",
  "category": "Groceries",
  "account": null,
  "tags": ["business"],
  "note": "Example receipt",
  "confidence": 0.95,
  "splits": [
    {
      "amount": 7.0,
      "category": "Groceries",
      "tags": ["business"],
      "note": "Food",
      "confidence": 0.9
    }
  ]
}
```

`total`, `date`, `vendor`, `category`, `account`, `tags`, `note`, and `confidence` are required. `splits` is optional and may contain at most `max_split_bills` entries; each split has `amount`, `category`, `tags`, `note`, and `confidence`.

```json
{
  "input": "mixed-receipt.txt",
  "response": {
    "total": 12.0,
    "currency": "EUR",
    "date": "2026-10-01",
    "vendor": "Example Market",
    "category": "Groceries",
    "account": null,
    "tags": ["business"],
    "note": "Example receipt",
    "confidence": 0.95
  }
}
```

The counter-account is only filled when the transaction does not already carry one; an existing account is kept and the ignored suggestion is reported. Set `accounts = false` in the `[bills]` section to leave accounts untouched.

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
confidence_threshold = 0.5         # below this, category, account and tags are left empty
marker_tag = "bill-matched"        # audit tag written onto enriched transactions
move_processed = true              # archive applied bills after a run
processed_subdir = "processed"     # subfolder applied bills are moved into
report_path = "./bills-report.md"  # where the Markdown report is written
vision = true                      # allow sending bills to the vision model
# HEIC/HEIF photos (iPhone) are transcoded to JPEG locally; requires:
# pip install "firefly-cash-converter[heic]"
max_pages = 1                      # PDF pages considered for text extraction
render_resolution = 1600           # maximum pixels on the longest image side
accounts = true                    # let bills also set the counter-account
account_types = ["expense"]        # existing Firefly account types offered to bills
max_split_bills = 5                # maximum bills contributing to one transaction

[llm]
base_url = "http://127.0.0.1:1234/v1"
model = "your-local-model"
timeout_s = 120
```

### Rules and bills

`--apply_rules` makes Firefly III run all of its rules on each transaction while it is imported. Combined with bill enrichment, the rules are only applied to the transactions that no bill was matched to; the bill-matched transactions keep the category, account and tags read from their bill. Such rule-labelled transactions are tagged `auto_labeled`, so a single tag filter separates them from the `bill-matched` ones.

Firefly III applies *all* active rules at import and cannot be limited to a single rule group. Unlike `--apply_rule_groups`, `--apply_rules` only ever touches the transactions of the current run and never re-processes transactions that are already stored.

**Note:** bill-aware enrichment cannot be combined with `--apply_rule_groups`, which would overwrite the category and tags read from the bills; the command refuses the combination with an error. `--apply_rules` and `--apply_rule_groups` are mutually exclusive as well.

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
uv sync --dev

# Run all tests
uv run pytest --cov=fireflyConverter test/
```

**Note:** The `.env` file is automatically loaded by the test suite using `python-dotenv` (included in dev dependencies).
