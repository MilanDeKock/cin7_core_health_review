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

                # Determine period bounds for date filtering
                from datetime import date as _date
                period_start = _date(report_year, report_month, 1).isoformat()
                if report_month == 12:
                    period_end = _date(report_year + 1, 1, 1).isoformat()
                else:
                    period_end = _date(report_year, report_month + 1, 1).isoformat()

                # Sales — single bulk pull, all counts derived client-side
                if sections['sales']:
                    with st.spinner("Loading sales data..."):
                        all_sales = st.session_state.client.get_sale_list()
                        st.session_state.metrics['sales'] = process_sales_metrics(
                            all_sales, None, report_year, report_month
                        )
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Purchases — single bulk pull, all counts derived client-side
                if sections['purchases']:
                    with st.spinner("Loading purchase data..."):
                        all_purchases = st.session_state.client.get_purchase_list()
                        st.session_state.metrics['purchases'] = process_purchase_metrics(
                            all_purchases, None, report_year, report_month
                        )
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Stock Adjustments
                if sections['stock_adjustments']:
                    with st.spinner("Loading stock adjustments..."):
                        adjustments = st.session_state.client.get_stock_adjustments()
                        # Filter to only adjustments within the reporting period by EffectiveDate
                        period_adjs = [
                            a for a in adjustments
                            if period_start <= (a.get('EffectiveDate') or a.get('Date') or '')[:10] < period_end
                        ]
                        adj_details = []
                        for adj in period_adjs:
                            detail = st.session_state.client.get_stock_adjustment_detail(adj['TaskID'])
                            adj_details.append(detail)
                        st.session_state.metrics['stock_adjustments'] = process_stock_adjustments(period_adjs, adj_details)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Stock Takes
                if sections['stock_takes']:
                    with st.spinner("Loading stock takes..."):
                        stocktakes = st.session_state.client.get_stock_takes()
                        # Filter to only stocktakes within the reporting period by EffectiveDate
                        period_takes = [
                            s for s in stocktakes
                            if period_start <= (s.get('EffectiveDate') or s.get('Date') or '')[:10] < period_end
                        ]
                        st_details = []
                        for st_item in period_takes:
                            detail = st.session_state.client.get_stock_take_detail(st_item['TaskID'])
                            st_details.append(detail)
                        st.session_state.metrics['stock_takes'] = process_stock_takes(
                            period_takes, st_details, st.session_state.get('products')
                        )
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Transfers — only DRAFT and IN TRANSIT (active, not completed)
                if sections['transfers']:
                    with st.spinner("Loading transfers..."):
                        transfers_draft = st.session_state.client.get_stock_transfers(status='DRAFT')
                        transfers_transit = st.session_state.client.get_stock_transfers(status='IN TRANSIT')
                        all_transfers = transfers_draft + transfers_transit
                        st.session_state.metrics['transfers'] = process_transfers(all_transfers)
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Assemblies — 3 separate status calls; Production — 4 status calls, Type='O' only
                if sections['assemblies']:
                    with st.spinner("Loading assemblies & production..."):
                        assemblies = (
                            st.session_state.client.get_finished_goods(status='DRAFT') +
                            st.session_state.client.get_finished_goods(status='AUTHORISED') +
                            st.session_state.client.get_finished_goods(status='IN PROGRESS')
                        )
                        production = (
                            st.session_state.client.get_production_orders(status='Draft') +
                            st.session_state.client.get_production_orders(status='Planned') +
                            st.session_state.client.get_production_orders(status='Released') +
                            st.session_state.client.get_production_orders(status='InProgress')
                        )
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

                        # Load products for cost data (exclude deprecated)
                        if 'products' not in st.session_state:
                            st.session_state.products = st.session_state.client.get_products(include_deprecated=False)

                        st.session_state.metrics['stock_availability'] = process_stock_availability(
                            availability, location_names, st.session_state.products
                        )
                    current += 1
                    progress_bar.progress(current / total_sections)

                # Data Hygiene
                if sections['data_hygiene']:
                    with st.spinner("Loading master data for hygiene checks..."):
                        # Load active products (exclude deprecated)
                        if 'products' not in st.session_state:
                            st.session_state.products = st.session_state.client.get_products(include_deprecated=False)

                        # Exclude deprecated customers and suppliers
                        customers = st.session_state.client.get_customers(include_deprecated=False)
                        suppliers = st.session_state.client.get_suppliers(include_deprecated=False)
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
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Prior Period Not Fulfilled",
                        sales['anomalies']['authorised_prior_not_fulfilled']['count']
                    )
                with col2:
                    st.metric(
                        "Fulfilled Not Invoiced",
                        sales['anomalies']['fulfilled_not_invoiced']['count']
                    )
                with col3:
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

                st.markdown("**Prior Period Anomalies:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Prior Period Not Invoiced",
                        purchases['anomalies']['prior_not_invoiced']['count']
                    )
                with col2:
                    st.metric(
                        "Prior Period Not Received",
                        purchases['anomalies']['prior_not_received']['count']
                    )

                st.markdown("**Current Period:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Current Period Not Invoiced",
                        purchases['anomalies']['current_not_invoiced']['count']
                    )
                with col2:
                    st.metric(
                        "Current Period Not Received",
                        purchases['anomalies']['current_not_received']['count']
                    )

                st.markdown("**Cross Anomalies:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Invoiced Not Received",
                        purchases['anomalies']['fully_invoiced_not_received']['count']
                    )
                with col2:
                    st.metric(
                        "Received Not Invoiced",
                        purchases['anomalies']['fully_received_not_invoiced']['count']
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

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Products (Sellable):**")
                    st.metric("No Retail Price", hygiene['summary']['products_no_price'])
                    st.metric("No Barcode", hygiene['summary']['products_no_barcode'])

                with col2:
                    st.markdown("**Customers:**")
                    st.metric("Missing Email", hygiene['summary']['customers_missing_email'])
                    st.metric("Missing Phone", hygiene['summary']['customers_missing_phone'])
                    st.metric("No Payment Term", hygiene['summary']['customers_missing_payment_terms'])
                    st.metric("On Credit Hold", hygiene['summary']['customers_on_credit_hold'])

                with col3:
                    st.markdown("**Suppliers:**")
                    st.metric("Missing Email", hygiene['summary']['suppliers_missing_email'])
                    st.metric("Missing Phone", hygiene['summary']['suppliers_missing_phone'])
                    st.metric("No Payment Term", hygiene['summary']['suppliers_missing_payment_terms'])

                # Show details
                if hygiene['products']['no_price']:
                    with st.expander(f"💰 Sellable Products with No Retail Price ({len(hygiene['products']['no_price'])})"):
                        st.dataframe(pd.DataFrame(hygiene['products']['no_price']))

                if hygiene['products']['no_barcode']:
                    with st.expander(f"📦 Sellable Products with No Barcode ({len(hygiene['products']['no_barcode'])})"):
                        st.dataframe(pd.DataFrame(hygiene['products']['no_barcode']))

                if hygiene['customers']['missing_email']:
                    with st.expander(f"👥 Customers Missing Email ({len(hygiene['customers']['missing_email'])})"):
                        st.dataframe(pd.DataFrame(hygiene['customers']['missing_email']))

                if hygiene['customers']['missing_phone']:
                    with st.expander(f"📞 Customers Missing Phone ({len(hygiene['customers']['missing_phone'])})"):
                        st.dataframe(pd.DataFrame(hygiene['customers']['missing_phone']))

                if hygiene['customers']['missing_payment_terms']:
                    with st.expander(f"💳 Customers with No Payment Term ({len(hygiene['customers']['missing_payment_terms'])})"):
                        st.dataframe(pd.DataFrame(hygiene['customers']['missing_payment_terms']))

                if hygiene['customers']['on_credit_hold']:
                    with st.expander(f"🚫 Customers on Credit Hold ({len(hygiene['customers']['on_credit_hold'])})"):
                        st.dataframe(pd.DataFrame(hygiene['customers']['on_credit_hold']))

                if hygiene['suppliers']['missing_email']:
                    with st.expander(f"🏭 Suppliers Missing Email ({len(hygiene['suppliers']['missing_email'])})"):
                        st.dataframe(pd.DataFrame(hygiene['suppliers']['missing_email']))

                if hygiene['suppliers']['missing_phone']:
                    with st.expander(f"📞 Suppliers Missing Phone ({len(hygiene['suppliers']['missing_phone'])})"):
                        st.dataframe(pd.DataFrame(hygiene['suppliers']['missing_phone']))

                if hygiene['suppliers']['missing_payment_terms']:
                    with st.expander(f"💳 Suppliers with No Payment Term ({len(hygiene['suppliers']['missing_payment_terms'])})"):
                        st.dataframe(pd.DataFrame(hygiene['suppliers']['missing_payment_terms']))

    # TAB 3: ANOMALIES
    with tab3:
        st.markdown("### 🔍 Anomalies & Issues")

        anomaly_count = 0

        # Sales anomalies
        if 'sales' in st.session_state.metrics:
            sales = st.session_state.metrics['sales']
            if sales['anomalies']['authorised_prior_not_fulfilled']['count'] > 0:
                anomaly_count += sales['anomalies']['authorised_prior_not_fulfilled']['count']
                with st.expander(f"⚠️ Auth SOs from Prior Periods Not Fulfilled ({sales['anomalies']['authorised_prior_not_fulfilled']['count']})", expanded=True):
                    st.dataframe(sales['anomalies']['authorised_prior_not_fulfilled']['records'])

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

                sales = st.session_state.metrics['sales']

                if sales['anomalies']['authorised_prior_not_fulfilled']['records']:
                    df = pd.DataFrame(sales['anomalies']['authorised_prior_not_fulfilled']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Prior Period Not Fulfilled",
                        csv,
                        f"sales_prior_not_fulfilled_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                if sales['anomalies']['fulfilled_not_invoiced']['records']:
                    df = pd.DataFrame(sales['anomalies']['fulfilled_not_invoiced']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Fulfilled Not Invoiced",
                        csv,
                        f"sales_fulfilled_not_invoiced_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

                if sales['anomalies']['invoiced_not_fulfilled']['records']:
                    df = pd.DataFrame(sales['anomalies']['invoiced_not_fulfilled']['records'])
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Invoiced Not Fulfilled",
                        csv,
                        f"sales_invoiced_not_fulfilled_{report_period.replace(' ', '_')}.csv",
                        "text/csv"
                    )

            # Purchase exports
            if 'purchases' in st.session_state.metrics:
                st.markdown("#### Purchase Data")

                purchases = st.session_state.metrics['purchases']

                for key, label, filename in [
                    ('prior_not_invoiced', '📥 Prior Period Not Invoiced', 'pos_prior_not_invoiced'),
                    ('prior_not_received', '📥 Prior Period Not Received', 'pos_prior_not_received'),
                    ('current_not_invoiced', '📥 Current Period Not Invoiced', 'pos_current_not_invoiced'),
                    ('current_not_received', '📥 Current Period Not Received', 'pos_current_not_received'),
                    ('fully_invoiced_not_received', '📥 Invoiced Not Received', 'pos_invoiced_not_received'),
                    ('fully_received_not_invoiced', '📥 Received Not Invoiced', 'pos_received_not_invoiced'),
                ]:
                    if purchases['anomalies'][key]['records']:
                        df = pd.DataFrame(purchases['anomalies'][key]['records'])
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label,
                            csv,
                            f"{filename}_{report_period.replace(' ', '_')}.csv",
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

                hygiene_exports = [
                    (hygiene['products']['no_price'], "📥 Sellable Products with No Retail Price", "products_no_price"),
                    (hygiene['products']['no_barcode'], "📥 Sellable Products with No Barcode", "products_no_barcode"),
                    (hygiene['customers']['missing_email'], "📥 Customers Missing Email", "customers_missing_email"),
                    (hygiene['customers']['missing_phone'], "📥 Customers Missing Phone", "customers_missing_phone"),
                    (hygiene['customers']['missing_payment_terms'], "📥 Customers with No Payment Term", "customers_missing_payment_terms"),
                    (hygiene['customers']['on_credit_hold'], "📥 Customers on Credit Hold", "customers_on_credit_hold"),
                    (hygiene['suppliers']['missing_email'], "📥 Suppliers Missing Email", "suppliers_missing_email"),
                    (hygiene['suppliers']['missing_phone'], "📥 Suppliers Missing Phone", "suppliers_missing_phone"),
                    (hygiene['suppliers']['missing_payment_terms'], "📥 Suppliers with No Payment Term", "suppliers_missing_payment_terms"),
                ]

                for data, label, filename in hygiene_exports:
                    if data:
                        df = pd.DataFrame(data)
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label,
                            csv,
                            f"{filename}_{report_period.replace(' ', '_')}.csv",
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
