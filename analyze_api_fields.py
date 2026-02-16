"""
API Field Analysis Script - COMPREHENSIVE VERSION

Fetches data from ALL Cin7 Core API endpoints and analyzes unique values for key fields.
This helps us understand the data semantics and match the UI's filtering logic.
"""

import os
from dotenv import load_dotenv
from modules.api_client import Cin7APIClient
from collections import defaultdict, Counter
import json

# Load environment variables
load_dotenv()


def analyze_endpoint(client, endpoint_name, fetch_func, fields_to_analyze, additional_analysis_func=None):
    """Generic endpoint analyzer"""
    print("\n" + "=" * 80)
    print(f"ANALYZING {endpoint_name.upper()}")
    print("=" * 80)

    try:
        data = fetch_func()
        print(f"\nTotal Records: {len(data)}")

        field_values = defaultdict(Counter)

        # Analyze specified fields
        for record in data:
            for field in fields_to_analyze:
                value = record.get(field)
                if value is not None:
                    field_values[field][str(value)] += 1

        # Print results
        for field in fields_to_analyze:
            if field in field_values:
                print(f"\n--- {field} ---")
                total = sum(field_values[field].values())
                for value, count in field_values[field].most_common():
                    percentage = (count / total * 100) if total > 0 else 0
                    print(f"  {value}: {count} ({percentage:.1f}%)")

        # Run additional analysis if provided
        if additional_analysis_func:
            additional_analysis_func(data)

        return data, field_values

    except Exception as e:
        print(f"ERROR: {e}")
        return [], {}


def analyze_sales_combos(sales):
    """Additional analysis for sales order status combinations"""
    print("\n" + "=" * 80)
    print("SALES STATUS COMBINATIONS (Top 20)")
    print("=" * 80)

    status_combos = defaultdict(int)

    for sale in sales:
        status = sale.get('Status', 'NULL')
        ship_status = sale.get('ShipmentStatus', 'NULL')
        invoice_status = sale.get('InvoiceStatus', 'NULL')
        combined_shipping = sale.get('CombinedShippingStatus', 'NULL')
        combined_invoice = sale.get('CombinedInvoiceStatus', 'NULL')

        combo = f"Status:{status} | Ship:{ship_status} | Inv:{invoice_status} | CombShip:{combined_shipping} | CombInv:{combined_invoice}"
        status_combos[combo] += 1

    print("\nTop 20 Status Combinations:")
    for combo, count in sorted(status_combos.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  [{count:>4}] {combo}")


def analyze_purchase_combos(purchases):
    """Additional analysis for purchase order status combinations"""
    print("\n" + "=" * 80)
    print("PURCHASE STATUS COMBINATIONS (Top 20)")
    print("=" * 80)

    status_combos = defaultdict(int)

    for po in purchases:
        status = po.get('Status', 'NULL')
        stock_status = po.get('StockStatus', 'NULL')
        invoice_status = po.get('InvoiceStatus', 'NULL')
        combined_stock = po.get('CombinedStockStatus', 'NULL')
        combined_invoice = po.get('CombinedInvoiceStatus', 'NULL')

        combo = f"Status:{status} | Stock:{stock_status} | Inv:{invoice_status} | CombStock:{combined_stock} | CombInv:{combined_invoice}"
        status_combos[combo] += 1

    print("\nTop 20 Status Combinations:")
    for combo, count in sorted(status_combos.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  [{count:>4}] {combo}")


def analyze_product_types(products):
    """Additional analysis for product characteristics"""
    print("\n" + "=" * 80)
    print("PRODUCT TYPE ANALYSIS")
    print("=" * 80)

    sellable_count = sum(1 for p in products if p.get('Sellable', False))
    purchasable_count = sum(1 for p in products if p.get('Purchasable', False))
    assemblable_count = sum(1 for p in products if p.get('Assembly', False))
    has_price = sum(1 for p in products if any(p.get(f'PriceTier{i}', 0) > 0 for i in range(1, 11)))
    has_cost = sum(1 for p in products if p.get('AverageCost', 0) > 0 or p.get('DefaultCost', 0) > 0)

    print(f"Sellable Products: {sellable_count}")
    print(f"Purchasable Products: {purchasable_count}")
    print(f"Assembly Products: {assemblable_count}")
    print(f"Products with Price: {has_price}")
    print(f"Products with Cost: {has_cost}")


def save_sample_records(data_dict, output_file='api_sample_data.json'):
    """Save sample records to JSON for inspection"""
    samples = {}

    for data_type, data_list in data_dict.items():
        if data_list:
            # Save first 5 records of each type
            samples[data_type] = data_list[:5]

    with open(output_file, 'w') as f:
        json.dump(samples, f, indent=2, default=str)

    print(f"\nSample records saved to: {output_file}")


def main():
    # Initialize API client
    client_number = int(input("Enter client number (1-10): ") or "1")
    client = Cin7APIClient(client_number=client_number)

    print(f"\nConnected to: {client.client_name}")
    print(f"Account ID: {client.account_id}")
    print("\nFetching and analyzing data from ALL endpoints...\n")
    print("(This may take several minutes depending on data volume)")

    # Store all results
    all_data = {}
    all_fields = {}

    # 1. SALES ORDERS
    sales, sales_fields = analyze_endpoint(
        client, "Sales Orders",
        client.get_sale_list,
        ['Status', 'SaleOrderDate', 'ShipBy', 'InvoiceStatus', 'PickStatus',
         'PackStatus', 'ShipmentStatus', 'CombinedPickingStatus',
         'CombinedPackingStatus', 'CombinedShippingStatus', 'CombinedInvoiceStatus',
         'InvoiceNumber', 'QuoteStatus', 'Type', 'Total', 'SubTotal', 'TaxTotal',
         'Currency', 'CustomerID', 'OrderNumber', 'DeliveryMethod', 'OrderLocationID'],
        analyze_sales_combos
    )
    all_data['sales'] = sales
    all_fields['sales'] = sales_fields

    # 2. PURCHASE ORDERS
    purchases, purchase_fields = analyze_endpoint(
        client, "Purchase Orders",
        client.get_purchase_list,
        ['Status', 'OrderDate', 'RequiredBy', 'StockReceivedDate',
         'InvoiceStatus', 'StockStatus', 'CombinedInvoiceStatus',
         'CombinedStockStatus', 'TaskID', 'Voided', 'Total', 'SubTotal',
         'TaxTotal', 'Currency', 'SupplierID', 'OrderNumber', 'DeliveryMethod'],
        analyze_purchase_combos
    )
    all_data['purchases'] = purchases
    all_fields['purchases'] = purchase_fields

    # 3. STOCK ADJUSTMENTS
    adjustments, adj_fields = analyze_endpoint(
        client, "Stock Adjustments",
        client.get_stock_adjustments,
        ['Status', 'TaskType', 'Location', 'Date', 'TaskID', 'AdjustmentReason',
         'TotalCost', 'TotalQuantity', 'CreatedBy', 'CompletedDate']
    )
    all_data['stock_adjustments'] = adjustments
    all_fields['stock_adjustments'] = adj_fields

    # 4. STOCK TAKES
    stock_takes, st_fields = analyze_endpoint(
        client, "Stock Takes",
        client.get_stock_takes,
        ['Status', 'Location', 'Date', 'Type', 'CreatedBy', 'CompletedDate',
         'TotalVariance', 'VarianceValue']
    )
    all_data['stock_takes'] = stock_takes
    all_fields['stock_takes'] = st_fields

    # 5. TRANSFERS
    transfers, transfer_fields = analyze_endpoint(
        client, "Transfers",
        client.get_stock_transfers,
        ['Status', 'TaskStatus', 'FromLocation', 'ToLocation', 'Date',
         'TransferNumber', 'TotalCost', 'CreatedBy', 'CompletedDate']
    )
    all_data['transfers'] = transfers
    all_fields['transfers'] = transfer_fields

    # 6. ASSEMBLIES
    assemblies, assembly_fields = analyze_endpoint(
        client, "Assemblies",
        client.get_finished_goods,
        ['Status', 'TaskStatus', 'Type', 'Location', 'AssemblyNumber',
         'Quantity', 'SKU', 'CreatedDate', 'CompletedDate']
    )
    all_data['assemblies'] = assemblies
    all_fields['assemblies'] = assembly_fields

    # 7. PRODUCTION ORDERS
    production, prod_fields = analyze_endpoint(
        client, "Production Orders",
        client.get_production_orders,
        ['Status', 'StartDate', 'DueDate', 'Location', 'ProductionNumber',
         'SKU', 'Quantity', 'TotalCost', 'CreatedBy']
    )
    all_data['production'] = production
    all_fields['production'] = prod_fields

    # 8. PRODUCTS
    products, product_fields = analyze_endpoint(
        client, "Products",
        client.get_products,
        ['Type', 'Status', 'Sellable', 'Purchasable', 'Assembly',
         'Category', 'Brand', 'COGSAccount', 'PriceTier1', 'AverageCost',
         'DefaultCost', 'ProductGroup', 'SupplierID', 'Weight'],
        analyze_product_types
    )
    all_data['products'] = products
    all_fields['products'] = product_fields

    # 9. STOCK AVAILABILITY
    availability, avail_fields = analyze_endpoint(
        client, "Stock Availability",
        client.get_product_availability,
        ['Location', 'SKU', 'Available', 'OnHand', 'Allocated', 'OnOrder',
         'StockOnHand', 'InStock', 'ProductID']
    )
    all_data['availability'] = availability
    all_fields['availability'] = avail_fields

    # 10. CUSTOMERS
    customers, cust_fields = analyze_endpoint(
        client, "Customers",
        client.get_customers,
        ['Type', 'Status', 'Currency', 'PaymentTerm', 'Carrier',
         'PriceColumn', 'Email', 'Phone', 'ContactPerson', 'CreditLimit',
         'TaxRule', 'DeliveryInstruction']
    )
    all_data['customers'] = customers
    all_fields['customers'] = cust_fields

    # 11. SUPPLIERS
    suppliers, supp_fields = analyze_endpoint(
        client, "Suppliers",
        client.get_suppliers,
        ['Status', 'Currency', 'PaymentTerm', 'Email', 'Phone',
         'ContactPerson', 'CreditLimit', 'TaxRule', 'DefaultCarrier']
    )
    all_data['suppliers'] = suppliers
    all_fields['suppliers'] = supp_fields

    # 12. LOCATIONS
    locations, loc_fields = analyze_endpoint(
        client, "Locations",
        client.get_locations,
        ['IsDefault', 'Deprecated', 'Name', 'LocationType', 'Address',
         'Country', 'IsShopifyLocation']
    )
    all_data['locations'] = locations
    all_fields['locations'] = loc_fields

    # 13. SALES CREDIT NOTES
    sale_credits, sc_fields = analyze_endpoint(
        client, "Sales Credit Notes",
        client.get_sale_credit_notes,
        ['Status', 'CreditDate', 'Type', 'Total', 'SubTotal', 'TaxTotal',
         'Currency', 'CustomerID', 'CreditNoteNumber', 'Reason']
    )
    all_data['sale_credits'] = sale_credits
    all_fields['sale_credits'] = sc_fields

    # 14. PURCHASE CREDIT NOTES
    purchase_credits, pc_fields = analyze_endpoint(
        client, "Purchase Credit Notes",
        client.get_purchase_credit_notes,
        ['Status', 'CreditDate', 'Type', 'Total', 'SubTotal', 'TaxTotal',
         'Currency', 'SupplierID', 'CreditNoteNumber', 'Reason']
    )
    all_data['purchase_credits'] = purchase_credits
    all_fields['purchase_credits'] = pc_fields

    # Save sample data
    save_sample_records(all_data)

    # Generate summary report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    for data_type, data_list in all_data.items():
        print(f"{data_type:.<40} {len(data_list):>6} records")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nOutputs generated:")
    print("  1. api_sample_data.json - Sample records from each endpoint")
    print("  2. Console output above - All unique field values with counts")
    print("\nNext steps:")
    print("  1. Review the unique values for each field above")
    print("  2. Go to Cin7 Core UI and compare the counts")
    print("  3. Identify which status combinations match UI filters")
    print("  4. Update data_processing.py to replicate UI logic")
    print("\nExample: If UI shows 500 'Awaiting Fulfilment' but API shows 1558,")
    print("look at the status combinations to find which ones the UI is filtering.")


if __name__ == "__main__":
    main()
