# AGENTS.md

## Setup

- Requires Python >= 3.11.
- Install the package with dev dependencies: `pip install -e ".[dev]"`
- There is no development container; install dependencies directly.

## Repository layout

- `src/fireflyConverter/` — main package: `cli.py`, `loadData.py`, `convertData.py`, `data.py`, `fireflyPayload.py`, `fireflyInterface.py`, and `__main__.py` (entry point for the `cash` command).
- `test/` — test suite in `test/testFireflyConverter/`, plus shared fixtures in `test/config/` and `test/data/`.
- `test/fireflyServer/` — docker-compose setup for a local Firefly III instance used by the integration tests.
- `examples/` — example `config.toml` and sample data; not a separate package.

## Development

The tests of the firefly interface (`testFireflyConverter/testFireflyInterface.py`) rely on a local Firefly III server. Unit tests for loading/conversion run offline.

### Full test suite (matches CI)

1. Start the Firefly III test server:

   ```bash
   cd test/fireflyServer
   docker compose up
   ```

2. Create the API token (requires `sudo`, writes `.env`):

   ```bash
   bash test/fireflyServer/createToken.sh
   ```

3. Run the tests:

   ```bash
   pytest --cov=fireflyConverter test/ --cov-report=html --cov-report=term
   ```

CI runs this same command on pull requests targeting `main` (`.github/workflows/test.yml`).

## Conventions

- Uses a `src/` layout; package config lives in `pyproject.toml`.
- Supported input sources: `barclays`, `paypal`, `trade_republic`, `common`.
- CLI subcommands: `cash convert` and `cash transfer` (parsers registered in `cli.py`).
- Follow existing patterns in `src/fireflyConverter/` when adding or modifying code.

## Commits and pull requests

- Follow conventional-commit style: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, ...
- Use the `gh` CLI for GitHub tasks (`gh pr create`, `gh pr edit`, `gh pr list`, etc.).
- Pull requests must follow the template in `.github/pull_request_template.md` (Changes, Relevant links, Reasoning, Explanation, Additional notes, and the Checklist).
- Keep the PR description as brief as possible, including only the information the reviewer needs to quickly grasp the changes.
- Squash-merge pull requests into `main`.
- The squash-merge commit message must be a conventional-commit message that describes the change for both developers and users - `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, followed by a concise summary. Release-please generates releases from these commits on `main` (`.github/workflows/release-please.yml`).