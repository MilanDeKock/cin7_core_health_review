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

DESCRIPTION = "PO Billing (with IsServiceOnly fix)"

UI_PO_NUMBERS = {
    'SPO000406','SPO000554','SPO000612','SPO000614',
    'SPO000621','SPO000626','SPO000629','SPO000631',
    'SPO000632','SPO000634','SPO000635','SPO000641',
    'SPO000642','SPO000646',
}

def match(record):
    status = record.get('Status', '')
    comb_recv = record.get('CombinedReceivingStatus', '')
    return (
        record.get('OrderStatus') in ('AUTHORISED', 'RECEIVED')
        and record.get('CombinedInvoiceStatus') in ('NOT INVOICED', 'PARTIALLY INVOICED', 'PARTIALLY INVOICED / CREDITED')
        and status not in ('COMPLETED', 'VOIDED', 'INVOICED', 'CREDITED',
                           'COMPLETED / CREDIT NOTE CLOSED')
        and not (status == 'ORDERED' and comb_recv in ('NOT RECEIVED', 'NOT AVAILABLE', '')
                 and not record.get('IsServiceOnly'))
    )

SHOW_FIELDS = ['OrderNumber', 'OrderStatus', 'CombinedInvoiceStatus', 'Status', 'IsServiceOnly']



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

    # If UI reference list provided, show found/missing/extra
    ui_numbers = globals().get('UI_PO_NUMBERS') or globals().get('UI_SO_NUMBERS')
    if ui_numbers:
        matched_numbers = {r.get('OrderNumber') for r in matched}
        ui_len = len(next(iter(ui_numbers)))
        api_len = len(next(iter(matched_numbers))) if matched_numbers else ui_len
        if api_len > ui_len:
            matched_short = {on[:ui_len] for on in matched_numbers}
            found = ui_numbers & matched_short
            missing = ui_numbers - matched_short
            extra = matched_short - ui_numbers
            print(f"\n(Comparing first {ui_len} chars of API numbers)")
        else:
            found = ui_numbers & matched_numbers
            missing = ui_numbers - matched_numbers
            extra = matched_numbers - ui_numbers
        print(f"\nUI reference count: {len(ui_numbers)}")
        print(f"Found in filter:    {len(found)}")
        print(f"MISSING from filter: {sorted(missing)}")
        print(f"EXTRA (not in UI):   {sorted(extra)}")

        if missing:
            print(f"\n--- MISSING ---")
            for ui_num in sorted(missing):
                for r in records:
                    on = r.get('OrderNumber', '')
                    compare_on = on[:ui_len] if api_len > ui_len else on
                    if compare_on == ui_num:
                        print(f"  {on}: Status={r.get('Status')}  OrderStatus={r.get('OrderStatus')}  CombInv={r.get('CombinedInvoiceStatus')}  CombRecv={r.get('CombinedReceivingStatus')}")
                        break
                else:
                    print(f"  {ui_num}: NOT FOUND in API at all")
        if extra and len(extra) <= 25:
            print(f"\n--- EXTRA (not in UI) field comparison ---")
            for r in matched:
                on = r.get('OrderNumber', '')
                compare_on = on[:ui_len] if api_len > ui_len else on
                if compare_on in extra:
                    print(f"  {on}: Status={r.get('Status')}  CombRecv={r.get('CombinedReceivingStatus')}  IsServiceOnly={r.get('IsServiceOnly')}")
    elif matched:
        if not SHOW_FIELDS:
            r = matched[0]
            print(f"\n--- ALL FIELDS for {r.get('OrderNumber')} ---")
            for k, v in r.items():
                print(f"  {k}: {v}")
            if len(matched) > 1:
                print(f"\n--- OrderNumbers for all {len(matched)} matched ---")
                for r in matched:
                    print(f"  {r.get('OrderNumber')}")
        else:
            print(f"\nAll {len(matched)} matched records:")
            print("  " + " | ".join(f"{f:<20}" for f in SHOW_FIELDS))
            print("  " + "-" * (22 * len(SHOW_FIELDS)))
            for r in matched:
                print("  " + " | ".join(str(r.get(f, ""))[:20] for f in SHOW_FIELDS))


if __name__ == "__main__":
    main()
