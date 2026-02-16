"""
Test script for Cin7 API Client

This script demonstrates how to use the API client and can be used
to verify that your API credentials are working correctly.
"""

from modules.api_client import Cin7APIClient, Cin7APIError
import logging

# Enable debug logging to see API calls
logging.basicConfig(level=logging.INFO)


def test_basic_connection():
    """Test basic API connection and authentication"""
    print("\n" + "=" * 60)
    print("Testing Cin7 API Connection")
    print("=" * 60)

    try:
        # Initialize client (defaults to CLIENT_1)
        client = Cin7APIClient(client_number=1)
        print(f"✓ Client initialized: {client.client_name}")

        # Test a simple API call - get locations
        print("\nFetching locations...")
        locations = client.get_locations()
        print(f"✓ Found {len(locations)} locations:")
        for loc in locations[:5]:  # Show first 5
            print(f"  - {loc.get('Name', 'Unknown')}")

        return True

    except Cin7APIError as e:
        print(f"✗ API Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        return False


def test_status_counts():
    """Test getting status counts (fast queries)"""
    print("\n" + "=" * 60)
    print("Testing Status Count Queries")
    print("=" * 60)

    try:
        client = Cin7APIClient(client_number=1)

        # Get sale status counts
        print("\nSale Status Counts:")
        sale_counts = client.get_sale_status_counts()
        for status, count in sale_counts.items():
            print(f"  {status}: {count}")

        # Get purchase status counts
        print("\nPurchase Status Counts:")
        purchase_counts = client.get_purchase_status_counts()
        for status, count in purchase_counts.items():
            print(f"  {status}: {count}")

        return True

    except Cin7APIError as e:
        print(f"✗ API Error: {e}")
        return False


def test_pagination():
    """Test paginated data retrieval"""
    print("\n" + "=" * 60)
    print("Testing Pagination")
    print("=" * 60)

    try:
        client = Cin7APIClient(client_number=1)

        # Fetch all products (paginated)
        print("\nFetching all products (this may take a minute)...")
        products = client.get_products()
        print(f"✓ Retrieved {len(products)} products")

        # Show sample product data
        if products:
            sample = products[0]
            print("\nSample Product:")
            print(f"  SKU: {sample.get('SKU', 'N/A')}")
            print(f"  Name: {sample.get('Name', 'N/A')}")
            print(f"  Status: {sample.get('Status', 'N/A')}")
            print(f"  Category: {sample.get('Category', 'N/A')}")

        return True

    except Cin7APIError as e:
        print(f"✗ API Error: {e}")
        return False


def test_stock_availability():
    """Test product availability queries"""
    print("\n" + "=" * 60)
    print("Testing Stock Availability")
    print("=" * 60)

    try:
        client = Cin7APIClient(client_number=1)

        print("\nFetching product availability (first 10 items)...")
        availability = client.get_product_availability()

        print(f"✓ Found availability data for {len(availability)} product-location combinations")

        # Show negative stock items
        negative_stock = [
            item for item in availability
            if item.get('Available', 0) < 0 or item.get('OnHand', 0) < 0
        ]

        if negative_stock:
            print(f"\n⚠ Found {len(negative_stock)} items with negative stock:")
            for item in negative_stock[:5]:  # Show first 5
                print(f"  - {item.get('SKU')}: OnHand={item.get('OnHand')}, Available={item.get('Available')}")
        else:
            print("\n✓ No negative stock items found")

        return True

    except Cin7APIError as e:
        print(f"✗ API Error: {e}")
        return False


def test_health_check_data():
    """Test fetching data for all health check sections"""
    print("\n" + "=" * 60)
    print("Testing Health Check Data Collection")
    print("=" * 60)

    try:
        client = Cin7APIClient(client_number=1)

        sections_tested = 0
        sections_passed = 0

        # Test each section
        tests = [
            ("Sale Orders", lambda: client.get_sale_status_counts()),
            ("Purchase Orders", lambda: client.get_purchase_status_counts()),
            ("Assemblies", lambda: client.get_assembly_status_counts()),
            ("Production Orders", lambda: client.get_production_status_counts()),
            ("Transfers", lambda: client.get_transfer_status_counts()),
            ("Stock Adjustments", lambda: client.get_stock_adjustments()),
            ("Stock Takes", lambda: client.get_stock_takes()),
            ("Locations", lambda: client.get_locations()),
        ]

        for section_name, test_func in tests:
            sections_tested += 1
            try:
                print(f"\n  Testing {section_name}...", end=" ")
                result = test_func()
                print(f"✓ ({len(result) if isinstance(result, list) else 'OK'})")
                sections_passed += 1
            except Exception as e:
                print(f"✗ {e}")

        print(f"\n{'=' * 60}")
        print(f"Summary: {sections_passed}/{sections_tested} sections passed")
        print(f"{'=' * 60}")

        return sections_passed == sections_tested

    except Cin7APIError as e:
        print(f"✗ API Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CIN7 CORE API CLIENT - TEST SUITE")
    print("=" * 60)

    # Run all tests
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Status Counts", test_status_counts),
        # Uncomment these for more comprehensive testing:
        # ("Pagination", test_pagination),
        # ("Stock Availability", test_stock_availability),
        # ("Full Health Check", test_health_check_data),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with error: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    print(f"\n{total_passed}/{total_tests} tests passed")
    print("=" * 60)
