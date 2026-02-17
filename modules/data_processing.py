"""
Data Processing Module

Processes raw Cin7 API data into health check metrics and insights.
Each function corresponds to a section of the health check report.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse ISO date string to datetime object.

    Args:
        date_string: ISO format date string

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Handle ISO format with timezone
        if 'T' in date_string:
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(date_string)
    except (ValueError, AttributeError):
        return None


def get_oldest_date(records: List[Dict], date_field: str) -> Optional[Dict[str, Any]]:
    """
    Find the record with the oldest date.

    Args:
        records: List of record dictionaries
        date_field: Name of the date field to check

    Returns:
        Dictionary with 'date', 'age_days', and 'record' (the oldest record)
    """
    if not records:
        return None

    oldest = None
    oldest_date = None

    for record in records:
        date_str = record.get(date_field)
        if not date_str:
            continue

        date_obj = parse_date(date_str)
        if date_obj and (oldest_date is None or date_obj < oldest_date):
            oldest_date = date_obj
            oldest = record

    if oldest and oldest_date:
        age_days = (datetime.now(oldest_date.tzinfo) - oldest_date).days
        return {
            'date': oldest_date.strftime('%Y-%m-%d'),
            'age_days': age_days,
            'record': oldest
        }

    return None


def calculate_age_days(date_string: str) -> int:
    """Calculate age in days from a date string to now"""
    date_obj = parse_date(date_string)
    if date_obj:
        return (datetime.now(date_obj.tzinfo) - date_obj).days
    return 0


# =============================================================================
# SALES METRICS
# =============================================================================

def process_sales_metrics(
    sales_data: List[Dict],
    status_counts: Optional[Dict[str, int]] = None,
    report_year: Optional[int] = None,
    report_month: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process sales data into health check metrics.

    Status counts are computed client-side from the bulk data (no separate API calls needed).
    Applies 365-day cutoff and excludes COMPLETED/VOIDED orders.

    Args:
        sales_data: Raw sale list from API (bulk pull)
        status_counts: Ignored — counts are now computed from bulk data
        report_year: Report period year (for period-split metrics)
        report_month: Report period month (for period-split metrics)

    Returns:
        Dictionary with sales health check metrics
    """
    logger.info("Processing sales metrics...")

    from datetime import date, timedelta
    today = date.today()
    cutoff = (today - timedelta(days=365)).isoformat()

    def _sale_date(s):
        return s.get('SaleOrderDate') or s.get('OrderDate') or ''

    # Apply 365-day cutoff and exclude completed/voided
    active_sales = [
        s for s in sales_data
        if s.get('Status') not in ('COMPLETED', 'VOIDED')
        and _sale_date(s) >= cutoff
    ]

    # Compute dashboard status counts client-side
    computed_counts = {
        'draft_quotes': len([s for s in active_sales if s.get('QuoteStatus') == 'DRAFT']),
        'pending_orders': len([s for s in active_sales if s.get('OrderStatus') == 'DRAFT']),
        'backordered': len([s for s in active_sales if s.get('Status') == 'BACKORDERED']),
        'awaiting_fulfilment': len([
            s for s in active_sales
            if s.get('OrderStatus') == 'AUTHORISED'
            and s.get('CombinedShippingStatus') in ('NOT SHIPPED', 'PARTIALLY SHIPPED')
        ]),
        'orders_to_bill': len([
            s for s in active_sales
            if s.get('OrderStatus') == 'AUTHORISED'
            and s.get('CombinedInvoiceStatus') in ('NOT AVAILABLE', 'DRAFT')
        ]),
        'authorised_quotes_no_so': len([
            s for s in active_sales
            if s.get('QuoteStatus') == 'AUTHORISED'
            and s.get('OrderStatus') == 'NOT AVAILABLE'
        ]),
    }

    metrics = {
        'status_counts': computed_counts,
        'oldest_by_status': {},
        'anomalies': {},
        'summary': {}
    }

    # Group active sales by OrderStatus for oldest-date tracking
    by_status = defaultdict(list)
    for sale in active_sales:
        status = sale.get('OrderStatus', sale.get('Status', 'UNKNOWN'))
        by_status[status].append(sale)

    # Use whichever date field the API returns
    date_field = 'SaleOrderDate' if any(s.get('SaleOrderDate') for s in active_sales[:5]) else 'OrderDate'

    for status, sales in by_status.items():
        oldest = get_oldest_date(sales, date_field)
        if oldest:
            metrics['oldest_by_status'][status] = {
                'order_number': oldest['record'].get('OrderNumber'),
                'date': oldest['date'],
                'age_days': oldest['age_days'],
                'customer': oldest['record'].get('Customer', 'Unknown')
            }

    # Determine period start for prior/current split
    if report_year and report_month:
        period_start = date(report_year, report_month, 1).isoformat()
    else:
        period_start = date(today.year, today.month, 1).isoformat()

    # Auth SOs from prior periods, not fulfilled
    authorised_prior_not_fulfilled = [
        s for s in active_sales
        if s.get('OrderStatus') == 'AUTHORISED'
        and s.get('FulFilmentStatus') in ('NOT FULFILLED', 'PARTIALLY FULFILLED')
        and _sale_date(s) < period_start
    ]

    # Fulfilled SOs not invoiced
    fulfilled_not_invoiced = [
        s for s in active_sales
        if s.get('FulFilmentStatus') == 'FULFILLED'
        and s.get('CombinedInvoiceStatus') in ('NOT AVAILABLE', 'DRAFT')
    ]

    # Invoiced SOs not fulfilled
    invoiced_not_fulfilled = [
        s for s in active_sales
        if s.get('CombinedInvoiceStatus') in ('AUTHORISED', 'PAID')
        and s.get('FulFilmentStatus') in ('NOT FULFILLED', 'PARTIALLY FULFILLED')
    ]

    metrics['anomalies'] = {
        'authorised_prior_not_fulfilled': {
            'count': len(authorised_prior_not_fulfilled),
            'oldest': get_oldest_date(authorised_prior_not_fulfilled, date_field),
            'records': authorised_prior_not_fulfilled[:10]
        },
        'fulfilled_not_invoiced': {
            'count': len(fulfilled_not_invoiced),
            'oldest': get_oldest_date(fulfilled_not_invoiced, date_field),
            'records': fulfilled_not_invoiced[:10]
        },
        'invoiced_not_fulfilled': {
            'count': len(invoiced_not_fulfilled),
            'oldest': get_oldest_date(invoiced_not_fulfilled, date_field),
            'records': invoiced_not_fulfilled[:10]
        }
    }

    metrics['summary'] = {
        'total_sales': len(sales_data),
        'active_sales': len(active_sales),
        'unique_statuses': len(by_status),
        'has_anomalies': any(a['count'] > 0 for a in metrics['anomalies'].values())
    }

    return metrics


# =============================================================================
# PURCHASE METRICS
# =============================================================================

def process_purchase_metrics(
    purchases_data: List[Dict],
    status_counts: Optional[Dict[str, int]] = None,
    report_year: Optional[int] = None,
    report_month: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process purchase data into health check metrics.

    Args:
        purchases_data: Raw purchase list from API
        status_counts: Pre-calculated status counts (optional)
        report_year: Report period year (for period-split metrics)
        report_month: Report period month (for period-split metrics)

    Returns:
        Dictionary with purchase health check metrics
    """
    logger.info("Processing purchase metrics...")

    from datetime import date, timedelta
    today = date.today()
    cutoff = (today - timedelta(days=365)).isoformat()

    # Apply 365-day cutoff and exclude completed/voided
    active_purchases = [
        p for p in purchases_data
        if p.get('Status') not in ('COMPLETED', 'VOIDED')
        and (p.get('OrderDate') or '') >= cutoff
    ]

    # Compute dashboard status counts client-side
    computed_counts = {
        'draft': len([p for p in active_purchases if p.get('Status') == 'DRAFT']),
        'awaiting_approval': len([p for p in active_purchases if p.get('Status') == 'ORDERING']),
        'billing': len([
            p for p in active_purchases
            if p.get('OrderStatus') == 'AUTHORISED' and p.get('InvoiceStatus') == 'DRAFT'
        ]),
        'awaiting_delivery': len([
            p for p in active_purchases
            if p.get('OrderStatus') == 'AUTHORISED'
            and p.get('CombinedReceivingStatus') in ('NOT RECEIVED', 'PARTIALLY RECEIVED')
        ]),
    }

    metrics = {
        'status_counts': computed_counts,
        'oldest_by_status': {},
        'anomalies': {},
        'summary': {}
    }

    # Group by order status
    by_status = defaultdict(list)
    for po in active_purchases:
        status = po.get('OrderStatus', 'UNKNOWN')
        by_status[status].append(po)

    # Find oldest for each status
    for status, pos in by_status.items():
        oldest = get_oldest_date(pos, 'OrderDate')
        if oldest:
            metrics['oldest_by_status'][status] = {
                'order_number': oldest['record'].get('OrderNumber'),
                'date': oldest['date'],
                'age_days': oldest['age_days'],
                'supplier': oldest['record'].get('SupplierName', oldest['record'].get('Supplier', 'Unknown'))
            }

    # Determine current period start for prior/current split
    if report_year and report_month:
        period_start = date(report_year, report_month, 1).isoformat()
    else:
        period_start = date(today.year, today.month, 1).isoformat()

    # All authorised POs (base set for all anomaly metrics)
    authorised = [p for p in active_purchases if p.get('OrderStatus') == 'AUTHORISED']

    # Auth POs from prior periods, not invoiced
    prior_not_invoiced = [
        p for p in authorised
        if p.get('CombinedInvoiceStatus') in ('NOT INVOICED', 'PARTIALLY INVOICED')
        and (p.get('OrderDate') or '') < period_start
    ]

    # Auth POs from prior periods, not received
    prior_not_received = [
        p for p in authorised
        if p.get('CombinedReceivingStatus') in ('NOT RECEIVED', 'PARTIALLY RECEIVED')
        and (p.get('OrderDate') or '') < period_start
    ]

    # Auth POs from current period, not invoiced
    current_not_invoiced = [
        p for p in authorised
        if p.get('CombinedInvoiceStatus') in ('NOT INVOICED', 'PARTIALLY INVOICED')
        and (p.get('OrderDate') or '') >= period_start
    ]

    # Auth POs from current period, not received
    current_not_received = [
        p for p in authorised
        if p.get('CombinedReceivingStatus') in ('NOT RECEIVED', 'PARTIALLY RECEIVED')
        and (p.get('OrderDate') or '') >= period_start
    ]

    # Fully invoiced but not fully received
    fully_invoiced_not_received = [
        p for p in authorised
        if p.get('CombinedInvoiceStatus') in ('INVOICED', 'INVOICED / CREDITED')
        and p.get('CombinedReceivingStatus') in ('NOT RECEIVED', 'PARTIALLY RECEIVED')
    ]

    # Fully received but not fully invoiced
    fully_received_not_invoiced = [
        p for p in authorised
        if p.get('CombinedReceivingStatus') == 'FULLY RECEIVED'
        and p.get('CombinedInvoiceStatus') in ('NOT INVOICED', 'PARTIALLY INVOICED')
    ]

    metrics['anomalies'] = {
        'prior_not_invoiced': {
            'count': len(prior_not_invoiced),
            'oldest': get_oldest_date(prior_not_invoiced, 'OrderDate'),
            'records': prior_not_invoiced[:10]
        },
        'prior_not_received': {
            'count': len(prior_not_received),
            'oldest': get_oldest_date(prior_not_received, 'OrderDate'),
            'records': prior_not_received[:10]
        },
        'current_not_invoiced': {
            'count': len(current_not_invoiced),
            'oldest': get_oldest_date(current_not_invoiced, 'OrderDate'),
            'records': current_not_invoiced[:10]
        },
        'current_not_received': {
            'count': len(current_not_received),
            'oldest': get_oldest_date(current_not_received, 'OrderDate'),
            'records': current_not_received[:10]
        },
        'fully_invoiced_not_received': {
            'count': len(fully_invoiced_not_received),
            'oldest': get_oldest_date(fully_invoiced_not_received, 'OrderDate'),
            'records': fully_invoiced_not_received[:10]
        },
        'fully_received_not_invoiced': {
            'count': len(fully_received_not_invoiced),
            'oldest': get_oldest_date(fully_received_not_invoiced, 'OrderDate'),
            'records': fully_received_not_invoiced[:10]
        }
    }

    metrics['summary'] = {
        'total_purchases': len(purchases_data),
        'active_purchases': len(active_purchases),
        'unique_statuses': len(by_status),
        'has_anomalies': any(a['count'] > 0 for a in metrics['anomalies'].values())
    }

    return metrics


# =============================================================================
# STOCK ADJUSTMENTS & STOCKTAKES
# =============================================================================

def process_stock_adjustments(
    adjustments: List[Dict],
    adjustment_details: List[Dict]
) -> Dict[str, Any]:
    """
    Process stock adjustments and calculate discrepancies.

    Args:
        adjustments: List of stock adjustment summaries
        adjustment_details: List of detailed adjustment records with line items

    Returns:
        Dictionary with adjustment metrics
    """
    logger.info("Processing stock adjustments...")

    metrics = {
        'total_adjustments': len(adjustments),
        'by_location': defaultdict(lambda: {'qty_total': 0, 'cost_total': 0, 'count': 0}),
        'top_qty_in': [],
        'top_qty_out': [],
        'top_cost_in': [],
        'top_cost_out': [],
        'summary': {}
    }

    # Process each detailed adjustment
    # v2 spec: lines are in NewStockLines with UnitCost field
    all_lines = []
    for detail in adjustment_details:
        location = detail.get('Location', 'Unknown')
        lines = detail.get('NewStockLines') or detail.get('Lines', [])

        for line in lines:
            qty = line.get('Quantity', 0)
            cost = line.get('UnitCost') or line.get('Cost', 0)
            total_cost = qty * cost

            # Add to location totals
            metrics['by_location'][location]['count'] += 1
            metrics['by_location'][location]['qty_total'] += abs(qty)
            metrics['by_location'][location]['cost_total'] += abs(total_cost)

            # Store for top lists
            all_lines.append({
                'sku': line.get('SKU', 'Unknown'),
                'name': line.get('Name', 'Unknown'),
                'location': location,
                'quantity': qty,
                'cost': cost,
                'total_cost': total_cost,
                'date': detail.get('Date', 'Unknown')
            })

    # Get top discrepancies (excluding packaging/consumables)
    filtered_lines = [
        line for line in all_lines
        if 'packaging' not in line['name'].lower()
        and 'consumable' not in line['name'].lower()
    ]

    # Top quantity IN (positive adjustments)
    qty_in = sorted(
        [l for l in filtered_lines if l['quantity'] > 0],
        key=lambda x: x['quantity'],
        reverse=True
    )
    metrics['top_qty_in'] = qty_in[:5]

    # Top quantity OUT (negative adjustments)
    qty_out = sorted(
        [l for l in filtered_lines if l['quantity'] < 0],
        key=lambda x: abs(x['quantity']),
        reverse=True
    )
    metrics['top_qty_out'] = qty_out[:5]

    # Top cost IN
    cost_in = sorted(
        [l for l in filtered_lines if l['total_cost'] > 0],
        key=lambda x: x['total_cost'],
        reverse=True
    )
    metrics['top_cost_in'] = cost_in[:5]

    # Top cost OUT
    cost_out = sorted(
        [l for l in filtered_lines if l['total_cost'] < 0],
        key=lambda x: abs(x['total_cost']),
        reverse=True
    )
    metrics['top_cost_out'] = cost_out[:5]

    # Summary
    total_cost = sum(loc['cost_total'] for loc in metrics['by_location'].values())
    total_qty = sum(loc['qty_total'] for loc in metrics['by_location'].values())

    metrics['summary'] = {
        'total_cost_impact': total_cost,
        'total_qty_impact': total_qty,
        'locations_affected': len(metrics['by_location']),
        'total_line_items': len(all_lines)
    }

    # Convert defaultdict to regular dict
    metrics['by_location'] = dict(metrics['by_location'])

    return metrics


def process_stock_takes(
    stocktakes: List[Dict],
    stocktake_details: List[Dict],
    products: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Process stock takes and calculate discrepancies.

    Stock take lines do not include cost — cross-reference with product AverageCost.

    Args:
        stocktakes: List of stock take summaries
        stocktake_details: List of detailed stocktake records
        products: Product master data for cost lookup (optional)

    Returns:
        Dictionary with stocktake metrics
    """
    logger.info("Processing stock takes...")

    # Build SKU-to-cost lookup from product master data
    sku_to_cost: Dict[str, float] = {}
    if products:
        for p in products:
            sku = p.get('SKU', '')
            cost = p.get('AverageCost') or p.get('DefaultCost') or 0
            if sku:
                sku_to_cost[sku] = cost

    metrics = {
        'total_stocktakes': len(stocktakes),
        'by_location': defaultdict(lambda: {'qty_discrepancy': 0, 'cost_impact': 0, 'count': 0}),
        'top_discrepancies': [],
        'summary': {}
    }

    # Process detailed stocktakes
    all_discrepancies = []
    for detail in stocktake_details:
        location = detail.get('Location', 'Unknown')
        non_zero_products = detail.get('NonZeroStockOnHandProducts', [])

        for product in non_zero_products:
            qty_on_hand = product.get('QuantityOnHand', 0)
            adjustment = product.get('Adjustment', 0)
            sku = product.get('SKU', '')
            # Cost from Transactions if available, else from product lookup
            cost = sku_to_cost.get(sku, 0)

            if adjustment != 0:  # Only count actual discrepancies
                cost_impact = adjustment * cost

                metrics['by_location'][location]['count'] += 1
                metrics['by_location'][location]['qty_discrepancy'] += abs(adjustment)
                metrics['by_location'][location]['cost_impact'] += abs(cost_impact)

                all_discrepancies.append({
                    'sku': sku or 'Unknown',
                    'name': product.get('Name', 'Unknown'),
                    'location': location,
                    'qty_on_hand': qty_on_hand,
                    'adjustment': adjustment,
                    'unit_cost': cost,
                    'cost_impact': cost_impact,
                    'date': detail.get('Date', 'Unknown')
                })

    # Get top discrepancies by cost impact
    metrics['top_discrepancies'] = sorted(
        all_discrepancies,
        key=lambda x: abs(x['cost_impact']),
        reverse=True
    )[:10]

    # Summary
    total_cost = sum(loc['cost_impact'] for loc in metrics['by_location'].values())
    total_qty = sum(loc['qty_discrepancy'] for loc in metrics['by_location'].values())

    metrics['summary'] = {
        'total_cost_impact': total_cost,
        'total_qty_discrepancy': total_qty,
        'locations_affected': len(metrics['by_location']),
        'total_discrepancies': len(all_discrepancies)
    }

    metrics['by_location'] = dict(metrics['by_location'])

    return metrics


# =============================================================================
# TRANSFERS
# =============================================================================

def process_transfers(transfers_data: List[Dict]) -> Dict[str, Any]:
    """
    Process stock transfer data.

    Args:
        transfers_data: Raw transfer list from API

    Returns:
        Dictionary with transfer metrics
    """
    logger.info("Processing transfers...")

    by_status = defaultdict(list)
    for transfer in transfers_data:
        status = transfer.get('Status', 'UNKNOWN')
        by_status[status].append(transfer)

    metrics = {
        'status_counts': {status: len(transfers) for status, transfers in by_status.items()},
        'oldest_by_status': {},
        'summary': {}
    }

    # Find oldest for each status
    for status, transfers in by_status.items():
        oldest = get_oldest_date(transfers, 'DepartureDate')
        if oldest:
            metrics['oldest_by_status'][status] = {
                'transfer_number': oldest['record'].get('TaskID'),
                'date': oldest['date'],
                'age_days': oldest['age_days'],
                'from_location': oldest['record'].get('From', 'Unknown'),
                'to_location': oldest['record'].get('To', 'Unknown')
            }

    metrics['summary'] = {
        'total_transfers': len(transfers_data),
        'unique_statuses': len(by_status)
    }

    return metrics


# =============================================================================
# ASSEMBLIES & PRODUCTION
# =============================================================================

def process_assemblies(assemblies_data: List[Dict]) -> Dict[str, Any]:
    """Process assembly/finished goods data"""
    logger.info("Processing assemblies...")

    by_status = defaultdict(list)
    for assembly in assemblies_data:
        status = assembly.get('Status', 'UNKNOWN')
        by_status[status].append(assembly)

    metrics = {
        'status_counts': {status: len(assemblies) for status, assemblies in by_status.items()},
        'oldest_by_status': {},
        'records_by_status': {status: assemblies for status, assemblies in by_status.items()},
        'summary': {'total_assemblies': len(assemblies_data)}
    }

    return metrics


def process_production_orders(production_data: List[Dict]) -> Dict[str, Any]:
    """Process production order data. Filters to Type='O' (orders only, not runs)."""
    logger.info("Processing production orders...")

    # Filter to production orders only (Type='O'), exclude runs (Type='R')
    orders_only = [o for o in production_data if o.get('Type') == 'O']

    by_status = defaultdict(list)
    for order in orders_only:
        status = order.get('Status', 'UNKNOWN')
        by_status[status].append(order)

    metrics = {
        'status_counts': {status: len(orders) for status, orders in by_status.items()},
        'oldest_by_status': {},
        'records_by_status': {status: orders for status, orders in by_status.items()},
        'summary': {'total_production_orders': len(orders_only)}
    }

    return metrics


# =============================================================================
# STOCK & INVENTORY
# =============================================================================

def process_stock_availability(
    availability_data: List[Dict],
    locations: List[str],
    products: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Process product availability data for stock analysis.

    Args:
        availability_data: Raw product availability from API
        locations: List of location names
        products: Product master data with costs (optional, for value calculation)

    Returns:
        Dictionary with stock metrics per location
    """
    logger.info("Processing stock availability...")

    # Build SKU to cost lookup if products provided
    sku_to_cost = {}
    if products:
        for product in products:
            sku = product.get('SKU', '')
            # Try to get average cost, fall back to default cost
            cost = product.get('AverageCost', product.get('DefaultCost', 0))
            if sku:
                sku_to_cost[sku] = cost

    metrics = {
        'by_location': defaultdict(lambda: {
            'total_on_hand': 0,
            'total_allocated': 0,
            'total_available': 0,
            'total_value': 0,
            'product_count': 0,
            'negative_stock_items': []
        }),
        'negative_stock': [],
        'summary': {}
    }

    for item in availability_data:
        location = item.get('Location', 'Unknown')
        sku = item.get('SKU', '')
        on_hand = item.get('OnHand', 0)
        allocated = item.get('Allocated', 0)
        available = item.get('Available', 0)

        # Get cost from lookup
        cost = sku_to_cost.get(sku, 0) if sku_to_cost else 0
        value = on_hand * cost

        # Aggregate by location
        metrics['by_location'][location]['total_on_hand'] += on_hand
        metrics['by_location'][location]['total_allocated'] += allocated
        metrics['by_location'][location]['total_available'] += available
        metrics['by_location'][location]['total_value'] += value
        metrics['by_location'][location]['product_count'] += 1

        # Track negative stock
        if on_hand < 0 or available < 0:
            neg_item = {
                'sku': item.get('SKU', 'Unknown'),
                'name': item.get('Name', 'Unknown'),
                'location': location,
                'on_hand': on_hand,
                'available': available
            }
            metrics['negative_stock'].append(neg_item)
            metrics['by_location'][location]['negative_stock_items'].append(neg_item)

    # Summary
    total_value = sum(loc['total_value'] for loc in metrics['by_location'].values())
    metrics['summary'] = {
        'total_locations': len(metrics['by_location']),
        'total_negative_items': len(metrics['negative_stock']),
        'has_negative_stock': len(metrics['negative_stock']) > 0,
        'total_stock_value': total_value
    }

    metrics['by_location'] = dict(metrics['by_location'])

    return metrics


# =============================================================================
# DATA HYGIENE
# =============================================================================

def process_data_hygiene(
    products: List[Dict],
    customers: Optional[List[Dict]] = None,
    suppliers: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Check for data quality issues in master data.

    Args:
        products: Product master data
        customers: Customer master data (optional)
        suppliers: Supplier master data (optional)

    Returns:
        Dictionary with data hygiene issues
    """
    logger.info("Processing data hygiene checks...")

    metrics = {
        'products': {
            'no_price': [],     # Sellable products with no retail price
            'no_barcode': [],   # Sellable products with no barcode
        },
        'customers': {
            'missing_email': [],
            'missing_phone': [],
            'missing_payment_terms': [],
            'on_credit_hold': [],
        },
        'suppliers': {
            'missing_email': [],
            'missing_phone': [],
            'missing_payment_terms': [],
        },
        'summary': {}
    }

    # Check products — only sellable items
    for product in products:
        sku = product.get('SKU', 'Unknown')
        name = product.get('Name', 'Unknown')
        is_sellable = product.get('Sellable', False)

        if is_sellable:
            # No retail price set
            has_price = any(product.get(f'PriceTier{i}', 0) > 0 for i in range(1, 11))
            if not has_price:
                metrics['products']['no_price'].append({'sku': sku, 'name': name})

            # No barcode
            if not product.get('Barcode'):
                metrics['products']['no_barcode'].append({'sku': sku, 'name': name})

    # Check customers
    # NOTE: Contacts are in a nested 'Contacts' array, NOT top-level fields
    if customers:
        for customer in customers:
            name = customer.get('Name', 'Unknown')
            contacts = customer.get('Contacts', []) or []

            has_email = any(c.get('Email') for c in contacts)
            has_phone = any(c.get('Phone') or c.get('MobilePhone') for c in contacts)

            if not has_email:
                metrics['customers']['missing_email'].append({'name': name})

            if not has_phone:
                metrics['customers']['missing_phone'].append({'name': name})

            if not customer.get('PaymentTerm'):
                metrics['customers']['missing_payment_terms'].append({'name': name})

            if customer.get('IsOnCreditHold'):
                metrics['customers']['on_credit_hold'].append({'name': name})

    # Check suppliers
    # NOTE: Contacts are in a nested 'Contacts' array, NOT top-level fields
    if suppliers:
        for supplier in suppliers:
            name = supplier.get('Name', 'Unknown')
            contacts = supplier.get('Contacts', []) or []

            has_email = any(c.get('Email') for c in contacts)
            has_phone = any(c.get('Phone') or c.get('MobilePhone') for c in contacts)

            if not has_email:
                metrics['suppliers']['missing_email'].append({'name': name})

            if not has_phone:
                metrics['suppliers']['missing_phone'].append({'name': name})

            if not supplier.get('PaymentTerm'):
                metrics['suppliers']['missing_payment_terms'].append({'name': name})

    # Summary counts
    metrics['summary'] = {
        'products_no_price': len(metrics['products']['no_price']),
        'products_no_barcode': len(metrics['products']['no_barcode']),
        'customers_missing_email': len(metrics['customers']['missing_email']),
        'customers_missing_phone': len(metrics['customers']['missing_phone']),
        'customers_missing_payment_terms': len(metrics['customers']['missing_payment_terms']),
        'customers_on_credit_hold': len(metrics['customers']['on_credit_hold']),
        'suppliers_missing_email': len(metrics['suppliers']['missing_email']),
        'suppliers_missing_phone': len(metrics['suppliers']['missing_phone']),
        'suppliers_missing_payment_terms': len(metrics['suppliers']['missing_payment_terms']),
        'total_issues': (
            len(metrics['products']['no_price']) +
            len(metrics['products']['no_barcode']) +
            len(metrics['customers']['missing_email']) +
            len(metrics['customers']['missing_phone']) +
            len(metrics['customers']['missing_payment_terms']) +
            len(metrics['customers']['on_credit_hold']) +
            len(metrics['suppliers']['missing_email']) +
            len(metrics['suppliers']['missing_phone']) +
            len(metrics['suppliers']['missing_payment_terms'])
        )
    }

    return metrics


# =============================================================================
# CREDIT NOTES
# =============================================================================

def process_credit_notes(
    sale_credit_notes: List[Dict],
    purchase_credit_notes: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Process credit note data.

    Args:
        sale_credit_notes: Sale credit notes
        purchase_credit_notes: Purchase credit notes (optional)

    Returns:
        Dictionary with credit note metrics
    """
    logger.info("Processing credit notes...")

    metrics = {
        'sales': {
            'count': len(sale_credit_notes),
            'total_value': sum(cn.get('Total', 0) for cn in sale_credit_notes),
            'recent': sale_credit_notes[:10]  # Most recent 10
        },
        'purchases': {
            'count': len(purchase_credit_notes) if purchase_credit_notes else 0,
            'total_value': sum(cn.get('Total', 0) for cn in purchase_credit_notes) if purchase_credit_notes else 0,
            'recent': purchase_credit_notes[:10] if purchase_credit_notes else []
        },
        'summary': {}
    }

    metrics['summary'] = {
        'total_sale_credit_notes': metrics['sales']['count'],
        'total_sale_credit_value': metrics['sales']['total_value'],
        'total_purchase_credit_notes': metrics['purchases']['count'],
        'total_purchase_credit_value': metrics['purchases']['total_value']
    }

    return metrics


# =============================================================================
# OVERALL HEALTH SCORE
# =============================================================================

def process_sync_errors(sync_error_df) -> Dict[str, Any]:
    """
    Process sync error data from uploaded XLSX file.

    The XLSX file typically has headers starting around row 7.
    Columns: Status, Type, Document Info, etc.

    Possible Status values: Failed, Skipped, Warning, Pending
    Possible Type values: Invoice, Attachment, Credit Note, Financial Journal, Product, Payment, Contact

    Args:
        sync_error_df: Pandas DataFrame from uploaded XLSX (already skipped header rows)

    Returns:
        Dictionary with sync error metrics
    """
    logger.info("Processing sync errors...")

    if sync_error_df is None or sync_error_df.empty:
        return {
            'total_errors': 0,
            'by_status': {},
            'by_type': {},
            'by_status_and_type': {},
            'summary': {}
        }

    # Clean column names (strip whitespace)
    sync_error_df.columns = sync_error_df.columns.str.strip()

    metrics = {
        'total_errors': len(sync_error_df),
        'by_status': {},
        'by_type': {},
        'by_status_and_type': {},
        'recent_errors': [],
        'summary': {}
    }

    # Count by Status
    if 'Status' in sync_error_df.columns:
        status_counts = sync_error_df['Status'].value_counts().to_dict()
        metrics['by_status'] = {str(k): int(v) for k, v in status_counts.items()}

    # Count by Type
    if 'Type' in sync_error_df.columns:
        type_counts = sync_error_df['Type'].value_counts().to_dict()
        metrics['by_type'] = {str(k): int(v) for k, v in type_counts.items()}

    # Cross-tabulation: Status x Type
    if 'Status' in sync_error_df.columns and 'Type' in sync_error_df.columns:
        crosstab = sync_error_df.groupby(['Status', 'Type']).size().to_dict()
        metrics['by_status_and_type'] = {f"{status}_{type}": count for (status, type), count in crosstab.items()}

    # Get recent errors (top 20)
    metrics['recent_errors'] = sync_error_df.head(20).to_dict('records')

    # Summary
    metrics['summary'] = {
        'total_errors': len(sync_error_df),
        'failed_count': metrics['by_status'].get('Failed', 0),
        'warning_count': metrics['by_status'].get('Warning', 0),
        'skipped_count': metrics['by_status'].get('Skipped', 0),
        'pending_count': metrics['by_status'].get('Pending', 0),
        'has_critical_errors': metrics['by_status'].get('Failed', 0) > 0
    }

    return metrics


def calculate_health_score(all_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate an overall health score based on all metrics.

    RAG (Red/Amber/Green) scoring for each section.

    Args:
        all_metrics: Dictionary containing all processed metrics

    Returns:
        Health score breakdown with RAG status per section
    """
    logger.info("Calculating health score...")

    score = {
        'sections': {},
        'overall': {
            'score': 0,
            'max_score': 0,
            'percentage': 0,
            'status': 'GREEN'
        }
    }

    # Define thresholds and scoring
    thresholds = {
        'negative_stock': {'green': 0, 'amber': 5, 'points': 15},
        'draft_orders': {'green': 5, 'amber': 20, 'points': 10},
        'old_orders': {'green': 0, 'amber': 5, 'points': 15},
        'data_hygiene': {'green': 10, 'amber': 50, 'points': 10},
        'anomalies': {'green': 0, 'amber': 5, 'points': 20}
    }

    # TODO: Implement actual scoring logic based on metrics
    # This is a placeholder structure

    return score
