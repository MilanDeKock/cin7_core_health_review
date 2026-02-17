"""
Filter Test Script

Fetches ALL records from an endpoint and counts how many match a filter.
We iterate on the filter logic here until the count matches the Cin7 UI.

Usage: python test_filter.py
"""

from dotenv import load_dotenv
from modules.api_client import Cin7APIClient

load_dotenv()


# =============================================================================
# EDIT THIS SECTION EACH ITERATION
# =============================================================================

ENDPOINT_CHOICE = "2"   # 1=Sales, 2=Purchases, 3=Transfers, 4=Assemblies, 5=Production

DESCRIPTION = "Auth POs — prior periods, not received (inspect EXTRA)"

from datetime import date, timedelta
_period_start = date(2026, 2, 1).isoformat()
_lookback = (date(2026, 2, 1) - timedelta(days=365)).isoformat()

_UI_POS = {
    'PO-00212','PO-00224','PO-00230','PO-00235','PO-00245','PO-00246','PO-00247','PO-00248',
    'PO-00261','PO-00270','PO-00278','PO-00277','PO-00276','PO-00280','PO-00284','PO-00287',
    'PO-00291','PO-00301','PO-00304','PO-00306','PO-00290','PO-00318','PO-00325','PO-00342',
    'PO-00360','PO-00361','PO-00362','PO-00382','PO-00383',
}

def match(record):
    order_date = record.get('OrderDate') or ''
    in_filter = (
        record.get('Status') in ('INVOICED', 'ORDERED', 'ORDERING', 'PARTIALLY INVOICED', 'RECEIVING')
        and record.get('OrderStatus') in ('AUTHORISED', 'DRAFT')
        and record.get('InvoiceStatus') in ('AUTHORISED', 'DRAFT', 'NOT AVAILABLE')
        and record.get('CombinedReceivingStatus') in ('', 'NOT AVAILABLE', 'NOT RECEIVED', 'PARTIALLY RECEIVED')
        and _lookback <= order_date < _period_start
    )
    return in_filter and record.get('OrderNumber') not in _UI_POS

# Empty → show distinct field values of the EXTRA POs
SHOW_FIELDS = []



# =============================================================================
# DON'T EDIT BELOW — just run the script
# =============================================================================

ENDPOINTS = {
    "1": {"name": "Sales Orders",      "endpoint": "/saleList"},
    "2": {"name": "Purchase Orders",   "endpoint": "/purchaseList"},
    "3": {"name": "Transfers",         "endpoint": "/stockTransferList"},
    "4": {"name": "Assemblies",        "endpoint": "/finishedGoodsList"},
    "5": {"name": "Production Orders", "endpoint": "/production/orderList"},
}


def main():
    client_number = int(input("Client number (1-10): ") or "1")
    client = Cin7APIClient(client_number=client_number)
    print(f"Connected: {client.client_name}\n")

    cfg = ENDPOINTS[ENDPOINT_CHOICE]
    print(f"Fetching ALL {cfg['name']} records...")
    records = client._paginate(cfg["endpoint"], {})
    print(f"Total records fetched: {len(records)}")

    matched = [r for r in records if match(r)]

    unique_pos = len({r.get('OrderNumber') for r in matched})
    print(f"\nFilter:   {DESCRIPTION}")
    print(f"Matched:  {len(matched)} raw records  |  {unique_pos} unique PO numbers  (compare unique to Cin7 UI)")

    # If SHOW_FIELDS is empty and no UI list, show distinct values for key fields
    if not SHOW_FIELDS and not globals().get('UI_PO_NUMBERS') and not globals().get('UI_SO_NUMBERS'):
        for field in ['Status', 'OrderStatus', 'InvoiceStatus', 'CombinedInvoiceStatus', 'CombinedReceivingStatus']:
            vals = sorted({str(r.get(field, '')) for r in matched})
            print(f"  {field}: {vals}")
        return

    # If UI reference list provided, show found/missing/extra
    ui_numbers = globals().get('UI_PO_NUMBERS') or globals().get('UI_SO_NUMBERS')
    if ui_numbers:
        matched_numbers = {r.get('OrderNumber') for r in matched}
        found = ui_numbers & matched_numbers
        missing = ui_numbers - matched_numbers
        extra = matched_numbers - ui_numbers
        print(f"\nUI reference count: {len(ui_numbers)}")
        print(f"Found in filter:    {len(found)}")
        print(f"MISSING from filter: {sorted(missing)}")
        print(f"EXTRA (not in UI):   {sorted(extra)}")
    elif matched:
        if not SHOW_FIELDS:
            # Dump ALL fields for inspection
            for r in matched:
                print(f"\n--- {r.get('OrderNumber')} ---")
                for k, v in r.items():
                    print(f"  {k}: {v}")
        else:
            print(f"\nAll {len(matched)} matched records:")
            print("  " + " | ".join(f"{f:<20}" for f in SHOW_FIELDS))
            print("  " + "-" * (22 * len(SHOW_FIELDS)))
            for r in matched:
                print("  " + " | ".join(str(r.get(f, ""))[:20] for f in SHOW_FIELDS))


if __name__ == "__main__":
    main()
