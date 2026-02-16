"""
Test API Client with UI-style Date Filters

This demonstrates how to filter results to match what you see in the Cin7 UI
by excluding old/archived records.
"""

from modules.api_client import Cin7APIClient
from modules.ui_filters import UIFilters, get_date_range

def test_with_ui_filters():
    """Test API calls with date filters to match Cin7 UI"""

    print("\n" + "=" * 80)
    print("TESTING WITH UI FILTERS (Excluding Archived Orders)")
    print("=" * 80)

    client = Cin7APIClient(client_number=1)
    filters = UIFilters()

    print(f"\nDate Filters Available:")
    print(f"  Last 30 days: {filters.last_30_days}")
    print(f"  Last 60 days: {filters.last_60_days}")
    print(f"  Last 90 days: {filters.last_90_days}")
    print(f"  Current month: {filters.current_month}")

    # ==========================================================================
    # PURCHASE ORDERS - Comparing with and without date filters
    # ==========================================================================

    print("\n" + "=" * 80)
    print("DRAFT PURCHASE ORDERS COMPARISON")
    print("=" * 80)

    # WITHOUT date filter (includes archived)
    print("\n1. WITHOUT date filter (all draft POs ever):")
    all_drafts = client.get_status_count("/purchaseList", {"OrderStatus": "DRAFT"})
    print(f"   Total draft POs: {all_drafts}")

    # WITH 90-day filter (active orders only)
    print("\n2. WITH 90-day filter (recent drafts only):")
    recent_drafts_90 = client.get_status_count(
        "/purchaseList",
        {
            "OrderStatus": "DRAFT",
            "ModifiedSince": filters.last_90_days
        }
    )
    print(f"   Draft POs (last 90 days): {recent_drafts_90}")

    # WITH 30-day filter (very recent)
    print("\n3. WITH 30-day filter (very recent drafts):")
    recent_drafts_30 = client.get_status_count(
        "/purchaseList",
        {
            "OrderStatus": "DRAFT",
            "ModifiedSince": filters.last_30_days
        }
    )
    print(f"   Draft POs (last 30 days): {recent_drafts_30}")

    print(f"\n📊 BREAKDOWN:")
    print(f"   Total drafts (all time):     {all_drafts}")
    print(f"   Active (last 90 days):       {recent_drafts_90}")
    print(f"   Very recent (last 30 days):  {recent_drafts_30}")
    print(f"   Archived (older than 90d):   {all_drafts - recent_drafts_90}")

    # ==========================================================================
    # COMPLETE STATUS COUNTS WITH DATE FILTERS
    # ==========================================================================

    print("\n" + "=" * 80)
    print("PURCHASE STATUS COUNTS (Last 90 Days - Matches UI)")
    print("=" * 80)

    # Get all purchase statuses with 90-day filter
    date_filter = filters.last_90_days

    counts = {
        "Draft": client.get_status_count(
            "/purchaseList",
            {"OrderStatus": "DRAFT", "ModifiedSince": date_filter}
        ),
        "Authorised": client.get_status_count(
            "/purchaseList",
            {"OrderStatus": "AUTHORISED", "ModifiedSince": date_filter}
        ),
        "Authorised (Not Invoiced)": client.get_status_count(
            "/purchaseList",
            {
                "OrderStatus": "AUTHORISED",
                "CombinedInvoiceStatus": "NOT INVOICED",
                "ModifiedSince": date_filter
            }
        ),
        "Authorised (Not Received)": client.get_status_count(
            "/purchaseList",
            {
                "OrderStatus": "AUTHORISED",
                "CombinedReceivingStatus": "NOT RECEIVED",
                "ModifiedSince": date_filter
            }
        ),
    }

    for status, count in counts.items():
        print(f"   {status:<30} {count:>5}")

    # ==========================================================================
    # SALE ORDERS WITH DATE FILTERS
    # ==========================================================================

    print("\n" + "=" * 80)
    print("SALE STATUS COUNTS (Last 90 Days - Matches UI)")
    print("=" * 80)

    sale_counts = {
        "Draft Quotes": client.get_status_count(
            "/saleList",
            {"QuoteStatus": "DRAFT", "ModifiedSince": date_filter}
        ),
        "Backordered": client.get_status_count(
            "/saleList",
            {"Status": "BACKORDERED", "ModifiedSince": date_filter}
        ),
        "Awaiting Fulfilment": client.get_status_count(
            "/saleList",
            {
                "OrderStatus": "AUTHORISED",
                "FulFilmentStatus": "NOT FULFILLED",
                "ModifiedSince": date_filter
            }
        ),
        "Fulfilled Not Invoiced": client.get_status_count(
            "/saleList",
            {
                "FulFilmentStatus": "FULFILLED",
                "CombinedInvoiceStatus": "NOT INVOICED",
                "ModifiedSince": date_filter
            }
        ),
    }

    for status, count in sale_counts.items():
        print(f"   {status:<30} {count:>5}")

    # ==========================================================================
    # RECOMMENDATION
    # ==========================================================================

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print("""
For your health check reports, I recommend using a 90-day filter by default:

    filters = UIFilters()
    client.get_purchase_list(
        order_status="DRAFT",
        modified_since=filters.last_90_days  # Only last 90 days
    )

This will:
✓ Match what users see in the Cin7 UI
✓ Exclude old archived orders
✓ Focus on actionable, current data
✓ Make reports more relevant and accurate

You can adjust the time period based on your needs:
- filters.last_30_days  → Very recent activity
- filters.last_60_days  → 2 months
- filters.last_90_days  → Standard (recommended)
- filters.current_month → This month only
    """)

if __name__ == "__main__":
    test_with_ui_filters()
