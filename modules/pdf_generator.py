"""
PDF Generator Module

Generates branded health check PDFs matching the Finovate report style.
Uses xhtml2pdf for HTML/CSS to PDF conversion.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from io import BytesIO
import logging
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

# Finovate Brand Colors
COLOR_DARK_BLUE = "#1e3a5f"  # Dark blue for headers
COLOR_NAVY = "#2c3e50"       # Navy for table headers
COLOR_RED = "#d32f2f"        # Red for ACTION blocks
COLOR_ORANGE = "#ff6600"     # Orange accents
COLOR_GREY = "#666666"       # Grey text
COLOR_LIGHT_GREY = "#f5f5f5" # Light grey backgrounds


class HealthCheckPDFGenerator:
    """
    Generates branded PDF health check reports using xhtml2pdf.
    Matches the Finovate report style from existing templates.
    """

    def __init__(self, client_name: str, report_period: str, logo_path: Optional[str] = None):
        """
        Initialize PDF generator.

        Args:
            client_name: Name of the client
            report_period: Report period (e.g., "January 2024")
            logo_path: Path to Finovate logo (optional)
        """
        self.client_name = client_name
        self.report_period = report_period
        self.logo_path = logo_path

    def generate(self, metrics: Dict[str, Any], sections_included: Dict[str, bool]) -> BytesIO:
        """
        Generate PDF report from processed metrics.

        Args:
            metrics: Dictionary of all processed health check metrics
            sections_included: Dict of which sections to include

        Returns:
            BytesIO buffer containing PDF data
        """
        logger.info(f"Generating PDF for {self.client_name} - {self.report_period}")

        # Build HTML content with embedded CSS
        html_content = self._build_html(metrics, sections_included)

        # Generate PDF using xhtml2pdf
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(
            html_content,
            dest=pdf_buffer
        )

        if pisa_status.err:
            logger.error(f"PDF generation failed with error code: {pisa_status.err}")
            raise Exception(f"PDF generation failed: {pisa_status.err}")

        pdf_buffer.seek(0)
        logger.info("PDF generated successfully")
        return pdf_buffer

    def _get_css(self) -> str:
        """Get CSS styling for the PDF (xhtml2pdf compatible)"""
        return f"""
        @page {{
            size: a4;
            margin: 2cm 1.5cm;
        }}

        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 10pt;
            color: #333;
            line-height: 1.5;
        }}

        .header {{
            text-align: right;
            font-size: 8pt;
            color: {COLOR_GREY};
            margin-bottom: 20px;
        }}

        .logo {{
            max-width: 150px;
            float: right;
        }}

        h1 {{
            color: {COLOR_DARK_BLUE};
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 30px;
            clear: both;
            border-bottom: 2px solid {COLOR_DARK_BLUE};
            padding-bottom: 10px;
        }}

        h2 {{
            color: {COLOR_DARK_BLUE};
            font-size: 13pt;
            font-weight: bold;
            margin-top: 30px;
            margin-bottom: 15px;
        }}

        h3 {{
            color: {COLOR_DARK_BLUE};
            font-size: 11pt;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
        }}

        .why {{
            font-style: italic;
            margin-bottom: 20px;
            color: {COLOR_GREY};
        }}

        .why-label {{
            text-decoration: underline;
            font-weight: bold;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}

        th {{
            background-color: {COLOR_NAVY};
            color: white;
            padding: 10px 12px;
            text-align: left;
            font-weight: bold;
            font-size: 9pt;
        }}

        td {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            font-size: 9pt;
        }}

        tr:nth-child(even) {{
            background-color: {COLOR_LIGHT_GREY};
        }}

        .action-block {{
            background-color: #fff5f5;
            border-left: 4px solid {COLOR_RED};
            padding: 15px;
            margin: 20px 0;
        }}

        .action-label {{
            color: {COLOR_RED};
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 10px;
        }}

        .action-block ul {{
            margin: 5px 0 5px 20px;
            padding: 0;
        }}

        .action-block li {{
            margin: 5px 0;
            color: {COLOR_RED};
        }}

        .highlight {{
            background-color: #ffeb3b;
            padding: 2px 4px;
        }}

        .note {{
            font-style: italic;
            font-size: 9pt;
            color: {COLOR_GREY};
            margin: 10px 0;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .metric-value {{
            font-weight: bold;
            color: {COLOR_DARK_BLUE};
        }}

        .warning {{
            color: {COLOR_RED};
            font-weight: bold;
        }}

        .success {{
            color: #4caf50;
            font-weight: bold;
        }}
        """

    def _build_html(self, metrics: Dict[str, Any], sections_included: Dict[str, bool]) -> str:
        """Build complete HTML document with embedded CSS"""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{self.client_name} - Cin7 Core Health Check - {self.report_period}</title>
            <style>
                {self._get_css()}
            </style>
        </head>
        <body>
            <div class="header">
                <strong>Finovate</strong><br>
                <small>BUSINESS GROWTH STEWARDSHIP</small>
            </div>

            <h1>{self.client_name} - Cin7 Core Health Check – {self.report_period}</h1>
        """

        # Add sections based on what's included

        # Sync Errors (Section 1) - if uploaded
        if 'sync_errors' in metrics:
            html += self._build_sync_errors_section(metrics['sync_errors'])

        if sections_included.get('sales') and 'sales' in metrics:
            html += self._build_sales_section(metrics['sales'])

        if sections_included.get('purchases') and 'purchases' in metrics:
            html += self._build_purchases_section(metrics['purchases'])

        if sections_included.get('stock_adjustments') and 'stock_adjustments' in metrics:
            html += self._build_stock_adjustments_section(metrics['stock_adjustments'])

        if sections_included.get('stock_takes') and 'stock_takes' in metrics:
            html += self._build_stock_takes_section(metrics['stock_takes'])

        if sections_included.get('transfers') and 'transfers' in metrics:
            html += self._build_transfers_section(metrics['transfers'])

        if sections_included.get('assemblies') and 'assemblies' in metrics:
            html += self._build_assemblies_section(metrics.get('assemblies'), metrics.get('production'))

        if sections_included.get('stock_per_location') and 'stock_availability' in metrics:
            html += self._build_stock_per_location_section(metrics['stock_availability'])

        if sections_included.get('data_hygiene') and 'data_hygiene' in metrics:
            html += self._build_data_hygiene_section(metrics['data_hygiene'])

        html += """
        </body>
        </html>
        """

        return html

    def _build_sync_errors_section(self, sync_metrics: Dict[str, Any]) -> str:
        """Build Xero/QBO Sync Errors section"""
        html = """
        <div class="section">
            <h2>1. C7C-Xero sync errors</h2>
            <p class="why">
                <span class="why-label">Why:</span> Ensures that C7C and Xero are in sync and can be reconciled. Workflow and system usage issues,
                which result in the sync errors, may be highlighted.
            </p>

            <table>
                <tr>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Count</th>
                </tr>
        """

        # Group by Type and Status
        by_type = sync_metrics.get('by_type', {})
        by_status = sync_metrics.get('by_status', {})

        # Show errors by type
        for error_type, count in by_type.items():
            html += f"""
                <tr>
                    <td>{error_type}</td>
                    <td>Failed</td>
                    <td class="metric-value">{count}</td>
                </tr>
            """

        html += """
            </table>

            <h3>Other Sync Statuses to be aware of:</h3>
            <table>
                <tr>
                    <th>Status</th>
                    <th>Count</th>
                    <th>Notes</th>
                </tr>
        """

        # Show by status
        for status, count in by_status.items():
            if status != 'Failed':
                html += f"""
                <tr>
                    <td>{status}</td>
                    <td class="metric-value">{count}</td>
                    <td></td>
                </tr>
                """

        html += """
            </table>

            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li>Work through the sync errors and resolve them.</li>
                    <li>Certain sync errors may be Skipped but be sure that this is the best course of action.</li>
                    <li>We recommend keeping a log of Skipped transactions so that there is an audit trail for these. Unfortunately, there is no functionality for this in Core, and therefore the log must be kept outside of Core.</li>
                    <li>Please see the Xero Synchronisation Report in the Reports module to assist with this.</li>
                    <li>If you are unsure or need assistance, please contact the Finovate team.</li>
                </ul>
            </div>
        </div>
        """

        return html

    def _build_sales_section(self, sales_metrics: Dict[str, Any]) -> str:
        """Build Sales section"""
        html = """
        <div class="section">
            <h2>4. Sales</h2>
            <p class="why">
                <span class="why-label">Why:</span> Prevents SO statuses from falling behind by putting a number to orders in various statuses,
                as well as highlighting aged SOs that may have been forgotten. This in turn helps to ensure stock and A/R accuracy.
            </p>

            <h3>1. Sales statuses: directly from the Sales dashboard</h3>
            <table>
                <tr>
                    <th>SO Status</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
        """

        # Add status counts
        counts = sales_metrics.get('status_counts', {})
        oldest = sales_metrics.get('oldest_by_status', {})

        # Draft quotes
        draft_count = counts.get('draft_quotes', 0)
        oldest_draft = oldest.get('DRAFT', {}).get('date', 'N/A') if 'DRAFT' in oldest else 'N/A'
        html += f"""
                <tr>
                    <td>Draft quotes</td>
                    <td>Unauthorised Quotes</td>
                    <td class="metric-value">{draft_count}</td>
                    <td>Oldest date {oldest_draft}</td>
                </tr>
        """

        # Backordered
        backorder_count = counts.get('backordered', 0)
        html += f"""
                <tr>
                    <td>Backordered</td>
                    <td>Backordered items</td>
                    <td class="metric-value">{backorder_count}</td>
                    <td>All in current period</td>
                </tr>
        """

        # Awaiting fulfilment
        awaiting_ful = counts.get('awaiting_fulfilment', 0)
        html += f"""
                <tr>
                    <td>Awaiting fulfilment</td>
                    <td>Authorised SOs with no authorised Shipment</td>
                    <td class="metric-value">{awaiting_ful}</td>
                    <td>All in current period</td>
                </tr>
        """

        # Orders to bill
        to_bill = counts.get('orders_to_bill', 0)
        html += f"""
                <tr>
                    <td>Orders to bill</td>
                    <td>Authorised SOs with no authorised Invoice</td>
                    <td class="metric-value">{to_bill}</td>
                    <td></td>
                </tr>
        """

        html += """
            </table>

            <h3>2. Sales metrics</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
        """

        # Anomalies
        anomalies = sales_metrics.get('anomalies', {})

        fulfilled_not_inv = anomalies.get('fulfilled_not_invoiced', {})
        html += f"""
                <tr>
                    <td>Fulfilled SOs not invoiced</td>
                    <td class="metric-value">{fulfilled_not_inv.get('count', 0)}</td>
                    <td>Oldest SO date {fulfilled_not_inv.get('oldest', {}).get('date', 'N/A') if fulfilled_not_inv.get('oldest') else 'N/A'}</td>
                </tr>
        """

        invoiced_not_ful = anomalies.get('invoiced_not_fulfilled', {})
        html += f"""
                <tr>
                    <td>Invoiced SOs not fulfilled</td>
                    <td class="metric-value">{invoiced_not_ful.get('count', 0)}</td>
                    <td>Oldest date {invoiced_not_ful.get('oldest', {}).get('date', 'N/A') if invoiced_not_ful.get('oldest') else 'N/A'}</td>
                </tr>
        """

        html += """
            </table>

            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li>Use the filters on your Sales Dashboard to go through each of these categories and determine whether the orders in each status should be there. Start with the oldest orders.</li>
                    <li>If not, clear orders that should not be there:
                        <ul>
                            <li>Reject/Void old draft quotes or old draft sales orders.</li>
                            <li>Authorise invoices, if relevant.</li>
                            <li>Fulfil orders, if relevant.</li>
                            <li>Mark closed orders as Complete/Received.</li>
                        </ul>
                    </li>
                    <li>If you are unsure or need assistance, please contact the Finovate team.</li>
                </ul>
            </div>
        </div>
        """

        return html

    def _build_purchases_section(self, purchase_metrics: Dict[str, Any]) -> str:
        """Build Purchases section"""
        html = """
        <div class="section">
            <h2>3. Purchases</h2>
            <p class="why">
                <span class="why-label">Why:</span> Prevents PO statuses from falling behind by putting a number to orders in various statuses and highlighting aged POs that may have been forgotten. This in turn helps to ensure stock and A/P accuracy.
            </p>

            <h3>1. Purchase statuses: directly from the Purchase dashboard</h3>
            <table>
                <tr>
                    <th>PO Status</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
        """

        counts = purchase_metrics.get('status_counts', {})
        oldest = purchase_metrics.get('oldest_by_status', {})

        # Draft orders
        draft_count = counts.get('draft', 0)
        oldest_draft = oldest.get('DRAFT', {}).get('date', 'N/A') if 'DRAFT' in oldest else 'N/A'
        html += f"""
                <tr>
                    <td>Draft orders</td>
                    <td>Unauthorised POs</td>
                    <td class="metric-value">{draft_count}</td>
                    <td>Oldest date {oldest_draft}</td>
                </tr>
        """

        # Authorised
        auth_count = counts.get('authorised', 0)
        html += f"""
                <tr>
                    <td>Authorised</td>
                    <td>Authorised POs</td>
                    <td class="metric-value">{auth_count}</td>
                    <td></td>
                </tr>
        """

        html += """
            </table>

            <h3>2. Purchase metrics</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
        """

        # Anomalies
        anomalies = purchase_metrics.get('anomalies', {})

        auth_not_inv = anomalies.get('authorised_not_invoiced', {})
        html += f"""
                <tr>
                    <td>Authorised POs from prior periods, not invoiced</td>
                    <td class="metric-value">{auth_not_inv.get('count', 0)}</td>
                    <td>Oldest date {auth_not_inv.get('oldest', {}).get('date', 'N/A') if auth_not_inv.get('oldest') else 'N/A'}. May include partially invoiced orders.</td>
                </tr>
        """

        auth_not_rec = anomalies.get('authorised_not_received', {})
        html += f"""
                <tr>
                    <td>Authorised POs from prior periods, not received</td>
                    <td class="metric-value">{auth_not_rec.get('count', 0)}</td>
                    <td>Oldest date {auth_not_rec.get('oldest', {}).get('date', 'N/A') if auth_not_rec.get('oldest') else 'N/A'}. May include partially received orders.</td>
                </tr>
        """

        inv_not_rec = anomalies.get('invoiced_not_received', {})
        html += f"""
                <tr>
                    <td>Authorised POs fully invoiced, not fully received</td>
                    <td class="metric-value">{inv_not_rec.get('count', 0)}</td>
                    <td>Oldest date {inv_not_rec.get('oldest', {}).get('date', 'N/A') if inv_not_rec.get('oldest') else 'N/A'}.</td>
                </tr>
        """

        rec_not_inv = anomalies.get('received_not_invoiced', {})
        html += f"""
                <tr>
                    <td>Authorised POs fully received, not fully invoiced</td>
                    <td class="metric-value">{rec_not_inv.get('count', 0)}</td>
                    <td>Oldest date {rec_not_inv.get('oldest', {}).get('date', 'N/A') if rec_not_inv.get('oldest') else 'N/A'}.</td>
                </tr>
        """

        html += """
            </table>

            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li>Sense check whether the number of orders in these categories is likely. Take note of the oldest date as well.</li>
                    <li>Action as required: Invoice, Receive, Close, or Void.</li>
                    <li>If you are unsure or need assistance, please contact the Finovate team.</li>
                </ul>
            </div>
        </div>
        """

        return html

    def _build_stock_adjustments_section(self, adj_metrics: Dict[str, Any]) -> str:
        """Build Stock Adjustments section"""
        html = """
        <div class="section">
            <h2>2. Sense-check of monthly stocktake / adjustments</h2>
            <p class="why">
                <span class="why-label">Why:</span> Prevents major stocktake errors from being overlooked, allowing them to be rectified before closing the month.
            </p>

            <h3>1. Total quantity and cost discrepancies per Location</h3>
            <table>
                <tr>
                    <th>Reference type</th>
                    <th>Location</th>
                    <th>Total Cost Discrepancy</th>
                </tr>
        """

        # Add location summaries
        by_location = adj_metrics.get('by_location', {})
        for location, data in by_location.items():
            cost_total = data.get('cost_total', 0)
            html += f"""
                <tr>
                    <td>StockAdjustment</td>
                    <td>{location}</td>
                    <td class="metric-value">R{cost_total:,.2f}</td>
                </tr>
            """

        html += """
            </table>

            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li>Be aware of the inventory discrepancy created by the stock takes – was it expected?</li>
                    <li>Be aware of the quantity of items that were either more or less than expected by the system – do you know why this is happening?</li>
                    <li>Are there workflow issues that could be causing large discrepancies?</li>
                    <li>Take note of the items with the largest quantity and cost discrepancies – can you explain why this happened?</li>
                </ul>
            </div>
        </div>
        """

        return html

    def _build_stock_takes_section(self, st_metrics: Dict[str, Any]) -> str:
        """Build Stock Takes section (combined with adjustments)"""
        return ""  # Combined with adjustments section

    def _build_transfers_section(self, transfer_metrics: Dict[str, Any]) -> str:
        """Build Transfers section"""
        html = """
        <div class="section">
            <h2>6. Transfers</h2>
            <p class="why">
                <span class="why-label">Why:</span> Prevents Transfer statuses from falling behind by putting a number to transfers in various statuses, as well as highlighting aged Transfers that may have been forgotten or duplicate Transfers. This in turn helps to ensure stock accuracy.
            </p>

            <h3>1. Transfer statuses</h3>
            <table>
                <tr>
                    <th>Transfer Status</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
        """

        counts = transfer_metrics.get('status_counts', {})
        oldest = transfer_metrics.get('oldest_by_status', {})

        # Draft
        draft_count = counts.get('DRAFT', 0)
        oldest_draft = oldest.get('DRAFT', {}).get('date', 'N/A') if 'DRAFT' in oldest else 'N/A'
        html += f"""
                <tr>
                    <td>Draft</td>
                    <td>Unauthorised Transfers</td>
                    <td class="metric-value">{draft_count}</td>
                    <td>Oldest date {oldest_draft}</td>
                </tr>
        """

        # In Transit
        in_transit = counts.get('IN TRANSIT', 0)
        html += f"""
                <tr>
                    <td>In Transit</td>
                    <td>Stock has been Sent, but not Received (Completed)</td>
                    <td class="metric-value">{in_transit}</td>
                    <td></td>
                </tr>
        """

        html += """
            </table>

            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li>Ensure Draft Transfers should be in Draft status, else authorize or Void them. Start with the oldest ones.</li>
                    <li>Ensure In Transit Transfers should not have been Completed.</li>
                    <li>If you are unsure or need assistance, please contact the Finovate team.</li>
                </ul>
            </div>
        </div>
        """

        return html

    def _build_assemblies_section(self, assembly_metrics: Optional[Dict], production_metrics: Optional[Dict]) -> str:
        """Build Assemblies & Production section"""
        if not assembly_metrics and not production_metrics:
            return ""

        html = """
        <div class="section">
            <h2>5. Assemblies and Production Orders</h2>
            <p class="why">
                <span class="why-label">Why:</span> Prevents Assembly and Production Order statuses from falling behind by putting a number to orders in various statuses, as well as highlighting aged Orders that may have been forgotten or duplicate Orders. This in turn helps to ensure stock accuracy.
            </p>
        """

        if assembly_metrics:
            html += """
            <h3>1. Assembly statuses</h3>
            <table>
                <tr>
                    <th>Assembly Status</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
            """

            counts = assembly_metrics.get('status_counts', {})
            for status, count in counts.items():
                html += f"""
                <tr>
                    <td>{status}</td>
                    <td></td>
                    <td class="metric-value">{count}</td>
                    <td></td>
                </tr>
                """

            html += "</table>"

        if production_metrics:
            html += """
            <h3>2. Production Order statuses</h3>
            <table>
                <tr>
                    <th>Production Status</th>
                    <th>Description</th>
                    <th>Quantity</th>
                    <th>Notes</th>
                </tr>
            """

            counts = production_metrics.get('status_counts', {})
            for status, count in counts.items():
                html += f"""
                <tr>
                    <td>{status}</td>
                    <td></td>
                    <td class="metric-value">{count}</td>
                    <td></td>
                </tr>
                """

            html += "</table>"

        html += """
            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li>Ensure Draft orders should be in Draft status, else authorize or Void them. Start with the oldest ones.</li>
                    <li>Ensure Authorised orders are awaiting completion. If not, Void them. Start with the oldest ones.</li>
                    <li>Ensure Work-in-Progress orders should not have been Completed.</li>
                </ul>
            </div>
        </div>
        """

        return html

    def _build_stock_per_location_section(self, stock_metrics: Dict[str, Any]) -> str:
        """Build Stock per Location section"""
        html = """
        <div class="section">
            <h2>7. Stock per Location</h2>
            <p class="why">
                <span class="why-label">Why:</span> May highlight where stock is incorrectly lying in the system.
            </p>

            <table>
                <tr>
                    <th>Location</th>
                    <th>Total Quantity on Hand</th>
                    <th>Stock on Hand Value</th>
                </tr>
        """

        by_location = stock_metrics.get('by_location', {})
        for location, data in by_location.items():
            on_hand = data.get('total_on_hand', 0)
            total_value = data.get('total_value', 0)
            html += f"""
                <tr>
                    <td>{location}</td>
                    <td class="metric-value">{on_hand:,.2f}</td>
                    <td class="metric-value">R{total_value:,.2f}</td>
                </tr>
            """

        html += """
            </table>
        </div>
        """

        return html

    def _build_data_hygiene_section(self, hygiene_metrics: Dict[str, Any]) -> str:
        """Build Data Quality/Hygiene section"""
        html = """
        <div class="section">
            <h2>8. Data Quality & Hygiene</h2>
            <p class="why">
                <span class="why-label">Why:</span> Ensures master data quality which impacts reporting accuracy,
                customer/supplier communication, and inventory costing. Clean data is essential for reliable business decisions.
            </p>

            <h3>Summary</h3>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Issue Type</th>
                    <th>Count</th>
                </tr>
        """

        # Product issues
        summary = hygiene_metrics.get('summary', {})
        html += f"""
                <tr>
                    <td>Products</td>
                    <td>No Price Set</td>
                    <td class="metric-value">{summary.get('products_no_price', 0)}</td>
                </tr>
                <tr>
                    <td>Products</td>
                    <td>No Category</td>
                    <td class="metric-value">{summary.get('products_no_category', 0)}</td>
                </tr>
        """

        # Customer issues
        html += f"""
                <tr>
                    <td>Customers</td>
                    <td>Missing Email</td>
                    <td class="metric-value">{summary.get('customers_missing_email', 0)}</td>
                </tr>
                <tr>
                    <td>Customers</td>
                    <td>Missing Contact Person</td>
                    <td class="metric-value">{len(hygiene_metrics.get('customers', {}).get('missing_contact', []))}</td>
                </tr>
        """

        # Supplier issues
        html += f"""
                <tr>
                    <td>Suppliers</td>
                    <td>Missing Email</td>
                    <td class="metric-value">{summary.get('suppliers_missing_email', 0)}</td>
                </tr>
        """

        html += """
            </table>

            <div class="action-block">
                <div class="action-label">ACTION:</div>
                <ul>
                    <li><strong>Products:</strong> Set prices for all products to ensure accurate quoting and invoicing. Assign categories to products for better organization and reporting.</li>
                    <li><strong>Customers:</strong> Update contact email addresses for invoicing and communication. Add contact person names for better relationship management.</li>
                    <li><strong>Suppliers:</strong> Ensure all supplier email addresses are complete to avoid communication delays and order issues.</li>
                    <li>Export the detailed data quality reports from the app for a complete list of affected records.</li>
                </ul>
            </div>
        </div>
        """

        return html


def generate_health_check_pdf(
    client_name: str,
    report_period: str,
    all_metrics: Dict[str, Any],
    sections_included: Dict[str, bool],
    output_path: Optional[str] = None
) -> BytesIO:
    """
    Generate a complete health check PDF.

    Args:
        client_name: Client name
        report_period: Report period (e.g., "January 2024")
        all_metrics: All processed metrics from data_processing module
        sections_included: Dict of which sections to include
        output_path: Optional path to save PDF file

    Returns:
        BytesIO buffer with PDF data
    """
    generator = HealthCheckPDFGenerator(client_name, report_period)
    pdf_buffer = generator.generate(all_metrics, sections_included)

    # Optionally save to file
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        logger.info(f"PDF saved to {output_path}")

    pdf_buffer.seek(0)
    return pdf_buffer


def format_currency(value: float) -> str:
    """Format value as South African Rand"""
    return f"R{value:,.2f}"


def format_age_days(days: int) -> str:
    """Format age in days"""
    if days == 0:
        return "Today"
    elif days == 1:
        return "1 day"
    else:
        return f"{days} days"
