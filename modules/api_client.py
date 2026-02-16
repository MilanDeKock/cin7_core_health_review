"""
Cin7 Core API Client Module

Handles authentication, rate limiting, pagination, and error handling
for the Cin7 Core (formerly DEAR Inventory) API.

API Documentation: https://dearinventory.docs.apiary.io/
Rate Limit: 60 calls per minute
"""

import os
import time
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Cin7APIError(Exception):
    """Custom exception for Cin7 API errors"""
    pass


class Cin7APIClient:
    """
    Cin7 Core API client with automatic pagination, rate limiting, and error handling.

    Authentication uses Account ID and API Key from environment variables.
    Supports multiple clients using naming convention: CLIENT_1_NAME, CLIENT_1_ACCOUNT_ID, etc.
    """

    BASE_URL = "https://inventory.dearsystems.com/ExternalApi/v2"
    RATE_LIMIT_DELAY = 1.0  # seconds between API calls (60 calls/min = 1 call/sec)
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds to wait before retrying

    def __init__(self, client_number: int = 1):
        """
        Initialize the API client for a specific client.

        Args:
            client_number: The client number (1, 2, 3, etc.) for multi-client support
        """
        load_dotenv()

        # Load client credentials from environment
        prefix = f"CLIENT_{client_number}_"
        self.client_name = os.getenv(f"{prefix}NAME")
        self.account_id = os.getenv(f"{prefix}ACCOUNT_ID")
        self.api_key = os.getenv(f"{prefix}API_KEY")

        if not self.account_id or not self.api_key:
            raise ValueError(
                f"Missing credentials for client {client_number}. "
                f"Please set {prefix}ACCOUNT_ID and {prefix}API_KEY in .env file"
            )

        self.session = requests.Session()
        self.session.headers.update({
            "api-auth-accountid": self.account_id,
            "api-auth-applicationkey": self.api_key,
            "Content-Type": "application/json"
        })

        self.last_request_time = 0
        logger.info(f"Initialized API client for: {self.client_name or f'Client {client_number}'}")

    def _enforce_rate_limit(self):
        """Enforce rate limiting of 60 calls per minute (1 call per second)"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make an API request with error handling and retries.

        Args:
            endpoint: API endpoint path (e.g., '/saleList')
            params: Query parameters
            method: HTTP method (GET, POST, etc.)
            retry_count: Current retry attempt number

        Returns:
            JSON response as dictionary

        Raises:
            Cin7APIError: For non-recoverable API errors
        """
        self._enforce_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.debug(f"Making {method} request to {endpoint} with params: {params}")
            response = self.session.request(method, url, params=params)

            # Handle different HTTP status codes
            if response.status_code == 200:
                return response.json()

            elif response.status_code == 400:
                raise Cin7APIError(f"Bad Request (400): {response.text}")

            elif response.status_code == 403:
                raise Cin7APIError(
                    f"Authentication Failed (403): Check Account ID and API Key. {response.text}"
                )

            elif response.status_code == 404:
                raise Cin7APIError(f"Resource Not Found (404): {endpoint}")

            elif response.status_code == 429:
                # Rate limit exceeded - wait and retry
                if retry_count < self.MAX_RETRIES:
                    logger.warning(f"Rate limit exceeded (429). Retrying in {self.RETRY_DELAY * 2} seconds...")
                    time.sleep(self.RETRY_DELAY * 2)
                    return self._make_request(endpoint, params, method, retry_count + 1)
                else:
                    raise Cin7APIError("Rate limit exceeded (429) - max retries reached")

            elif response.status_code in [500, 503]:
                # Server error - retry for transient issues
                if retry_count < self.MAX_RETRIES:
                    logger.warning(
                        f"Server error ({response.status_code}). "
                        f"Retry {retry_count + 1}/{self.MAX_RETRIES} in {self.RETRY_DELAY} seconds..."
                    )
                    time.sleep(self.RETRY_DELAY)
                    return self._make_request(endpoint, params, method, retry_count + 1)
                else:
                    raise Cin7APIError(
                        f"Server error ({response.status_code}) - max retries reached: {response.text}"
                    )

            else:
                raise Cin7APIError(
                    f"Unexpected status code {response.status_code}: {response.text}"
                )

        except requests.exceptions.RequestException as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(f"Request failed: {e}. Retrying...")
                time.sleep(self.RETRY_DELAY)
                return self._make_request(endpoint, params, method, retry_count + 1)
            else:
                raise Cin7APIError(f"Request failed after {self.MAX_RETRIES} retries: {e}")

    def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Automatically paginate through all results for an endpoint.

        Args:
            endpoint: API endpoint path
            params: Query parameters (excluding Page and Limit)
            limit: Number of records per page (max 250 for most endpoints)

        Returns:
            List of all records across all pages
        """
        if params is None:
            params = {}

        all_records = []
        page = 1
        params["Limit"] = limit

        while True:
            params["Page"] = page
            logger.info(f"Fetching page {page} from {endpoint}...")

            response = self._make_request(endpoint, params)

            # Handle different response structures
            # Most list endpoints return a list directly
            # Some return {"Total": N, "<ResourceName>": [...]}
            if isinstance(response, list):
                records = response
                total = len(records)
            elif isinstance(response, dict):
                # Find the data key (it varies by endpoint)
                # Common patterns: "Products", "Sales", "Purchases", etc.
                total = response.get("Total", 0)

                # Extract the actual data array
                data_keys = [k for k in response.keys() if k != "Total" and isinstance(response[k], list)]
                if data_keys:
                    records = response[data_keys[0]]
                else:
                    # Fallback: return the whole dict if structure is unexpected
                    logger.warning(f"Unexpected response structure: {response.keys()}")
                    return [response]
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                break

            if not records:
                break

            all_records.extend(records)

            # Check if we've retrieved all records
            if len(records) < limit:
                # Last page
                break

            # For endpoints that return Total, we can check if we're done
            if total > 0 and len(all_records) >= total:
                break

            page += 1

        logger.info(f"Retrieved {len(all_records)} total records from {endpoint}")
        return all_records

    def get_status_count(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Get count of records matching filters without fetching all data.
        Uses Limit=1 and reads the Total field from response.

        Args:
            endpoint: API endpoint path
            params: Query parameters (filters)

        Returns:
            Total count of matching records
        """
        if params is None:
            params = {}

        params["Limit"] = 1
        params["Page"] = 1

        response = self._make_request(endpoint, params)

        # Extract total from response
        if isinstance(response, dict) and "Total" in response:
            return response["Total"]
        elif isinstance(response, list):
            # If response is just a list, we can't get total without fetching all
            logger.warning(f"Endpoint {endpoint} doesn't return Total field. Fetching all records to count.")
            return len(self._paginate(endpoint, params))
        else:
            return 0

    # =========================================================================
    # SALES ENDPOINTS
    # =========================================================================

    def get_sale_list(
        self,
        status: Optional[str] = None,
        quote_status: Optional[str] = None,
        order_status: Optional[str] = None,
        combined_invoice_status: Optional[str] = None,
        fulfilment_status: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sale orders with optional filters.

        Possible values (from feasibility doc):
        - status: DRAFT, ESTIMATING, ESTIMATED, ORDERING, ORDERED, BACKORDERED, etc.
        - quote_status: DRAFT, AUTHORISED, NOT AVAILABLE
        - order_status: DRAFT, AUTHORISED, NOT AVAILABLE
        - combined_invoice_status: NOT AVAILABLE, NOT INVOICED, INVOICED, AUTHORISED
        - fulfilment_status: NOT FULFILLED, FULFILLED, PARTIAL
        - modified_since: ISO date string (YYYY-MM-DD)

        Returns:
            List of sale order dictionaries
        """
        params = {}
        if status:
            params["Status"] = status
        if quote_status:
            params["QuoteStatus"] = quote_status
        if order_status:
            params["OrderStatus"] = order_status
        if combined_invoice_status:
            params["CombinedInvoiceStatus"] = combined_invoice_status
        if fulfilment_status:
            params["FulFilmentStatus"] = fulfilment_status
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/saleList", params)

    def get_sale_detail(self, sale_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific sale.

        Args:
            sale_id: The sale ID (GUID)

        Returns:
            Detailed sale information
        """
        return self._make_request("/sale", {"ID": sale_id})

    def get_sale_credit_notes(
        self,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of sale credit notes.

        Args:
            modified_since: ISO date string (YYYY-MM-DD)

        Returns:
            List of credit note dictionaries
        """
        params = {}
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/saleCreditNoteList", params)

    def get_sale_credit_note_detail(self, sale_id: str) -> Dict[str, Any]:
        """
        Get detailed credit note information for a sale.

        Args:
            sale_id: The sale ID (GUID)

        Returns:
            Credit note details
        """
        return self._make_request("/sale/creditnote", {"SaleID": sale_id})

    # =========================================================================
    # PURCHASE ENDPOINTS
    # =========================================================================

    def get_purchase_list(
        self,
        order_status: Optional[str] = None,
        combined_invoice_status: Optional[str] = None,
        combined_receiving_status: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get purchase orders with optional filters.

        Possible values:
        - order_status: DRAFT, AUTHORISED
        - combined_invoice_status: NOT INVOICED, INVOICED, AUTHORISED
        - combined_receiving_status: NOT RECEIVED, RECEIVED, PARTIAL
        - modified_since: ISO date string

        Returns:
            List of purchase order dictionaries
        """
        params = {}
        if order_status:
            params["OrderStatus"] = order_status
        if combined_invoice_status:
            params["CombinedInvoiceStatus"] = combined_invoice_status
        if combined_receiving_status:
            params["CombinedReceivingStatus"] = combined_receiving_status
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/purchaseList", params)

    def get_purchase_detail(self, purchase_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific purchase.

        Args:
            purchase_id: The purchase ID (GUID)

        Returns:
            Detailed purchase information
        """
        return self._make_request("/purchase", {"ID": purchase_id})

    def get_purchase_credit_notes(
        self,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of purchase credit notes.

        Args:
            modified_since: ISO date string

        Returns:
            List of credit note dictionaries
        """
        params = {}
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/purchaseCreditNoteList", params)

    # =========================================================================
    # STOCK ADJUSTMENT & STOCKTAKE ENDPOINTS
    # =========================================================================

    def get_stock_adjustments(
        self,
        status: str = "COMPLETED",
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stock adjustment list.

        Args:
            status: DRAFT, COMPLETED (default: COMPLETED)
            modified_since: ISO date string

        Returns:
            List of stock adjustment summaries
        """
        params = {"Status": status}
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/stockadjustmentList", params)

    def get_stock_adjustment_detail(self, task_id: str) -> Dict[str, Any]:
        """
        Get detailed lines for a specific stock adjustment.

        Args:
            task_id: The TaskID from stock adjustment list

        Returns:
            Detailed adjustment with product lines, quantities, costs
        """
        return self._make_request("/stockadjustment", {"TaskID": task_id})

    def get_stock_takes(
        self,
        status: str = "COMPLETED",
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stock take list.

        Args:
            status: DRAFT, COMPLETED (default: COMPLETED)
            modified_since: ISO date string

        Returns:
            List of stock take summaries
        """
        params = {"Status": status}
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/stockTakeList", params)

    def get_stock_take_detail(self, task_id: str) -> Dict[str, Any]:
        """
        Get detailed lines for a specific stock take.

        The response includes NonZeroStockOnHandProducts with:
        - QuantityOnHand: actual counted quantity
        - Adjustment: discrepancy amount

        Args:
            task_id: The TaskID from stock take list

        Returns:
            Detailed stock take with discrepancies
        """
        return self._make_request("/stocktake", {"TaskID": task_id})

    # =========================================================================
    # STOCK TRANSFER ENDPOINTS
    # =========================================================================

    def get_stock_transfers(
        self,
        status: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stock transfer list.

        Possible status values: DRAFT, IN TRANSIT, ORDERED, PICKING

        Args:
            status: Transfer status filter
            modified_since: ISO date string

        Returns:
            List of stock transfers
        """
        params = {}
        if status:
            params["Status"] = status
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/stockTransferList", params)

    def get_stock_transfer_detail(self, task_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a stock transfer.

        Includes DepartureDate, CompletionDate, From/To locations.

        Args:
            task_id: The TaskID from transfer list

        Returns:
            Detailed transfer information
        """
        return self._make_request("/stockTransfer", {"TaskID": task_id})

    # =========================================================================
    # ASSEMBLY & PRODUCTION ENDPOINTS
    # =========================================================================

    def get_finished_goods(
        self,
        status: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get assembly/finished goods list.

        Possible status values: DRAFT, AUTHORISED, IN PROGRESS

        Args:
            status: Assembly status filter
            modified_since: ISO date string

        Returns:
            List of assemblies
        """
        params = {}
        if status:
            params["Status"] = status
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/finishedGoodsList", params)

    def get_finished_goods_detail(self, task_id: str) -> Dict[str, Any]:
        """
        Get detailed information for an assembly.

        Args:
            task_id: The TaskID from finished goods list

        Returns:
            Detailed assembly information
        """
        return self._make_request("/finishedGoods", {"TaskID": task_id})

    def get_production_orders(
        self,
        status: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get production order list.

        Possible status values: Draft, Planned, Released, InProgress

        Args:
            status: Production order status
            modified_since: ISO date string

        Returns:
            List of production orders
        """
        params = {}
        if status:
            params["Status"] = status
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/production/orderList", params)

    def get_production_order_detail(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a production order.

        Args:
            order_id: The production order ID

        Returns:
            Detailed production order with dates, BOM, runs
        """
        return self._make_request("/production/order", {"ID": order_id})

    # =========================================================================
    # PRODUCT & INVENTORY ENDPOINTS
    # =========================================================================

    def get_products(
        self,
        sku: Optional[str] = None,
        name: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get product master data list.

        Used for data hygiene checks (no price, no category, no supplier).
        Contains: SKU, Name, Category, PriceTier1-10, Status, AverageCost, etc.

        Args:
            sku: Filter by SKU
            name: Filter by product name
            modified_since: ISO date string

        Returns:
            List of products with master data
        """
        params = {}
        if sku:
            params["SKU"] = sku
        if name:
            params["Name"] = name
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/product", params, limit=100)  # Product endpoint may have lower page limit

    def get_product_availability(
        self,
        sku: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stock on hand, allocated, available per product per location.

        Returns: OnHand, Allocated, Available, OnOrder, InTransit for each product/location.
        Critical for negative stock detection and stock valuation.

        Args:
            sku: Filter by SKU
            location: Filter by location name

        Returns:
            List of product availability records
        """
        params = {}
        if sku:
            params["SKU"] = sku
        if location:
            params["Location"] = location

        return self._paginate("/ref/productavailability", params)

    def get_product_suppliers(self) -> List[Dict[str, Any]]:
        """
        Get product-supplier relationships.

        Used to identify products with no supplier linked.

        Returns:
            List of product-supplier links
        """
        # NOTE: This endpoint may not exist in standard Cin7 API
        # If it doesn't, we'll need to extract supplier info from the product endpoint
        # Flagging for verification
        logger.warning(
            "get_product_suppliers: Verify if /product-suppliers endpoint exists. "
            "May need to extract from /product endpoint instead."
        )
        return self._paginate("/product-suppliers", {})

    # =========================================================================
    # CUSTOMER & SUPPLIER ENDPOINTS
    # =========================================================================

    def get_customers(
        self,
        name: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get customer list.

        Used for data hygiene checks (missing contacts, emails, payment terms).

        Args:
            name: Filter by customer name
            modified_since: ISO date string

        Returns:
            List of customers
        """
        params = {}
        if name:
            params["Name"] = name
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/customer", params)

    def get_suppliers(
        self,
        name: Optional[str] = None,
        modified_since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get supplier list.

        Used for data hygiene checks.

        Args:
            name: Filter by supplier name
            modified_since: ISO date string

        Returns:
            List of suppliers
        """
        params = {}
        if name:
            params["Name"] = name
        if modified_since:
            params["ModifiedSince"] = modified_since

        return self._paginate("/supplier", params)

    # =========================================================================
    # REFERENCE DATA ENDPOINTS
    # =========================================================================

    def get_locations(self) -> List[Dict[str, Any]]:
        """
        Get list of stock locations.

        Returns location names for stock reporting.

        Returns:
            List of location dictionaries
        """
        return self._paginate("/ref/location", {})

    def get_payment_terms(self) -> List[Dict[str, Any]]:
        """
        Get payment terms reference data.

        Returns:
            List of payment terms
        """
        return self._paginate("/ref/paymentterm", {})

    def get_tax_rules(self) -> List[Dict[str, Any]]:
        """
        Get tax rules reference data.

        Returns:
            List of tax rules
        """
        return self._paginate("/ref/taxrule", {})

    # =========================================================================
    # HELPER METHODS FOR COMMON HEALTH CHECK QUERIES
    # =========================================================================

    def get_sale_status_counts(self) -> Dict[str, int]:
        """
        Get counts for all sale statuses in one batch.

        Returns:
            Dictionary with status names as keys and counts as values
        """
        logger.info("Fetching sale status counts...")

        counts = {
            "draft_quotes": self.get_status_count("/saleList", {"QuoteStatus": "DRAFT"}),
            "authorised_quotes_no_so": self.get_status_count(
                "/saleList",
                {"QuoteStatus": "AUTHORISED", "OrderStatus": "NOT AVAILABLE"}
            ),
            "backordered": self.get_status_count("/saleList", {"Status": "BACKORDERED"}),
            "awaiting_fulfilment": self.get_status_count(
                "/saleList",
                {"OrderStatus": "AUTHORISED", "FulFilmentStatus": "NOT FULFILLED"}
            ),
            "orders_to_bill": self.get_status_count(
                "/saleList",
                {"OrderStatus": "AUTHORISED", "CombinedInvoiceStatus": "NOT AVAILABLE"}
            ),
            "fulfilled_not_invoiced": self.get_status_count(
                "/saleList",
                {"FulFilmentStatus": "FULFILLED", "CombinedInvoiceStatus": "NOT INVOICED"}
            ),
            "invoiced_not_fulfilled": self.get_status_count(
                "/saleList",
                {"CombinedInvoiceStatus": "AUTHORISED", "FulFilmentStatus": "NOT FULFILLED"}
            ),
        }

        return counts

    def get_purchase_status_counts(self) -> Dict[str, int]:
        """
        Get counts for all purchase statuses in one batch.

        Returns:
            Dictionary with status names as keys and counts as values
        """
        logger.info("Fetching purchase status counts...")

        counts = {
            "draft": self.get_status_count("/purchaseList", {"OrderStatus": "DRAFT"}),
            "authorised": self.get_status_count("/purchaseList", {"OrderStatus": "AUTHORISED"}),
            "authorised_not_invoiced": self.get_status_count(
                "/purchaseList",
                {"OrderStatus": "AUTHORISED", "CombinedInvoiceStatus": "NOT INVOICED"}
            ),
            "authorised_not_received": self.get_status_count(
                "/purchaseList",
                {"OrderStatus": "AUTHORISED", "CombinedReceivingStatus": "NOT RECEIVED"}
            ),
            "fully_invoiced_not_received": self.get_status_count(
                "/purchaseList",
                {"CombinedInvoiceStatus": "AUTHORISED", "CombinedReceivingStatus": "NOT RECEIVED"}
            ),
            "fully_received_not_invoiced": self.get_status_count(
                "/purchaseList",
                {"CombinedReceivingStatus": "RECEIVED", "CombinedInvoiceStatus": "NOT INVOICED"}
            ),
        }

        return counts

    def get_assembly_status_counts(self) -> Dict[str, int]:
        """
        Get counts for assembly statuses.

        Returns:
            Dictionary with status counts
        """
        logger.info("Fetching assembly status counts...")

        counts = {
            "draft": self.get_status_count("/finishedGoodsList", {"Status": "DRAFT"}),
            "authorised": self.get_status_count("/finishedGoodsList", {"Status": "AUTHORISED"}),
            "in_progress": self.get_status_count("/finishedGoodsList", {"Status": "IN PROGRESS"}),
        }

        return counts

    def get_production_status_counts(self) -> Dict[str, int]:
        """
        Get counts for production order statuses.

        Returns:
            Dictionary with status counts
        """
        logger.info("Fetching production order status counts...")

        counts = {
            "draft": self.get_status_count("/production/orderList", {"Status": "Draft"}),
            "planned": self.get_status_count("/production/orderList", {"Status": "Planned"}),
            "released": self.get_status_count("/production/orderList", {"Status": "Released"}),
            "in_progress": self.get_status_count("/production/orderList", {"Status": "InProgress"}),
        }

        return counts

    def get_transfer_status_counts(self) -> Dict[str, int]:
        """
        Get counts for stock transfer statuses.

        Returns:
            Dictionary with status counts
        """
        logger.info("Fetching transfer status counts...")

        counts = {
            "draft": self.get_status_count("/stockTransferList", {"Status": "DRAFT"}),
            "in_transit": self.get_status_count("/stockTransferList", {"Status": "IN TRANSIT"}),
        }

        return counts
