"""
Investigate Draft Purchase Orders
Shows exactly what the API is returning vs what you see in Cin7 UI
"""

from modules.api_client import Cin7APIClient
from datetime import datetime

def investigate_draft_pos():
    """Fetch and display all draft POs with details"""
    print("\n" + "=" * 80)
    print("INVESTIGATING DRAFT PURCHASE ORDERS")
    print("=" * 80)

    client = Cin7APIClient(client_number=1)

    # Fetch all draft POs
    print("\nFetching all draft purchase orders from API...")
    draft_pos = client.get_purchase_list(order_status="DRAFT")

    print(f"\n✓ API returned {len(draft_pos)} draft purchase orders")
    print("\nHere are the details:\n")

    # Display each draft PO
    for i, po in enumerate(draft_pos, 1):
        order_number = po.get('OrderNumber', 'N/A')
        order_date = po.get('OrderDate', 'N/A')
        supplier = po.get('SupplierName', po.get('Supplier', 'N/A'))
        total = po.get('Total', 0)
        invoice_status = po.get('CombinedInvoiceStatus', 'N/A')
        receiving_status = po.get('CombinedReceivingStatus', 'N/A')

        # Try to parse and format the date
        try:
            if order_date and order_date != 'N/A':
                # Handle different date formats
                if 'T' in order_date:
                    date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                else:
                    formatted_date = order_date
            else:
                formatted_date = 'N/A'
        except:
            formatted_date = order_date

        print(f"{i:2}. PO: {order_number:<15} | Date: {formatted_date:<12} | "
              f"Supplier: {supplier:<25} | Total: ${total:>10.2f}")
        print(f"    Invoice: {invoice_status:<20} | Receiving: {receiving_status}")
        print()

    # Summary analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    # Check if any are very old
    old_orders = []
    recent_orders = []

    for po in draft_pos:
        order_date = po.get('OrderDate', '')
        try:
            if order_date and 'T' in order_date:
                date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                age_days = (datetime.now(date_obj.tzinfo) - date_obj).days

                if age_days > 90:
                    old_orders.append((po.get('OrderNumber'), age_days))
                else:
                    recent_orders.append((po.get('OrderNumber'), age_days))
        except:
            pass

    print(f"\nOrders older than 90 days: {len(old_orders)}")
    if old_orders:
        for order_num, age in old_orders[:5]:
            print(f"  - {order_num}: {age} days old")

    print(f"\nOrders within last 90 days: {len(recent_orders)}")

    print("\n" + "=" * 80)
    print("POSSIBLE REASONS FOR UI DISCREPANCY")
    print("=" * 80)
    print("""
1. DATE FILTER: The Cin7 UI might have a date filter active
   - Check if there's a date range selector at the top of the page
   - The UI often defaults to "Last 30 days" or "Last 60 days"

2. LOCATION FILTER: Check if you have a location filter active in the UI
   - Look for a location dropdown or filter

3. STATUS COMBINATION: The UI "Draft POs" might use different criteria
   - Maybe it shows only "Draft AND Not Invoiced"
   - Or "Draft AND Not Received"

4. ARCHIVED ORDERS: Some of these might be archived/hidden in the UI
   - Old draft orders are sometimes hidden to reduce clutter

5. USER PERMISSIONS: The UI might only show POs for your user/branch
   - The API returns ALL draft POs regardless of user
    """)

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("""
1. Compare the PO numbers above with what you see in Cin7 UI
2. Note which PO numbers are missing from the UI
3. Try searching for one of the "missing" POs directly in Cin7
4. Check what filters are active in your Cin7 UI (top of page)

If you want, I can add date filters to only get recent orders.
    """)

if __name__ == "__main__":
    investigate_draft_pos()
