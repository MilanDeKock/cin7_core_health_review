# Cin7 Core API Client Documentation

## Overview

The `Cin7APIClient` module provides a Python wrapper for the Cin7 Core (formerly DEAR Inventory) API with automatic rate limiting, pagination, error handling, and retry logic.

## Features

- ✅ **Multi-client support** - manage multiple clients with separate credentials
- ✅ **Automatic rate limiting** - enforces 60 calls/minute API limit
- ✅ **Automatic pagination** - fetches all records across multiple pages
- ✅ **Robust error handling** - retries transient errors, clear error messages
- ✅ **Health check helpers** - convenience methods for common queries
- ✅ **Comprehensive endpoint coverage** - all endpoints needed for health checks

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Credentials

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

**Where to find credentials in Cin7 Core:**
1. Log in to Cin7 Core
2. Go to Settings > Integrations > API
3. Copy your Account ID and API Key

### 3. Test Connection

```bash
python test_api_client.py
```

## Basic Usage

### Initialize Client

```python
from modules.api_client import Cin7APIClient

# Connect to Client 1
client = Cin7APIClient(client_number=1)

# Connect to Client 2
client = Cin7APIClient(client_number=2)
```

### Get Simple Counts

```python
# How many draft purchase orders?
draft_pos = client.get_status_count("/purchaseList", {"OrderStatus": "DRAFT"})
print(f"Draft POs: {draft_pos}")

# How many backordered sales?
backordered = client.get_status_count("/saleList", {"Status": "BACKORDERED"})
print(f"Backordered sales: {backordered}")
```

### Fetch Full Data (Paginated)

```python
# Get all authorised purchase orders
pos = client.get_purchase_list(order_status="AUTHORISED")
print(f"Found {len(pos)} authorised POs")

# Get all completed stock adjustments for January
adjustments = client.get_stock_adjustments(
    status="COMPLETED",
    modified_since="2024-01-01"
)
```

### Health Check Helper Methods

```python
# Get all sale status counts at once
sale_counts = client.get_sale_status_counts()
print(sale_counts)
# {
#   'draft_quotes': 5,
#   'authorised_quotes_no_so': 2,
#   'backordered': 12,
#   'awaiting_fulfilment': 45,
#   ...
# }

# Get all purchase status counts
purchase_counts = client.get_purchase_status_counts()

# Get assembly status counts
assembly_counts = client.get_assembly_status_counts()
```

## Available Methods

### Sales

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_sale_list(...)` | Get sale orders with filters | List of sales |
| `get_sale_detail(sale_id)` | Get detailed sale info | Sale dict |
| `get_sale_credit_notes()` | Get credit note list | List of credit notes |
| `get_sale_status_counts()` | All sale status counts | Dict of counts |

**Filters for `get_sale_list`:**
- `status`: DRAFT, ESTIMATING, ESTIMATED, ORDERING, ORDERED, BACKORDERED
- `quote_status`: DRAFT, AUTHORISED, NOT AVAILABLE
- `order_status`: DRAFT, AUTHORISED, NOT AVAILABLE
- `combined_invoice_status`: NOT AVAILABLE, NOT INVOICED, INVOICED, AUTHORISED
- `fulfilment_status`: NOT FULFILLED, FULFILLED, PARTIAL
- `modified_since`: ISO date (YYYY-MM-DD)

### Purchases

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_purchase_list(...)` | Get purchase orders with filters | List of POs |
| `get_purchase_detail(purchase_id)` | Get detailed PO info | PO dict |
| `get_purchase_credit_notes()` | Get credit note list | List of credit notes |
| `get_purchase_status_counts()` | All PO status counts | Dict of counts |

**Filters for `get_purchase_list`:**
- `order_status`: DRAFT, AUTHORISED
- `combined_invoice_status`: NOT INVOICED, INVOICED, AUTHORISED
- `combined_receiving_status`: NOT RECEIVED, RECEIVED, PARTIAL
- `modified_since`: ISO date

### Stock Adjustments & Stocktakes

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_stock_adjustments(status)` | List of adjustments | List of summaries |
| `get_stock_adjustment_detail(task_id)` | Detailed adjustment lines | Adjustment dict |
| `get_stock_takes(status)` | List of stock takes | List of summaries |
| `get_stock_take_detail(task_id)` | Detailed stocktake with discrepancies | Stocktake dict |

### Transfers

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_stock_transfers(status)` | List of transfers | List of transfers |
| `get_stock_transfer_detail(task_id)` | Detailed transfer info | Transfer dict |
| `get_transfer_status_counts()` | Transfer status counts | Dict of counts |

**Transfer statuses:** DRAFT, IN TRANSIT, ORDERED, PICKING

### Assemblies & Production

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_finished_goods(status)` | List of assemblies | List of assemblies |
| `get_finished_goods_detail(task_id)` | Detailed assembly | Assembly dict |
| `get_production_orders(status)` | List of production orders | List of orders |
| `get_production_order_detail(order_id)` | Detailed production order | Order dict |
| `get_assembly_status_counts()` | Assembly status counts | Dict of counts |
| `get_production_status_counts()` | Production status counts | Dict of counts |

**Assembly statuses:** DRAFT, AUTHORISED, IN PROGRESS
**Production statuses:** Draft, Planned, Released, InProgress

### Products & Inventory

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_products(...)` | Get product master data | List of products |
| `get_product_availability(...)` | Stock levels per location | List of availability records |

**Product fields include:**
- SKU, Name, Category, Status
- PriceTier1-10 (for data hygiene checks)
- AverageCost (for stock valuation)

**Availability fields include:**
- OnHand, Allocated, Available
- OnOrder, InTransit
- Used for negative stock detection

### Customers & Suppliers

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_customers(...)` | Customer list | List of customers |
| `get_suppliers(...)` | Supplier list | List of suppliers |

### Reference Data

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_locations()` | Stock locations | List of locations |
| `get_payment_terms()` | Payment terms | List of terms |
| `get_tax_rules()` | Tax rules | List of rules |

### Low-Level Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_status_count(endpoint, params)` | Get count without fetching data | Integer count |
| `_paginate(endpoint, params)` | Fetch all pages | List of records |
| `_make_request(endpoint, params)` | Single API call | Response dict |

## Error Handling

The client handles errors gracefully:

```python
from modules.api_client import Cin7APIClient, Cin7APIError

try:
    client = Cin7APIClient(client_number=1)
    sales = client.get_sale_list()
except Cin7APIError as e:
    print(f"API Error: {e}")
```

**Error types handled:**
- **400 Bad Request** - Invalid parameters (raises exception)
- **403 Forbidden** - Auth failure (raises exception with clear message)
- **404 Not Found** - Endpoint doesn't exist (raises exception)
- **429 Rate Limit** - Automatically retries after delay
- **500/503 Server Error** - Automatically retries up to 3 times
- **Network errors** - Automatically retries up to 3 times

## Rate Limiting

The API enforces **60 calls per minute**. The client automatically:
- Waits 1 second between calls
- Handles 429 responses by retrying after delay
- Logs each API call for debugging

For a typical health check with ~100 API calls, expect **~2-3 minutes** total runtime.

## Pagination

All list endpoints are automatically paginated:

```python
# This will automatically fetch all pages
all_products = client.get_products()  # Could be 1000s of products

# Behind the scenes:
# - Fetches page 1 (100 records)
# - Fetches page 2 (100 records)
# - Continues until all records retrieved
# - Returns combined list
```

You can adjust page size for specific endpoints:

```python
# Use smaller pages if needed (default is 100)
products = client._paginate("/product", {}, limit=50)
```

## Response Structures

### Sale List Item

```python
{
    "ID": "guid",
    "OrderNumber": "SO-12345",
    "OrderDate": "2024-01-15",
    "Status": "ORDERED",
    "QuoteStatus": "AUTHORISED",
    "OrderStatus": "AUTHORISED",
    "CombinedInvoiceStatus": "NOT INVOICED",
    "FulFilmentStatus": "NOT FULFILLED",
    "Customer": "Customer Name",
    "Total": 1250.00,
    ...
}
```

### Product Availability

```python
{
    "SKU": "PROD-001",
    "Name": "Product Name",
    "Location": "Main Warehouse",
    "OnHand": 100,
    "Allocated": 20,
    "Available": 80,
    "OnOrder": 50,
    "InTransit": 10,
    ...
}
```

### Stock Adjustment Detail

```python
{
    "TaskID": "guid",
    "Status": "COMPLETED",
    "Location": "Main Warehouse",
    "Lines": [
        {
            "ProductID": "guid",
            "SKU": "PROD-001",
            "Name": "Product Name",
            "Quantity": -5,  # negative = adjustment out
            "Cost": 25.00,
            ...
        }
    ]
}
```

## Troubleshooting

### Authentication Errors

```
Cin7APIError: Authentication Failed (403)
```

**Solution:** Check your Account ID and API Key in `.env` file. Verify they're correct in Cin7 Core > Settings > Integrations > API.

### Rate Limit Errors

```
Cin7APIError: Rate limit exceeded (429)
```

**Solution:** The client automatically retries. If you still see this, you may be making concurrent calls. Ensure you're using a single client instance.

### Empty Results

```python
products = client.get_products()
print(len(products))  # 0
```

**Solution:** Check your filters. Try fetching without filters first to verify the endpoint works, then add filters incrementally.

### Timeout Errors

```
Cin7APIError: Request failed after 3 retries
```

**Solution:** Cin7 servers may be slow or down. Try again in a few minutes. For large data pulls, increase retry delay in the client code.

## Performance Tips

1. **Use status counts when you only need totals:**
   ```python
   # Fast - single API call
   count = client.get_status_count("/saleList", {"Status": "BACKORDERED"})

   # Slow - fetches all records
   sales = client.get_sale_list(status="BACKORDERED")
   count = len(sales)
   ```

2. **Filter by date range to reduce data:**
   ```python
   # Only get this month's data
   sales = client.get_sale_list(modified_since="2024-01-01")
   ```

3. **Use helper methods for common queries:**
   ```python
   # Gets all 7 sale status counts with 7 fast API calls
   counts = client.get_sale_status_counts()
   ```

4. **Reuse client instances:**
   ```python
   # Good - single instance
   client = Cin7APIClient(1)
   sales = client.get_sale_list()
   purchases = client.get_purchase_list()

   # Bad - creates new session each time
   sales = Cin7APIClient(1).get_sale_list()
   purchases = Cin7APIClient(1).get_purchase_list()
   ```

## Next Steps

Once the API client is working:

1. **Build `data_processing.py`** - calculate metrics from raw API data
2. **Build `pdf_generator.py`** - generate branded health check PDFs
3. **Build `app.py`** - Streamlit UI for the full workflow

See `Cin7_API_Feasibility_Analysis.md` for the complete endpoint mapping and metric calculations needed.
