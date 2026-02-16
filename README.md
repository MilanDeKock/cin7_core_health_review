# Cin7 Core Health Check Automation

Automated health check report generation for Cin7 Core (formerly DEAR Inventory) clients using the Cin7 API.

**No CSV uploads required** – everything is pulled directly from the Cin7 Core API!

---

## 🎯 What It Does

This tool automatically:
1. ✅ Connects to Cin7 Core API with client credentials
2. ✅ Pulls all transaction data (sales, purchases, stock, transfers, etc.)
3. ✅ Analyzes data to identify issues and anomalies
4. ✅ Displays metrics in an interactive Streamlit dashboard
5. 🚧 Generates branded PDF reports (coming soon)

---

## 📋 Health Check Sections

| Section | What It Checks | Status |
|---------|---------------|--------|
| **Sales Orders** | Status counts, anomalies (fulfilled not invoiced, etc.) | ✅ Implemented |
| **Purchase Orders** | Status counts, anomalies (authorised not received, etc.) | ✅ Implemented |
| **Stock Adjustments** | Discrepancies by location, top adjustments IN/OUT | ✅ Implemented |
| **Stock Takes** | Discrepancies, cost impact per location | ✅ Implemented |
| **Transfers** | Status counts, oldest transfers | ✅ Implemented |
| **Assemblies & Production** | Status counts for assemblies and production orders | ✅ Implemented |
| **Stock per Location** | Stock levels, negative stock detection | ✅ Implemented |
| **Data Hygiene** | Products with no price/category, customer/supplier data quality | ✅ Implemented |
| **Credit Notes** | Sale and purchase credit note analysis | ✅ Implemented |
| **PDF Export** | Branded PDF report generation | 🚧 Coming in Phase 2 |

---

## 🚀 Quick Start

### 1. Install Python

Make sure Python 3.10+ is installed:
```bash
python --version
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Client Credentials

Edit `.env` file with your Cin7 Core API credentials:

```bash
# Client 1
CLIENT_1_NAME=OTT
CLIENT_1_ACCOUNT_ID=your-account-id-here
CLIENT_1_API_KEY=your-api-key-here

# Client 2
CLIENT_2_NAME=Another Client
CLIENT_2_ACCOUNT_ID=their-account-id
CLIENT_2_API_KEY=their-api-key
```

**Where to find credentials:**
1. Log into Cin7 Core
2. Go to **Settings** → **Integrations** → **API**
3. Copy your **Account ID** and **API Key**

### 4. Run the Streamlit App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📖 How to Use

### In the Streamlit App:

1. **Select Client** – Choose client number (1, 2, 3, etc.) from sidebar
2. **Choose Report Period** – Select month and year
3. **Select Sections** – Check which sections to include in the health check
4. **Click "Load Data from Cin7"** – The app will:
   - Connect to Cin7 API
   - Pull all data (takes 2-3 minutes due to rate limiting)
   - Process metrics
   - Display results

5. **Review Results** – Use the tabs to explore:
   - 📊 **Summary** – High-level metrics at a glance
   - 📋 **Detailed Metrics** – Full breakdown per section
   - 🔍 **Anomalies** – Issues that need attention
   - 📄 **Generate PDF** – Export report (coming soon)

---

## 🗂️ Project Structure

```
cin7_core_health_review/
├── .env                    # API credentials (DO NOT commit to Git!)
├── .gitignore             # Excludes .env from version control
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # This file
│
├── modules/
│   ├── api_client.py      # Cin7 API wrapper (pagination, rate limiting)
│   ├── data_processing.py # Metrics calculation and analysis
│   ├── pdf_generator.py   # PDF report generation (placeholder)
│   └── ui_filters.py      # Date filtering helpers (optional)
│
└── test files/
    ├── test_api_client.py       # Basic API connection tests
    ├── test_with_ui_filters.py  # Test with date filters
    └── investigate_drafts.py    # Debug tool for draft order counts
```

---

## 🛠️ Development Workflow

### Testing API Connection

Before running the full app, test your API credentials:

```bash
python test_api_client.py
```

This will verify:
- ✅ API credentials are correct
- ✅ You can connect to Cin7 Core
- ✅ Basic data retrieval works

### Investigating Discrepancies

If counts don't match the Cin7 UI:

```bash
python investigate_drafts.py
```

This shows all draft POs with dates, helping you understand why the API might return more records than the UI shows (usually due to old/archived orders).

---

## 📊 API Coverage

**Fully automated (no CSV needed):**
- ✅ Sales Orders (all statuses, anomalies)
- ✅ Purchase Orders (all statuses, anomalies)
- ✅ Stock Adjustments (with line-level detail)
- ✅ Stock Takes (with discrepancies)
- ✅ Transfers (all statuses)
- ✅ Assemblies & Production Orders
- ✅ Stock Availability per Location
- ✅ Product Master Data
- ✅ Customer & Supplier Data
- ✅ Credit Notes

**Not available via API:**
- ❌ Xero/QBO Sync Errors (would need CSV export or screen scrape)

---

## ⚙️ Configuration Options

### Date Filtering (Optional)

By default, the app shows **all data** (including old/archived records) for full transparency.

If you want to filter by date to match the Cin7 UI:

```python
from modules.ui_filters import UIFilters

filters = UIFilters()

# Get only recent orders
purchases = client.get_purchase_list(
    order_status="DRAFT",
    modified_since=filters.last_90_days  # Only last 90 days
)
```

Available filters:
- `filters.last_30_days`
- `filters.last_60_days`
- `filters.last_90_days`
- `filters.current_month`
- `filters.last_365_days`

---

## 🔒 Security

**IMPORTANT:**
- ✅ `.env` file is in `.gitignore` – it won't be committed to Git
- ✅ Never share your `.env` file or API credentials
- ✅ API credentials have read-only access (cannot modify data)

---

## 📈 Performance

- **Rate Limit:** 60 API calls per minute (enforced automatically)
- **Typical Runtime:** 2-3 minutes for a full health check
- **Data Volume:** Handles 1000s of transactions with pagination

---

## 🚧 Roadmap

### Phase 1 (✅ Complete)
- ✅ API client with all health check endpoints
- ✅ Data processing for all sections
- ✅ Streamlit UI with interactive dashboard

### Phase 2 (Next)
- 🚧 PDF generation (branded reports matching Finovate style)
- 🚧 Historical tracking (compare month-over-month)
- 🚧 RAG health score (Red/Amber/Green status per section)

### Phase 3 (Future)
- 🚧 Scheduled monthly runs with email delivery
- 🚧 Multi-client dashboard (compare across clients)
- 🚧 Anomaly alerts and recommendations

---

## 🐛 Troubleshooting

### "Authentication Failed (403)"
- Check your Account ID and API Key in `.env`
- Verify credentials in Cin7 Core: Settings → Integrations → API

### "Rate limit exceeded (429)"
- The client automatically retries
- If persistent, wait a few minutes and try again

### "ModuleNotFoundError"
- Run: `pip install -r requirements.txt`

### Counts don't match Cin7 UI
- The API returns **all records** (including old/archived)
- The UI may have date filters active
- Run `python investigate_drafts.py` to see what the API is returning

### Streamlit command not found
- Make sure streamlit is installed: `pip install streamlit`
- Try: `python -m streamlit run app.py`

---

## 📚 Documentation

- [API_CLIENT_README.md](API_CLIENT_README.md) – Detailed API client documentation
- [Cin7 API Docs](https://dearinventory.docs.apiary.io/) – Official Cin7 Core API reference

---

## 📝 License

Internal tool for Finovate. Not for public distribution.

---

## 🙋 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in the terminal
3. Test with `python test_api_client.py`
4. Contact the development team

---

**Built with ❤️ for Finovate clients**
