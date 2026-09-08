# Cin7 Core Health Review

Technical reference for the **Cin7 Core Health Review** tool — an internal Finovate
utility that connects to the **Cin7 Core API** and produces a "health review" of a
client's Cin7 Core setup (sales-order and purchase-order metrics, stock checks, and
data-quality checks). It is a **Streamlit** app that runs on demand and shows the
results in an interactive dashboard, with CSV export and (partially built) PDF export.

> New to this tool and this practice? Read **`HANDOVER.md`** first — it explains what
> the tool is, who depends on it, where it lives, and the ownership risks that must be
> closed. This file is the feature-level reference for someone who already has the
> context and wants to run, extend, or debug the code.

**No CSV uploads required for the core review** — everything is pulled directly from the
Cin7 Core API. (One optional section, Xero/QBO Sync Errors, does take a manual XLSX
export because that data is not exposed by the API.)

---

## What it is

- **Cin7 Core** (formerly **DEAR Inventory**) is a cloud inventory-management system.
  Its API base URL is still on the legacy `dearsystems.com` domain
  (`https://inventory.dearsystems.com/ExternalApi/v2`).
- **Finovate** is a South African finance / accounting practice. This tool is used
  internally by Finovate to review the state of a client's Cin7 Core account —
  spotting stuck orders, un-invoiced fulfilments, negative stock, missing master
  data, and similar issues — as part of a periodic (monthly) client health review.
- It is a **read-only** tool. The credentials it uses are read-only API keys; it never
  writes back to Cin7 Core.

---

## What it does

1. Connects to the Cin7 Core API using a selected client's credentials.
2. Pulls transaction and master data (sales, purchases, stock adjustments, stock takes,
   transfers, assemblies/production, stock availability, products, customers, suppliers,
   credit notes).
3. Analyses the data to compute status counts and flag anomalies / data-quality issues.
4. Displays everything in an interactive Streamlit dashboard (Summary, Detailed Metrics,
   Anomalies, Generate PDF, Export Data tabs).
5. Lets the user download the underlying tables as CSV. PDF export exists but is
   **not fully finished** — see *Current state* below.

### Review sections

| Section | What it checks |
|---|---|
| **Sales Orders** | Status counts; anomalies (authorised prior-period not fulfilled, fulfilled not invoiced, invoiced not fulfilled) |
| **Purchase Orders** | Status counts; anomalies (prior/current period not invoiced / not received, invoiced-not-received, received-not-invoiced) |
| **Stock Adjustments** | Adjustments in the reporting period, cost impact, by-location breakdown, top qty in/out |
| **Stock Takes** | Discrepancies and cost impact per location |
| **Transfers** | Active transfers only (DRAFT + IN TRANSIT) |
| **Assemblies & Production** | Status counts for assemblies and production orders (off by default) |
| **Stock per Location** | Stock levels per location, negative-stock detection |
| **Data Hygiene** | Sellable products with no price / no barcode; customers & suppliers missing email / phone / payment terms; customers on credit hold (off by default) |
| **Credit Notes** | Sale and purchase credit-note analysis (off by default) |
| **Xero/QBO Sync Errors** | **Optional, manual** — parsed from an uploaded XLSX export (not available via API) |

---

## How it authenticates to Cin7 Core

Authentication is **per client**, using two Cin7 Core credentials sent as HTTP headers
on every request:

| Header sent to Cin7 | Sourced from env var | Meaning |
|---|---|---|
| `api-auth-accountid` | `CLIENT_<n>_ACCOUNT_ID` | The client's Cin7 Core **Account ID** |
| `api-auth-applicationkey` | `CLIENT_<n>_API_KEY` | The client's Cin7 Core **API Application Key** |

A friendly label for each client is read from `CLIENT_<n>_NAME`.

- These are the standard Cin7 Core "External API" credentials. In Cin7 Core they are
  found under **Settings → Integrations → API** (Account ID + Application Key).
- **Multi-client by design.** Credentials are numbered `CLIENT_1_…`, `CLIENT_2_…`,
  `CLIENT_3_…` and so on. In the app you pick a **Client Number** in the sidebar and
  the client at that slot is loaded (`Cin7APIClient(client_number=n)` reads
  `CLIENT_<n>_ACCOUNT_ID` / `CLIENT_<n>_API_KEY` from the environment).
- There is **no OAuth, no login screen, no per-user auth** — whoever runs the app has
  the client keys that are present in the environment. Keys should be read-only.

> **Never commit the `.env` file or print key values.** `.env` is git-ignored. The names
> above are all you need to document; the values belong only in the runtime environment.

### To add a new client

Add three more variables to the environment, incrementing the number:

```
CLIENT_4_NAME=<friendly client name>
CLIENT_4_ACCOUNT_ID=<the client's Cin7 Core Account ID>
CLIENT_4_API_KEY=<the client's Cin7 Core API Application Key>
```

Then select **Client Number 4** in the sidebar.

---

## Quick start (local)

```bash
# 1. Python 3.10+ recommended
python --version

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create a .env file (see "How it authenticates" above) with at least CLIENT_1_*

# 4. (Optional) sanity-check the API connection for client 1
python test_api_client.py

# 5. Run the app
streamlit run app.py
# opens at http://localhost:8501
```

In the app: pick a **Client Number**, choose the **report month/year**, tick the
**sections** to include, optionally upload the Sync Error XLSX, then click
**Load Data from Cin7**. A full pull takes roughly **2–3 minutes** because of API rate
limiting.

---

## Project structure

```
cin7_core_health_review/
├── .env                     # Per-client Cin7 credentials (GIT-IGNORED, never commit)
├── .gitignore               # Ignores .env, outputs/, *.pdf, caches, .claude/
├── app.py                   # Streamlit UI + orchestration of the data pull
├── requirements.txt         # Python dependencies
├── README.md                # This file (technical reference)
├── HANDOVER.md              # Stranger-facing hand-off pack (read this first)
│
├── modules/
│   ├── api_client.py        # Cin7APIClient: auth, rate limiting, pagination, retries
│   ├── data_processing.py   # All metric/anomaly calculations per section
│   ├── pdf_generator.py     # PDF report generation (xhtml2pdf) — WIP
│   └── ui_filters.py        # Date-range filter helpers (optional)
│
├── analyze_api_fields.py    # Dev tool: dumps unique values of key fields per endpoint
├── analyze_status_combos.py # Dev tool: exports every unique status-field combination
├── inspect_endpoint.py      # Dev tool: prints raw sample records for one endpoint
├── investigate_drafts.py    # Dev tool: explains API vs UI draft-PO count differences
├── test_api_client.py       # Basic API connection test
├── test_filter.py           # Filter experiments
├── test_stock_adjustment.py # Stock-adjustment endpoint experiments
├── test_with_ui_filters.py  # Test pulls with date filters
└── outputs/                 # Generated CSVs from the dev/analysis scripts (git-ignored)
```

The `analyze_*`, `inspect_*`, `investigate_*` and `test_*` scripts are **developer /
calibration tools**, not part of the running app. They exist because a lot of the work
was reconciling API results against what the Cin7 Core UI shows (draft/archived orders,
status-field semantics). They are safe to keep for future calibration but are not needed
to run the review.

---

## The API client (`modules/api_client.py`)

`Cin7APIClient` wraps the Cin7 Core External API v2. Key behaviours:

- **Base URL:** `https://inventory.dearsystems.com/ExternalApi/v2`
- **Auth:** the two `api-auth-*` headers described above, per client.
- **Rate limiting:** Cin7 Core allows **60 calls/minute**. The client self-throttles to
  ~1 call/second (`RATE_LIMIT_DELAY = 1.0`).
- **Retries:** transient errors (429, 500, 503, network) are retried up to `MAX_RETRIES`
  (3) with a delay. 400/403/404 are raised as `Cin7APIError`.
- **Pagination:** list endpoints are auto-paginated until all records are retrieved.
- **Helpers:** convenience methods for status counts and each health-check section (see
  **`API_CLIENT_README.md`** for the full method reference).

`API_CLIENT_README.md` is the detailed method-by-method reference for this client.

---

## Configuration / environment variables

Only the per-client Cin7 credentials are required. Names only (values never committed):

| Variable | Required | Purpose |
|---|---|---|
| `CLIENT_<n>_NAME` | recommended | Friendly label for client slot `n` |
| `CLIENT_<n>_ACCOUNT_ID` | **yes** | Client `n` Cin7 Core Account ID (`api-auth-accountid`) |
| `CLIENT_<n>_API_KEY` | **yes** | Client `n` Cin7 Core API Application Key (`api-auth-applicationkey`) |

`n` starts at 1 and increments per client. The sidebar allows client numbers 1–10.

---

## Current state & known limitations

- **PDF export is work-in-progress.** The UI has a "Generate PDF" tab and
  `modules/pdf_generator.py` exists (xhtml2pdf), but this path is not fully finished /
  verified. Treat CSV export as the reliable output.
- **Assemblies, Data Hygiene, and Credit Notes are off by default** in the sidebar; tick
  them to include them.
- **Sync Errors are manual.** Xero/QBO sync errors are not in the Cin7 Core API, so that
  section only appears if you upload the XLSX export from Cin7 (Reports → Xero/QBO
  Synchronisation Report). The parser skips the first 6 header rows (`header=6`).
- **API vs UI count differences are expected.** The API returns all records (including
  old/archived); the Cin7 UI often has date filters. `investigate_drafts.py` exists to
  explain the difference. Several commits ("Fix SO and PO metric filters to match Cin7
  UI", "Calibrate PO anomaly filters") were specifically to reconcile these — be careful
  changing the filter logic in `data_processing.py`.
- Leftover `modules/data_processing.py.tmp.*` files are editor temp files and can be
  deleted; the live module is `modules/data_processing.py`.
- **No automated tests / CI.** The `test_*.py` files are manual scripts, not a suite.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Authentication Failed (403)` | Wrong/expired Account ID or API Key for that client. Re-check in Cin7 Core → Settings → Integrations → API. |
| `Rate limit exceeded (429)` | The client auto-retries; if persistent, wait and re-run. Ensure a single client instance. |
| `ModuleNotFoundError` | `pip install -r requirements.txt`. |
| Counts don't match the Cin7 UI | The API returns all records incl. archived; the UI may be date-filtered. Run `python investigate_drafts.py`. |
| `streamlit: command not found` | `pip install streamlit`, or run `python -m streamlit run app.py`. |

---

## Security

- API credentials are **read-only** and must stay in `.env` (git-ignored) or the host's
  secret store — never in code, never committed, never printed.
- `.env` is listed in `.gitignore`; confirm it is untracked before any push.
- See `HANDOVER.md` for the ownership / migration risks (personal GitHub account, and
  any personal hosting account).

---

## Further reading

- **`HANDOVER.md`** — hand-off pack (what it is, who depends on it, where it lives, risks).
- **`API_CLIENT_README.md`** — full `Cin7APIClient` method reference and response shapes.
- [Cin7 Core (DEAR) API docs](https://dearinventory.docs.apiary.io/) — official reference.

---

*Internal tool for Finovate. Not for public distribution.*
