# Finances Tracker

A Python tool for tracking accounts, scheduled income and expenses, assets, and debts. It computes key numbers (liquid total, projected change to end of month, non-liquid net) and shows current status from a YAML data file.

See [DESIGN.md](DESIGN.md) for goals, concepts, and business rules.

## Project Structure

```text
├── data/                   # Finances YAML files
│   └── finances.yaml       # Your data
├── web/                    # Flask web app (view + inline edit for accounts)
│   ├── app.py              # Routes and Jinja filters; POST endpoints for accounts add/edit/delete
│   └── templates/          # Base, status, accounts (View/Edit), budget, assets
├── finances/               # Shared package (loader, calculations, filters, formatting, tables, writer, cli)
│   ├── __init__.py         # Re-exports for CLI and web
│   ├── types.py            # TypedDict definitions for entities
│   ├── loader.py
│   ├── writer.py           # Generic CRUD operations with validation
│   ├── calculations.py
│   ├── filters.py
│   ├── formatting.py
│   ├── tables.py
│   └── cli.py              # CLI commands and main()
├── tests/
│   ├── test_finances.py    # Unit tests for calculations and loader
│   └── test_writer.py      # Tests for writer operations
├── finances.py             # CLI entrypoint (runs finances.cli.main)
├── validate_yaml.py        # Validates data/*.yaml against schema
├── schema.yaml             # YAML schema (accounts, income, expenses, assets, debts)
├── pyproject.toml          # Project metadata and dependencies
└── mise.toml               # mise task runner configuration
```

## Prerequisites

- [mise](https://mise.jdx.dev/) - Task runner (also installs uv)

## Setup

```bash
# Install mise if you haven't already
# See https://mise.jdx.dev/getting-started.html

# Install tools and dependencies
mise install
mise run setup
```

## Development

```bash
# Run tests with coverage
mise run test

# Format code
mise run format

# Lint
mise run lint
mise run lint-fix          # auto-fix lint issues

# Validate YAML files
mise run validate

# Run all CI checks (format, lint, validate, test)
mise run ci
```

## Usage

There are two ways to interact with the system: a **web GUI** (recommended for mobile) and a **CLI**.

### Web GUI

The web interface provides a mobile-friendly dashboard for viewing status and editing data.

```bash
# Start the web server
mise run serve

# The app will be available at:
# - http://localhost:5001 (on your computer)
# - http://<your-ip>:5001 (from your phone on the same network)
```

To find your computer's IP address for mobile access:
```bash
# macOS
ipconfig getifaddr en0

# Linux
hostname -I | awk '{print $1}'
```

**Features:**
- Status dashboard showing accounts, budget, and assets
- Accounts page with inline editing (click cell to edit, save on blur/Enter)
- Add new accounts via empty row at bottom
- Per-row delete with inline confirmation
- Uses HTMX for dynamic updates without page reloads

Data file: set `FINANCES_DATA` to a path to your YAML file, or the app uses `data/finances.yaml` by default.

### CLI

The `finances.py` CLI provides commands: `status`, `accounts`, `budget`, `income`, `expenses`, `assets`, and `debts`. Most support `add`, `edit <id>`, and `delete <id>` subcommands.

### View Status

```bash
uv run python finances.py <data-file> status
```

The status command prints a summary table with Accounts (liquid minus CC), Budget (prorated), Assets (non-liquid net), and Total. Key numbers:

- **(1)** Liquid total — sum of liquid account balances
- **(2)** Accounts total — liquid minus credit card debts (includes CC rewards balances where present)
- **(3)** Projected change to end of month (scheduled income − expenses in the period). Continuous monthly items (e.g. food, gas) are prorated by the proportion of the month remaining.
- **(4)** Expected end-of-month total (2 + 3)
- **(5)** Non-liquid net (paired assets and their debts)
- **(6)** Non-liquid net (total)

### Sorting and ID/Index Display

All list commands support sorting and displaying IDs/indexes:

```bash
# Sort accounts by name
uv run python finances.py data/finances.yaml accounts --sort name

# Sort budget by amount (descending)
uv run python finances.py data/finances.yaml budget --sort amount --sort-dir desc

# Show IDs (for accounts) or indexes (for income/expenses/assets/debts)
uv run python finances.py data/finances.yaml accounts --show-id
uv run python finances.py data/finances.yaml income --show-id

# Combine sorting and ID display
uv run python finances.py data/finances.yaml expenses --sort amount --sort-dir desc --show-id
```

The `--show-id` flag displays the ID or index in the first column, which you can use with edit/delete commands:

- Accounts use auto-generated unique IDs
- Income, expenses, assets, and debts use 0-based array indexes

### Budget with Monthly/Annual Views

The `budget`, `income`, and `expenses` commands show both prorated subtotals and full budget amounts:

```bash
# Show budget with monthly amounts column
uv run python finances.py data/finances.yaml budget

# Show budget with annual amounts column
uv run python finances.py data/finances.yaml budget --annual

# Income/expenses also support --annual
uv run python finances.py data/finances.yaml income --annual
uv run python finances.py data/finances.yaml expenses --annual
```

This lets you see at a glance:

- **Subtotal**: What you'll earn/spend in the remainder of this month (prorated)
- **Monthly/Annual**: Your full monthly or annual budget for that item

For subcommand-specific help (e.g., add/edit/delete options), use:

```bash
uv run python finances.py data/finances.yaml accounts add -h
uv run python finances.py data/finances.yaml income edit -h
```

## Data File Format

Each finances file is a YAML document with five top-level arrays:

| Section       | Description |
|---------------|-------------|
| `accounts`    | Monetary balances (bank, credit card, cash, etc.). Each has `name`, `type`: `credit_card`, `checking`, `savings`, `gift_card`, `wallet`, `digital_wallet`, `loan`, `other`. Types map internally to liquid (for (1)/(2)), credit_card, or other. For credit_card: `limit` and `available`. For all others: `balance`. |
| `income`      | Scheduled income. Each has `description`, `amount`, `recurrence` (`one_time` \| `monthly` \| `biweekly` \| `quarterly` \| `semiannual` \| `annual`), plus recurrence-specific fields. Optional `continuous: true` for monthly items spent/earned over the month (prorated for (3)). |
| `expenses`    | Scheduled expenses. Same structure as income. Optional `type`: housing, insurance, service, utility, product, transport, food. |
| `assets`      | Non-liquid assets. Each has `name`, `value`, optional `source`. |
| `debts`| Debts (e.g. mortgage, car loan). Each has `name`, `balance`, optional `assetRef` (asset name), `interestRate`, `nextDueDate`. |

See `schema.yaml` for the full schema.
