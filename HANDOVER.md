# Handover — Cin7 Core Health Review

> Hand-off pack for whoever inherits this tool. It assumes the reader has never seen
> Finovate, this codebase, or the people involved. Every name, acronym, and internal
> term is spelled out the first time it appears. For the feature-level detail (endpoints,
> methods, sections, filter logic) read `README.md`; for the API client's method-by-method
> reference read `API_CLIENT_README.md`. This file is the map that ties those together.

> ## ⚠️ Read this first — ownership must be migrated to Finovate
> Two things about this tool are currently tied to **Milan de Kock's personal accounts**,
> not Finovate-owned ones, and **both must be migrated before this can be considered a
> safe Finovate asset**:
> 1. **The source code lives on Milan's PERSONAL GitHub:**
>    `github.com/MilanDeKock/cin7_core_health_review`. It must be moved to the Finovate
>    org (**FinovateSA**). If Milan's personal GitHub is closed or lost, Finovate loses
>    the code.
> 2. **If the app is deployed to a cloud host** (e.g. Streamlit Community Cloud), it is
>    almost certainly under **Milan's personal login** — this is **UNKNOWN / unconfirmed**
>    (see §6). Any such deployment must be moved to a Finovate-owned account/host.
>
> Until both are done, the **bus factor is 1** (§9): if Milan is unavailable, Finovate
> cannot reliably access, host, or maintain this tool.

---

## 1. What it is and why it exists

**Finovate** (a South African finance / accounting practice) has clients who run their
inventory in **Cin7 Core** (a cloud inventory-management system, formerly called **DEAR
Inventory**). As part of servicing those clients, Finovate periodically (monthly) reviews
the *health* of each client's Cin7 Core setup: are there sales orders that were fulfilled
but never invoiced? Purchase orders stuck un-received? Negative stock? Products with no
price? Customers missing an email?

This tool automates that review. It is a small **Streamlit** web app (Streamlit is a
Python framework for quick data dashboards) that:

1. connects to the **Cin7 Core API** using a chosen client's read-only credentials,
2. pulls the relevant transaction and master data,
3. computes status counts, anomalies, and data-quality issues, and
4. shows them in an interactive dashboard, with CSV download (and a partly-built PDF export).

It is **read-only** — it never changes anything in the client's Cin7 Core account. It
replaces what used to be a manual, CSV-driven review.

---

## 2. Who depends on it

- **Finovate's client-services / accounting staff** — the people who run the review each
  month and act on what it flags. They are the only users; there is no client-facing side.
- **Finovate's clients** — indirectly. The review surfaces issues in *their* Cin7 Core
  data (stuck orders, bad master data) that Finovate then helps them fix. Clients never
  touch the tool.
- **Upstream dependency:** the **Cin7 Core API** (`inventory.dearsystems.com`). If Cin7
  changes its API, statuses, or rate limits, this tool can break or drift.
- **There is no scheduler, webhook, or trigger.** Nothing runs automatically. A staff
  member opens the app and clicks **Load Data from Cin7** on demand.

If the tool stops working, nobody's payments or invoices break — the impact is that the
monthly health review reverts to being done manually.

---

## 3. Who's who

| Name / Term | What it is |
|---|---|
| **Finovate** | The company that owns this tool. SA finance / accounting practice. |
| **Milan de Kock** (`milan@finovate.co.za`) | Author and sole maintainer to date. Also the holder of the personal GitHub (and any personal hosting) this currently depends on. |
| **Cin7 Core** | Third-party cloud inventory-management SaaS the clients use. Formerly **DEAR Inventory**; the API still lives on the `dearsystems.com` domain. |
| **DEAR Inventory** | The old name for Cin7 Core. You'll see "dear" in the API URL and docs. |
| **Streamlit** | The Python web-app framework this tool is built on. Also the name of **Streamlit Community Cloud**, a free public hosting service for Streamlit apps — the suspected (unconfirmed) host. |
| **FinovateSA** | Finovate's GitHub organisation — where this repo *should* live. |

---

## 4. How it's connected and run (the 60-second mental model)

```
Finovate staff member                THIS APP (Streamlit)                 Cin7 Core API
opens the app, picks a client,   ─►  Cin7APIClient(client_number=n)   ─►  GET /saleList, /purchaseList,
month, and sections, clicks          sends per-client auth headers        /stockAdjustment, /product,
"Load Data from Cin7"                 (rate-limited to 60/min)         ◄─  /availabilityList, ... (paginated)
                                      data_processing.py computes
                                      counts + anomalies + hygiene
                                      dashboard shows Summary / Detailed /
                                      Anomalies / PDF / Export tabs; CSV download
```

- **Language / runtime:** Python (3.10+ recommended), a **Streamlit** app (`app.py`).
- **Entry point:** `streamlit run app.py` → browser UI at `http://localhost:8501`.
- **Auth to Cin7:** per-client **Account ID + API Application Key** sent as HTTP headers
  (see §"How it authenticates" below). No OAuth, no login screen on the app itself.
- **Runtime cost:** a full pull takes ~**2–3 minutes** because Cin7 caps the API at
  **60 calls/minute** and the client self-throttles.
- **State:** none persisted. Data lives only in the Streamlit session while the app is
  open; outputs are downloaded as CSV (or PDF, WIP).

### How it authenticates to Cin7 Core (names only — never record the values)

Authentication is **per client**. For each client the app needs three environment
variables, numbered by a client slot `n`:

| Env var | Becomes this Cin7 request header | Meaning |
|---|---|---|
| `CLIENT_<n>_ACCOUNT_ID` | `api-auth-accountid` | The client's Cin7 Core **Account ID** |
| `CLIENT_<n>_API_KEY` | `api-auth-applicationkey` | The client's Cin7 Core **API Application Key** |
| `CLIENT_<n>_NAME` | *(not sent — UI label only)* | Friendly name for the client |

So `CLIENT_1_*` is client 1, `CLIENT_2_*` is client 2, and so on. In the sidebar you pick
a **Client Number**, and the app loads that slot's credentials. **To onboard a new
client, a new person supplies that client's Cin7 Account ID and API Application Key** (get
them from the client's Cin7 Core under **Settings → Integrations → API**), adds them as
the next `CLIENT_<n>_*` set, and selects that number. Keys should be **read-only**.

> These credentials live in a `.env` file locally (git-ignored) or in the host's secrets
> store if deployed. **Never** commit them, print them, or paste values into any document.

---

## 5. How to run and deploy

**Run locally (all you need is the client credentials):**
```bash
pip install -r requirements.txt
# create a .env with at least CLIENT_1_NAME / CLIENT_1_ACCOUNT_ID / CLIENT_1_API_KEY
python test_api_client.py     # optional: sanity-check the connection
streamlit run app.py          # opens http://localhost:8501
```

**Deploy — UNKNOWN / not configured in the repo.** There is **no deployment
configuration in the codebase**: no `.streamlit/` folder, no `Procfile`, no Dockerfile,
no GitHub Actions workflow, no Azure/Heroku config. That means one of:
- it is **run locally only** on Milan's machine (most consistent with what's in the repo), or
- it was deployed **manually** to **Streamlit Community Cloud** (free public host for
  Streamlit apps) under **Milan's personal login**, with secrets pasted into that
  platform's UI rather than committed.

Which of these is true is **UNKNOWN — needs confirmation from Milan.** If it is on
Streamlit Community Cloud, note that platform pulls straight from a GitHub repo — today
that would be **Milan's personal repo**, reinforcing the migration need in §9.

---

## 6. Where it lives (so a new person can find and access it)

| Item | Value |
|---|---|
| Source code | `github.com/MilanDeKock/cin7_core_health_review` — **Milan's PERSONAL GitHub**, branch `main`. **Must move to the FinovateSA org.** |
| Deployed host | **UNKNOWN — needs confirmation from Milan.** No deploy config exists in the repo (no `.streamlit/`, Procfile, Dockerfile, or CI). Most likely **local-only**, or manually deployed to **Streamlit Community Cloud under Milan's personal login**. |
| Public URL | **UNKNOWN** — none found in the code. If on Streamlit Community Cloud it would be a `*.streamlit.app` URL held under Milan's account. |
| Secrets location | Locally: a git-ignored `.env`. If deployed on Streamlit Community Cloud: that app's **Secrets** settings (again under Milan's personal account). Never in the repo. |

**To get access today:** you would need access to **Milan's personal GitHub** for the
code, and — if it's deployed — **Milan's personal Streamlit Community Cloud account** for
the running app and its secrets. **This is exactly the problem §9 says to fix:** move the
repo to **FinovateSA** and re-deploy (if deployed at all) under a **Finovate-owned host
and account**, so access no longer depends on one person's personal logins.

---

## 7. Current state & known limitations

- **Status:** working internal tool. Core sections (Sales, Purchases, Stock Adjustments,
  Stock Takes, Transfers, Stock per Location) run and produce metrics + CSV export.
- **PDF export is work-in-progress.** The "Generate PDF" tab and `modules/pdf_generator.py`
  exist but the PDF path is not fully finished/verified. **CSV export is the reliable
  output.**
- **Some sections are off by default:** Assemblies & Production, Data Hygiene, and Credit
  Notes must be ticked in the sidebar to run.
- **Xero/QBO Sync Errors are manual.** That data is *not* in the Cin7 API, so the section
  only appears if a staff member uploads the XLSX export from Cin7 (Reports → Xero/QBO
  Synchronisation Report).
- **API vs Cin7-UI count differences are expected and were deliberately calibrated.** The
  API returns all records incl. old/archived; the UI is often date-filtered. Filter logic
  in `data_processing.py` was tuned to match the UI (see git history) — change it with care.
- **No automated tests or CI.** The `test_*.py` files are manual scripts. The
  `analyze_*`, `inspect_*`, `investigate_*` scripts are developer/calibration tools, not
  part of the app.
- **No hosting config** in the repo (see §5/§6).

---

## 8. If it breaks — first things to check

1. **`Authentication Failed (403)`** → the selected client's **Account ID / API Key** is
   wrong, expired, or revoked. Re-check in that client's Cin7 Core → Settings →
   Integrations → API, and confirm the matching `CLIENT_<n>_*` values in the environment.
   Quick isolation: `python test_api_client.py`.
2. **`Rate limit exceeded (429)`** → the client auto-retries; if it persists, wait a
   minute and re-run. Make sure only one pull is running.
3. **Counts look wrong / don't match the Cin7 UI** → usually the API returning archived
   records or a date-filter mismatch, not a bug. Run `python investigate_drafts.py` to see
   what the API is actually returning before changing any filter logic.
4. **App won't start** → `pip install -r requirements.txt`; if `streamlit` isn't found,
   run `python -m streamlit run app.py`.
5. **PDF errors** → known WIP area; fall back to CSV export.
6. **Whole thing is inaccessible** → you have hit the ownership problem: the code and any
   host may be behind Milan's personal accounts (§6, §9).

---

## 9. Bus-factor / ownership risks to close

1. **Migrate the repo to Finovate.** The code is on **Milan's personal GitHub**
   (`MilanDeKock/cin7_core_health_review`). Move it to the **FinovateSA** org so Finovate
   owns the source. **Highest priority.**
2. **Confirm and migrate the host.** Establish whether the app is deployed anywhere
   (likely **Streamlit Community Cloud under Milan's personal login**, or local-only —
   currently **UNKNOWN**). If deployed, re-create it under a **Finovate-owned account/host**
   and re-enter secrets there. If local-only, decide whether Finovate wants a proper
   Finovate-owned hosted instance.
3. **Sole maintainer is Milan.** No one else currently knows or can maintain this tool. A
   second Finovate person should get the repo, credentials, and a walkthrough.
4. **Client API keys are the sensitive asset.** They are per-client Cin7 Core read-only
   keys held in `.env` / host secrets. Ensure they are never committed, are stored in a
   Finovate-controlled place, and are rotated / removed when a client leaves. Confirm
   `.env` is untracked before any push.
5. **Upstream drift.** The tool depends on Cin7 Core's API semantics (statuses, filters,
   the legacy `dearsystems.com` endpoint). If Cin7 changes these, the review can silently
   drift — worth a periodic re-calibration check against the Cin7 UI.
