"""
Cin7 Core Health Check Automation - Streamlit App

Main application for generating automated health check reports for Cin7 Core clients.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from modules.api_client import Cin7APIClient, Cin7APIError
from modules.data_processing import (
    process_sales_metrics,
    process_purchase_metrics,
    process_stock_adjustments,
    process_stock_takes,
    process_transfers,
    process_assemblies,
    process_production_orders,
    process_stock_availability,
    process_data_hygiene,
    process_credit_notes,
    process_sync_errors
)
from modules.pdf_generator import generate_health_check_pdf, format_currency, format_age_days
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Cin7 Core Health Check",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #003366;
        font-weight: bold;
    }
    .section-header {
        font-size: 1.5rem;
        color: #FF6600;
        font-weight: bold;
        margin-top: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF6600;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

if 'client' not in st.session_state:
    st.session_state.client = None

if 'metrics' not in st.session_state:
    st.session_state.metrics = {}

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False


# =============================================================================
# SIDEBAR - CLIENT SETUP
# =============================================================================

with st.sidebar:
    st.markdown('<p class="main-header">🏥 Health Check</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.subheader("1. Client Setup")

    # Client selection
    client_number = st.number_input(
        "Client Number",
        min_value=1,
        max_value=10,
        value=1,
        help="Client number from .env file (CLIENT_1_, CLIENT_2_, etc.)"
    )

    # Report period
    col1, col2 = st.columns(2)
    with col1:
        report_month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=datetime.now().month - 1,
            format_func=lambda x: datetime(2000, x, 1).strftime('%B')
        )
    with col2:
        report_year = st.number_input(
            "Year",
            min_value=2020,
            max_value=2030,
            value=datetime.now().year
        )

    report_period = f"{datetime(report_year, report_month, 1).strftime('%B %Y')}"

    st.markdown("---")
    st.subheader("2. Sections to Include")

    sections = {
        'sales': st.checkbox("Sales Orders", value=True),
        'purchases': st.checkbox("Purchase Orders", value=True),
        'stock_adjustments': st.checkbox("Stock Adjustments", value=True),
        'stock_takes': st.checkbox("Stock Takes", value=True),
        'transfers': st.checkbox("Transfers", value=True),
        'assemblies': st.checkbox("Assemblies & Production", value=False),
        'stock_per_location': st.checkbox("Stock per Location", value=True),
        'data_hygiene': st.checkbox("Data Hygiene", value=False),
        'credit_notes': st.checkbox("Credit Notes", value=False),
    }

    st.markdown("---")
    st.subheader("3. Sync Errors (Optional)")

    st.info("💡 Upload the Xero/QBO Synchronisation report (XLSX) from Cin7 Core")

    sync_file = st.file_uploader(
        "Upload Sync Error Report",
        type=['xlsx'],
        help="Export from Cin7: Reports > Xero/QBO Synchronisation Report"
    )

    st.markdown("---")

    # Action buttons
    if st.button("🔄 Load Data from Cin7", type="primary", use_container_width=True):
        with st.spinner("Connecting to Cin7 Core API..."):
            try:
                # Initialize client
                st.session_state.client = Cin7APIClient(client_number=client_number)
                st.success(f"✓ Connected to {st.session_state.client.client_name}")

                # Load data for selected sections
                st.session_state.metrics = {}
                progress_bar = st.progress(0)
                total_sections = sum(sections.values())
                current = 0

                # Sales
                if sections['sales']:
                    with st.spinner("Loading sales data..."):
                        sales_counts = st.session_state.client.get_sale_status_counts()
                        all_sales = st.session_state.client.get_sale_list()
                        st.session_state.metrics['sales'] = process_sales_metrics(all_sales, sales_counts)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Purchases
                if sections['purchases']:
                    with st.spinner("Loading purchase data..."):
                        purchase_counts = st.session_state.client.get_purchase_status_counts()
                        all_purchases = st.session_state.client.get_purchase_list()
                        st.session_state.metrics['purchases'] = process_purchase_metrics(all_purchases, purchase_counts)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Stock Adjustments
                if sections['stock_adjustments']:
                    with st.spinner("Loading stock adjustments..."):
                        adjustments = st.session_state.client.get_stock_adjustments()
                        # Fetch details for each adjustment (limit to recent ones)
                        adj_details = []
                        for adj in adjustments[:20]:  # Limit to prevent too many API calls
                            detail = st.session_state.client.get_stock_adjustment_detail(adj['TaskID'])
                            adj_details.append(detail)
                        st.session_state.metrics['stock_adjustments'] = process_stock_adjustments(adjustments, adj_details)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Stock Takes
                if sections['stock_takes']:
                    with st.spinner("Loading stock takes..."):
                        stocktakes = st.session_state.client.get_stock_takes()
                        st_details = []
                        for st_item in stocktakes[:20]:
                            detail = st.session_state.client.get_stock_take_detail(st_item['TaskID'])
                            st_details.append(detail)
                        st.session_state.metrics['stock_takes'] = process_stock_takes(stocktakes, st_details)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Transfers
                if sections['transfers']:
                    with st.spinner("Loading transfers..."):
                        all_transfers = st.session_state.client.get_stock_transfers()
                        st.session_state.metrics['transfers'] = process_transfers(all_transfers)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Assemblies
                if sections['assemblies']:
                    with st.spinner("Loading assemblies & production..."):
                        assemblies = st.session_state.client.get_finished_goods()
                        production = st.session_state.client.get_production_orders()
                        st.session_state.metrics['assemblies'] = process_assemblies(assemblies)
                        st.session_state.metrics['production'] = process_production_orders(production)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Stock per Location
                if sections['stock_per_location']:
                    with st.spinner("Loading stock availability..."):
                        locations = st.session_state.client.get_locations()
                        availability = st.session_state.client.get_product_availability()
                        location_names = [loc.get('Name') for loc in locations]

                        # Load products for cost data (if not already loaded)
                        if 'products' not in st.session_state:
                            st.session_state.products = st.session_state.client.get_products()

                        st.session_state.metrics['stock_availability'] = process_stock_availability(
                            availability, location_names, st.session_state.products
                        )
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Data Hygiene
                if sections['data_hygiene']:
                    with st.spinner("Loading master data for hygiene checks..."):
                        # Load products if not already loaded
                        if 'products' not in st.session_state:
                            st.session_state.products = st.session_state.client.get_products()

                        customers = st.session_state.client.get_customers()
                        suppliers = st.session_state.client.get_suppliers()
                        st.session_state.metrics['data_hygiene'] = process_data_hygiene(
                            st.session_state.products, customers, suppliers
                        )
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Credit Notes
                if sections['credit_notes']:
                    with st.spinner("Loading credit notes..."):
                        sale_cns = st.session_state.client.get_sale_credit_notes()
                        purchase_cns = st.session_state.client.get_purchase_credit_notes()
                        st.session_state.metrics['credit_notes'] = process_credit_notes(sale_cns, purchase_cns)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Process Sync Errors if uploaded
                if sync_file is not None:
                    with st.spinner("Processing sync errors..."):
                        # Read XLSX file, skip first 6 rows to get to the data
                        sync_df = pd.read_excel(sync_file, sheet_name=0, header=6)
                        st.session_state.metrics['sync_errors'] = process_sync_errors(sync_df)
                        st.success(f"✓ Processed {st.session_state.metrics['sync_errors']['total_errors']} sync errors")

                progress_bar.progress(1.0)
                st.session_state.data_loaded = True
                st.success("✓ All data loaded successfully!")

            except Cin7APIError as e:
                st.error(f"API Error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                logger.exception("Error loading data")


# =============================================================================
# MAIN CONTENT AREA
# =============================================================================

st.markdown('<p class="main-header">Cin7 Core Health Check Report</p>', unsafe_allow_html=True)

if not st.session_state.data_loaded:
    st.info("👈 Configure settings in the sidebar and click **Load Data from Cin7** to begin.")

    # Show quick overview
    st.markdown("### What is this?")
    st.write("""
    This app automatically generates health check reports for Cin7 Core clients by:

    1. **Connecting** to the Cin7 Core API with client credentials
    2. **Pulling** all relevant transaction data (sales, purchases, stock, etc.)
    3. **Analyzing** the data to identify issues and anomalies
    4. **Generating** a branded PDF report with actionable insights

    **No CSV uploads needed** – everything is pulled directly from the Cin7 API!
    """)

else:
    # Display metrics tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Summary", "📋 Detailed Metrics", "🔍 Anomalies", "📄 Generate PDF", "💾 Export Data"])

    # TAB 1: SUMMARY
    with tab1:
        st.markdown("### Health Check Summary")

        # Summary metrics cards
        col1, col2, col3, col4 = st.columns(4)

        # Sales summary
        if 'sales' in st.session_state.metrics:
            with col1:
                sales = st.session_state.metrics['sales']
                st.metric(
                    "Total Sales Orders",
                    sales['summary']['total_sales'],
                    delta="Anomalies" if sales['summary']['has_anomalies'] else "OK"
                )

        # Purchases summary
        if 'purchases' in st.session_state.metrics:
            with col2:
                purchases = st.session_state.metrics['purchases']
                st.metric(
                    "Total Purchase Orders",
                    purchases['summary']['total_purchases'],
                    delta="Anomalies" if purchases['summary']['has_anomalies'] else "OK"
                )

        # Stock availability
        if 'stock_availability' in st.session_state.metrics:
            with col3:
                stock = st.session_state.metrics['stock_availability']
                st.metric(
                    "Negative Stock Items",
                    stock['summary']['total_negative_items'],
                    delta="Critical!" if stock['summary']['has_negative_stock'] else "OK",
                    delta_color="inverse"
                )

        # Data hygiene
        if 'data_hygiene' in st.session_state.metrics:
            with col4:
                hygiene = st.session_state.metrics['data_hygiene']
                st.metric(
                    "Data Quality Issues",
                    hygiene['summary']['total_issues']
                )

        # Sync Errors (if uploaded)
        if 'sync_errors' in st.session_state.metrics:
            st.markdown("---")
            sync = st.session_state.metrics['sync_errors']

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Sync Errors (Failed)", sync['summary']['failed_count'], delta="Critical!" if sync['summary']['failed_count'] > 0 else "OK", delta_color="inverse")
            with col2:
                st.metric("Warnings", sync['summary']['warning_count'])
            with col3:
                st.metric("Skipped", sync['summary']['skipped_count'])
            with col4:
                st.metric("Pending", sync['summary']['pending_count'])

    # TAB 2: DETAILED METRICS
    with tab2:
        st.markdown("### Detailed Metrics by Section")

        # Sync Errors section (if uploaded)
        if 'sync_errors' in st.session_state.metrics:
            with st.expander("🔄 Xero/QBO Sync Errors", expanded=True):
                sync = st.session_state.metrics['sync_errors']

                st.markdown(f"**Total Errors:** {sync['total_errors']}")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**By Status:**")
                    if sync['by_status']:
                        st.json(sync['by_status'])

                with col2:
                    st.markdown("**By Type:**")
                    if sync['by_type']:
                        st.json(sync['by_type'])

                if sync['recent_errors']:
                    st.markdown("**Recent Errors (First 20):**")
                    st.dataframe(pd.DataFrame(sync['recent_errors']))

        # Sales section
        if 'sales' in st.session_state.metrics:
            with st.expander("📦 Sales Orders", expanded=True):
                sales = st.session_state.metrics['sales']

                st.markdown("**Status Counts:**")
                if sales['status_counts']:
                    st.json(sales['status_counts'])

                st.markdown("**Anomalies:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Fulfilled Not Invoiced",
                        sales['anomalies']['fulfilled_not_invoiced']['count']
                    )
                with col2:
                    st.metric(
                        "Invoiced Not Fulfilled",
                        sales['anomalies']['invoiced_not_fulfilled']['count']
                    )

        # Purchases section
        if 'purchases' in st.session_state.metrics:
            with st.expander("🛒 Purchase Orders", expanded=True):
                purchases = st.session_state.metrics['purchases']

                st.markdown("**Status Counts:**")
                if purchases['status_counts']:
                    st.json(purchases['status_counts'])

                st.markdown("**Anomalies:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Authorised Not Invoiced",
                        purchases['anomalies']['authorised_not_invoiced']['count']
                    )
                    st.metric(
                        "Invoiced Not Received",
                        purchases['anomalies']['invoiced_not_received']['count']
                    )
                with col2:
                    st.metric(
                        "Authorised Not Received",
                        purchases['anomalies']['authorised_not_received']['count']
                    )
                    st.metric(
                        "Received Not Invoiced",
                        purchases['anomalies']['received_not_invoiced']['count']
                    )

        # Stock Adjustments
        if 'stock_adjustments' in st.session_state.metrics:
            with st.expander("📊 Stock Adjustments"):
                adj = st.session_state.metrics['stock_adjustments']
                st.metric("Total Adjustments", adj['total_adjustments'])
                st.metric("Total Cost Impact", format_currency(adj['summary']['total_cost_impact']))

                if adj['by_location']:
                    st.markdown("**By Location:**")
                    st.json(adj['by_location'])

        # Stock Takes
        if 'stock_takes' in st.session_state.metrics:
            with st.expander("📋 Stock Takes"):
                st_data = st.session_state.metrics['stock_takes']
                st.metric("Total Stock Takes", st_data['total_stocktakes'])
                st.metric("Total Cost Impact", format_currency(st_data['summary']['total_cost_impact']))

        # Negative Stock
        if 'stock_availability' in st.session_state.metrics:
            stock = st.session_state.metrics['stock_availability']
            if stock['negative_stock']:
                with st.expander("⚠️ Negative Stock Items", expanded=True):
                    st.warning(f"Found {len(stock['negative_stock'])} items with negative stock!")
                    st.dataframe(stock['negative_stock'])

        # Data Hygiene
        if 'data_hygiene' in st.session_state.metrics:
            with st.expander("🧹 Data Quality / Hygiene Issues", expanded=True):
                hygiene = st.session_state.metrics['data_hygiene']

                st.markdown(f"**Total Issues Found:** {hygiene['summary']['total_issues']}")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Products:**")
                    st.metric("No Price Set", hygiene['summary']['products_no_price'])
                    st.metric("No Category", hygiene['summary']['products_no_category'])

                with col2:
                    st.markdown("**Customers:**")
                    st.metric("Missing Email", hygiene['summary']['customers_missing_email'])
                    st.metric("Missing Contact Person", len(hygiene['customers']['missing_contact']))

                st.markdown("**Suppliers:**")
                st.metric("Missing Email", hygiene['summary']['suppliers_missing_email'])

                # Show details if available
                if hygiene['products']['no_price']:
                    with st.expander(f"📦 Products with No Price ({len(hygiene['products']['no_price'])})"):
                        st.dataframe(pd.DataFrame(hygiene['products']['no_price']))

                if hygiene['products']['no_category']:
                    with st.expander(f"📁 Products with No Category ({len(hygiene['products']['no_category'])})"):
                        st.dataframe(pd.DataFrame(hygiene['products']['no_category']))

                if hygiene['customers']['missing_email']:
                    with st.expander(f"👥 Customers Missing Email ({len(hygiene['customers']['missing_email'])})"):
                        st.dataframe(pd.DataFrame(hygiene['customers']['missing_email']))

                if hygiene['customers']['missing_contact']:
                    with st.expander(f"👥 Customers Missing Contact Person ({len(hygiene['customers']['missing_contact'])})"):
                        st.dataframe(pd.DataFrame(hygiene['customers']['missing_contact']))

                if hygiene['suppliers']['missing_email']:
                    with st.expander(f"🏭 Suppliers Missing Email ({len(hygiene['suppliers']['missing_email'])})"):
                        st.dataframe(pd.DataFrame(hygiene['suppliers']['missing_email']))

    # TAB 3: ANOMALIES
    with tab3:
        st.markdown("### 🔍 Anomalies & Issues")

        anomaly_count = 0

        # Sales anomalies
        if 'sales' in st.session_state.metrics:
            sales = st.session_state.metrics['sales']
            if sales['anomalies']['fulfilled_not_invoiced']['count'] > 0:
                anomaly_count += sales['anomalies']['fulfilled_not_invoiced']['count']
                with st.expander(f"⚠️ Fulfilled Sales Not Invoiced ({sales['anomalies']['fulfilled_not_invoiced']['count']})", expanded=True):
                    st.dataframe(sales['anomalies']['fulfilled_not_invoiced']['records'])

            if sales['anomalies']['invoiced_not_fulfilled']['count'] > 0:
                anomaly_count += sales['anomalies']['invoiced_not_fulfilled']['count']
                with st.expander(f"⚠️ Invoiced Sales Not Fulfilled ({sales['anomalies']['invoiced_not_fulfilled']['count']})"):
                    st.dataframe(sales['anomalies']['invoiced_not_fulfilled']['records'])

        # Purchase anomalies
        if 'purchases' in st.session_state.metrics:
            purchases = st.session_state.metrics['purchases']
            for anomaly_type, anomaly_data in purchases['anomalies'].items():
                if anomaly_data['count'] > 0:
                    anomaly_count += anomaly_data['count']
                    title = anomaly_type.replace('_', ' ').title()
                    with st.expander(f"⚠️ {title} ({anomaly_data['count']})"):
                        st.dataframe(anomaly_data['records'])

        if anomaly_count == 0:
            st.success("✅ No anomalies detected!")

    # TAB 4: GENERATE PDF
    with tab4:
        st.markdown("### 📄 Generate PDF Report")

        st.write(f"**Client:** {st.session_state.client.client_name if st.session_state.client else 'N/A'}")
        st.write(f"**Period:** {report_period}")

        if st.button("🎨 Generate PDF", type="primary"):
            try:
                with st.spinner("Generating PDF report..."):
                    pdf_buffer = generate_health_check_pdf(
                        client_name=st.session_state.client.client_name,
                        report_period=report_period,
                        all_metrics=st.session_state.metrics,
                        sections_included=sections
                    )

                    filename = f"{st.session_state.client.client_name}_{report_period.replace(' ', '_')}_Health_Check.pdf"

                    st.success("✓ PDF generated successfully!")

                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        type="primary"
                    )

            except Exception as e:
                st.error(f"Error generating PDF: {e}")
                logger.exception("PDF generation failed")

    # TAB 5: EXPORT DATA
    with tab5:
        st.markdown("### 💾 Export Raw Data to CSV")
        st.write("Download the raw data tables for further analysis in Excel or other tools.")

        # Sync Errors (full width)
        if 'sync_errors' in st.session_state.metrics:
            sync = st.session_state.metrics['sync_errors']
            if sync['recent_errors']:
                st.markdown("#### Sync Errors")
                df = pd.DataFrame(sync['recent_errors'])
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download All Sync Errors",
                    csv,
                    f"sync_errors_{report_period.replace(' ', '_')}.csv",
                    "text/csv",
                    type="primary"
                )
                st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            # Sales exports
            if 'sales' in st.session_state.metrics:
                st.markdown("#### Sales Data")

                # All sales orders
                if st.button("📥 Download All Sales Orders"):
                    # We'd need to store the raw API data for this
                    # For now, we can export the anomalies
                    pass

                # Fulfilled not invoiced
                sales = st.session_state.metrics['sales']
                if sales['anomalies']['fulfilled_not_invoiced']['records']:
                    df = pd.DataFrame(sales['anomalies']['fulfilled_not_invoiced']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Fulfilled Not Invoiced",
                        csv,
                        f"fulfilled_not_invoiced_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Invoiced not fulfilled
                if sales['anomalies']['invoiced_not_fulfilled']['records']:
                    df = pd.DataFrame(sales['anomalies']['invoiced_not_fulfilled']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Invoiced Not Fulfilled",
                        csv,
                        f"invoiced_not_fulfilled_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

            # Purchase exports
            if 'purchases' in st.session_state.metrics:
                st.markdown("#### Purchase Data")

                purchases = st.session_state.metrics['purchases']

                # Authorised not invoiced
                if purchases['anomalies']['authorised_not_invoiced']['records']:
                    df = pd.DataFrame(purchases['anomalies']['authorised_not_invoiced']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Authorised Not Invoiced",
                        csv,
                        f"pos_authorised_not_invoiced_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Authorised not received
                if purchases['anomalies']['authorised_not_received']['records']:
                    df = pd.DataFrame(purchases['anomalies']['authorised_not_received']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Authorised Not Received",
                        csv,
                        f"pos_authorised_not_received_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

        with col2:
            # Stock adjustments
            if 'stock_adjustments' in st.session_state.metrics:
                st.markdown("#### Stock Adjustments")

                adj = st.session_state.metrics['stock_adjustments']

                # Top qty in
                if adj['top_qty_in']:
                    df = pd.DataFrame(adj['top_qty_in'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Top Qty Adjustments IN",
                        csv,
                        f"top_adjustments_in_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Top qty out
                if adj['top_qty_out']:
                    df = pd.DataFrame(adj['top_qty_out'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Top Qty Adjustments OUT",
                        csv,
                        f"top_adjustments_out_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

            # Stock takes
            if 'stock_takes' in st.session_state.metrics:
                st.markdown("#### Stock Takes")

                st_data = st.session_state.metrics['stock_takes']

                # Top discrepancies
                if st_data['top_discrepancies']:
                    df = pd.DataFrame(st_data['top_discrepancies'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Top Stock Take Discrepancies",
                        csv,
                        f"stocktake_discrepancies_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

            # Negative stock
            if 'stock_availability' in st.session_state.metrics:
                stock = st.session_state.metrics['stock_availability']
                if stock['negative_stock']:
                    st.markdown("#### Negative Stock")
                    df = pd.DataFrame(stock['negative_stock'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Negative Stock Items",
                        csv,
                        f"negative_stock_{report_period.replace(' ', '_')}.csv",
                        "text/csv",
                        type="primary"
                    )

            # Data Hygiene
            if 'data_hygiene' in st.session_state.metrics:
                st.markdown("#### Data Quality Issues")

                hygiene = st.session_state.metrics['data_hygiene']

                # Products with no price
                if hygiene['products']['no_price']:
                    df = pd.DataFrame(hygiene['products']['no_price'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Products with No Price",
                        csv,
                        f"products_no_price_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Products with no category
                if hygiene['products']['no_category']:
                    df = pd.DataFrame(hygiene['products']['no_category'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Products with No Category",
                        csv,
                        f"products_no_category_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Customers missing email
                if hygiene['customers']['missing_email']:
                    df = pd.DataFrame(hygiene['customers']['missing_email'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Customers Missing Email",
                        csv,
                        f"customers_missing_email_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Customers missing contact
                if hygiene['customers']['missing_contact']:
                    df = pd.DataFrame(hygiene['customers']['missing_contact'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Customers Missing Contact Person",
                        csv,
                        f"customers_missing_contact_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                # Suppliers missing email
                if hygiene['suppliers']['missing_email']:
                    df = pd.DataFrame(hygiene['suppliers']['missing_email'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Suppliers Missing Email",
                        csv,
                        f"suppliers_missing_email_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

        st.markdown("---")
        st.info("💡 **Tip:** These CSV files contain the detailed data behind each metric. Open them in Excel for further analysis, filtering, or reporting.")


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>Cin7 Core Health Check Automation | Built with Streamlit | © Finovate</small>
</div>
""", unsafe_allow_html=True)
