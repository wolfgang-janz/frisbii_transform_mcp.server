"""
Frisbii Transform MCP Server

A comprehensive MCP server for interacting with the Frisbii Transform subscription and billing API.
Provides tools for customer management, contract operations, subscription handling, and more.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import json

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from authlib.integrations.httpx_client import OAuth2Client
from authlib.oauth2.rfc6749 import OAuth2Token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP instance
mcp = FastMCP("Frisbii Transform")

# API Configuration
API_BASE_URL = os.getenv("FRISBII_BASE_URL", "https://sandbox.billwerk.com")
API_KEY = os.getenv("FRISBII_API_KEY")
LEGAL_ENTITY_ID = os.getenv("FRISBII_LEGAL_ENTITY_ID")

# OAuth2 Configuration
OAUTH2_CLIENT_ID = os.getenv("FRISBII_OAUTH2_CLIENT_ID")
OAUTH2_CLIENT_SECRET = os.getenv("FRISBII_OAUTH2_CLIENT_SECRET")
OAUTH2_TOKEN_URL = os.getenv("FRISBII_OAUTH2_TOKEN_URL", f"{API_BASE_URL}/oauth/token")
OAUTH2_SCOPE = os.getenv("FRISBII_OAUTH2_SCOPE")
TOKEN_STORAGE_FILE = os.getenv("FRISBII_TOKEN_STORAGE", "frisbii_oauth_token.json")

# Authentication configuration check
auth_method = None
if OAUTH2_CLIENT_ID and OAUTH2_CLIENT_SECRET:
    auth_method = "oauth2"
    logger.info("Using OAuth2 authentication")
elif API_KEY:
    auth_method = "bearer"
    logger.info("Using Bearer token authentication")
else:
    logger.warning("No authentication method configured. Please set either FRISBII_API_KEY or OAuth2 credentials.")

# Legal Entity ID validation - now optional
if not LEGAL_ENTITY_ID:
    logger.warning("FRISBII_LEGAL_ENTITY_ID not set - x-selected-legal-entity-id header will be omitted from requests")

# Token storage functions
def save_token(token: Dict[str, Any]) -> None:
    """Save OAuth2 token to file."""
    try:
        with open(TOKEN_STORAGE_FILE, 'w') as f:
            json.dump(token, f)
        logger.info("OAuth2 token saved successfully")
    except Exception as e:
        logger.error(f"Failed to save OAuth2 token: {e}")

def load_token() -> Optional[Dict[str, Any]]:
    """Load OAuth2 token from file."""
    try:
        if os.path.exists(TOKEN_STORAGE_FILE):
            with open(TOKEN_STORAGE_FILE, 'r') as f:
                token = json.load(f)
            logger.info("OAuth2 token loaded successfully")
            return token
    except Exception as e:
        logger.error(f"Failed to load OAuth2 token: {e}")
    return None

def is_token_valid(token: Dict[str, Any]) -> bool:
    """Check if OAuth2 token is still valid."""
    if not token or 'expires_at' not in token:
        return False
    
    expires_at = token.get('expires_at', 0)
    # Add 60 second buffer before expiration
    return datetime.now().timestamp() < (expires_at - 60)

# HTTP Client configuration
def get_oauth2_token() -> Optional[str]:
    """Get a valid OAuth2 access token."""
    if not OAUTH2_CLIENT_ID or not OAUTH2_CLIENT_SECRET:
        return None
    
    # Try to load existing token
    token = load_token()
    
    # Check if token is valid
    if token and is_token_valid(token):
        return token.get('access_token')
    
    # Request new token
    try:
        client = OAuth2Client(
            client_id=OAUTH2_CLIENT_ID,
            client_secret=OAUTH2_CLIENT_SECRET,
            token_endpoint=OAUTH2_TOKEN_URL
        )
        
        token = client.fetch_token(
            url=OAUTH2_TOKEN_URL,
            grant_type='client_credentials',
            scope=OAUTH2_SCOPE
        )
        
        # Add expires_at if not present
        if 'expires_at' not in token and 'expires_in' in token:
            token['expires_at'] = datetime.now().timestamp() + token['expires_in']
        
        save_token(token)
        return token.get('access_token')
        
    except Exception as e:
        logger.error(f"Failed to fetch OAuth2 token: {e}")
        return None

def get_client() -> httpx.Client:
    """Get configured HTTP client with authentication headers."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Add legal entity ID header only if provided
    if LEGAL_ENTITY_ID:
        headers["x-selected-legal-entity-id"] = LEGAL_ENTITY_ID
    
    # Choose authentication method
    if auth_method == "oauth2":
        access_token = get_oauth2_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        else:
            logger.error("Failed to obtain OAuth2 token")
            raise Exception("Authentication failed: Unable to obtain OAuth2 token")
    elif auth_method == "bearer" and API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    else:
        logger.error("No valid authentication method available")
        raise Exception("Authentication failed: No valid credentials configured")
    
    return httpx.Client(base_url=API_BASE_URL, headers=headers, timeout=30.0)

# Pydantic models for request/response validation
class CustomerCreate(BaseModel):
    firstName: str = Field(..., description="Customer's first name")
    lastName: str = Field(..., description="Customer's last name")
    emailAddress: str = Field(..., description="Customer's email address")
    companyName: Optional[str] = Field(None, description="Company name")
    language: Optional[str] = Field("en-US", description="Language preference")
    locale: Optional[str] = Field("en-US", description="Locale preference")
    customerType: Optional[str] = Field("Consumer", description="Customer type")

class ContractCreate(BaseModel):
    customerId: str = Field(..., description="Customer ID for the contract")
    planVariantId: str = Field(..., description="Plan variant ID")
    startDate: Optional[str] = Field(None, description="Contract start date (ISO format)")
    endDate: Optional[str] = Field(None, description="Contract end date (ISO format)")

class ComponentSubscriptionCreate(BaseModel):
    componentId: str = Field(..., description="Component ID to subscribe to")
    quantity: float = Field(..., description="Quantity of the component")
    startDate: Optional[str] = Field(None, description="Subscription start date")
    memo: Optional[str] = Field(None, description="Optional memo")

class MeteredUsageCreate(BaseModel):
    componentId: str = Field(..., description="Component ID for usage tracking")
    quantity: float = Field(..., description="Usage quantity")
    memo: Optional[str] = Field(None, description="Optional usage memo")
    dueDate: Optional[str] = Field(None, description="Due date for the usage")

# Customer Management Tools

@mcp.tool()
def get_customers(
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve a list of customers.
    
    Args:
        search: Search customers by name, email, or external ID
        status_filter: Filter by customer status (Normal, Unconfirmed, Deleted)
        from_cursor: Cursor for pagination
        take: Number of customers to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if search:
            params["search"] = search
        if status_filter:
            params["statusFilter"] = status_filter
        if from_cursor:
            params["from"] = from_cursor
            
        response = client.get("/api/v1/customers", params=params)
        response.raise_for_status()
        data = response.json()
        
        # Ensure we return a dict structure for MCP compatibility
        if isinstance(data, list):
            return {"customers": data, "count": len(data)}
        return data

@mcp.tool()
def get_customer(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific customer by ID.
    
    Args:
        customer_id: The customer's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/customers/{customer_id}")
        response.raise_for_status()
        data = response.json()
        # Always return a dict with a key for MCP compatibility
        return {"customer": data}

@mcp.tool()
def create_customer(customer_data: CustomerCreate) -> Dict[str, Any]:
    """
    Create a new customer.
    
    Args:
        customer_data: Customer information including name, email, and other details
    """
    with get_client() as client:
        response = client.post("/api/v1/customers", json=customer_data.model_dump())
        response.raise_for_status()
        data = response.json()
        return {"customer": data}

@mcp.tool()
def update_customer(customer_id: str, customer_data: CustomerCreate) -> Dict[str, Any]:
    """
    Update an existing customer.
    
    Args:
        customer_id: The customer's unique identifier
        customer_data: Updated customer information
    """
    with get_client() as client:
        response = client.put(f"/api/v1/customers/{customer_id}", json=customer_data.model_dump())
        response.raise_for_status()
        data = response.json()
        return {"customer": data}

@mcp.tool()
def delete_customer(customer_id: str) -> Dict[str, Any]:
    """
    Delete a customer (GDPR compliant).
    
    Args:
        customer_id: The customer's unique identifier
    """
    with get_client() as client:
        response = client.delete(f"/api/v1/customers/{customer_id}")
        response.raise_for_status()
        return {"message": "Customer deleted successfully"}

# Contract Management Tools

@mcp.tool()
def get_contracts(
    from_cursor: Optional[str] = None,
    take: int = 50,
    external_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve a list of contracts.
    
    Args:
        from_cursor: Cursor for pagination
        take: Number of contracts to return (max 500)
        external_id: Filter by external ID
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if from_cursor:
            params["from"] = from_cursor
        if external_id:
            params["externalId"] = external_id
            
        response = client.get("/api/v1/contracts", params=params)
        response.raise_for_status()
        data = response.json()
        
        # Ensure we return a dict structure for MCP compatibility
        if isinstance(data, list):
            return {"contracts": data, "count": len(data)}
        return data

@mcp.tool()
def get_contract(contract_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific contract by ID.
    
    Args:
        contract_id: The contract's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/contracts/{contract_id}")
        response.raise_for_status()
        data = response.json()
        return {"contract": data}

@mcp.tool()
def get_contracts_by_customer(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve all contracts for a specific customer.
    
    Args:
        customer_id: The customer's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/customers/{customer_id}/contracts")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"contracts": data, "count": len(data)}
        return data

@mcp.tool()
def cancel_contract(contract_id: str, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Cancel a contract.
    
    Args:
        contract_id: The contract's unique identifier
        end_date: Optional end date for the contract (ISO format)
    """
    with get_client() as client:
        data = {}
        if end_date:
            data["endDate"] = end_date
        response = client.post(f"/api/v1/contracts/{contract_id}/end", json=data)
        response.raise_for_status()
        data = response.json()
        return {"contract": data}

@mcp.tool()
def pause_contract(contract_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Pause a contract.
    
    Args:
        contract_id: The contract's unique identifier
        start_date: Optional pause start date (ISO format)
        end_date: Optional pause end date (ISO format)
    """
    with get_client() as client:
        data = {}
        if start_date:
            data["startDate"] = start_date
        if end_date:
            data["endDate"] = end_date
        response = client.post(f"/api/v1/contracts/{contract_id}/pause", json=data)
        response.raise_for_status()
        data = response.json()
        return {"contract": data}

@mcp.tool()
def resume_contract(contract_id: str, resume_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Resume a paused contract.
    
    Args:
        contract_id: The contract's unique identifier
        resume_date: Optional resume date (ISO format)
    """
    with get_client() as client:
        data = {}
        if resume_date:
            data["resumeDate"] = resume_date
        response = client.post(f"/api/v1/contracts/{contract_id}/resume", json=data)
        response.raise_for_status()
        data = response.json()
        return {"contract": data}

# Component Subscription Tools

@mcp.tool()
def get_component_subscriptions(
    contract_id: Optional[str] = None,
    component_id: Optional[str] = None,
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve component subscriptions.
    
    Args:
        contract_id: Filter by contract ID
        component_id: Filter by component ID
        from_cursor: Cursor for pagination
        take: Number of subscriptions to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if contract_id:
            params["contractId"] = contract_id
        if component_id:
            params["componentId"] = component_id
        if from_cursor:
            params["from"] = from_cursor
        response = client.get("/api/v1/componentsubscriptions", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"component_subscriptions": data, "count": len(data)}
        return data

@mcp.tool()
def get_contract_component_subscriptions(contract_id: str) -> Dict[str, Any]:
    """
    Retrieve all component subscriptions for a specific contract.
    
    Args:
        contract_id: The contract's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/contracts/{contract_id}/componentsubscriptions")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"component_subscriptions": data, "count": len(data)}
        return data

@mcp.tool()
def create_component_subscription(contract_id: str, subscription_data: ComponentSubscriptionCreate) -> Dict[str, Any]:
    """
    Create a new component subscription for a contract.
    
    Args:
        contract_id: The contract's unique identifier
        subscription_data: Component subscription details
    """
    with get_client() as client:
        response = client.post(
            f"/api/v1/contracts/{contract_id}/componentsubscriptions", 
            json=subscription_data.model_dump()
        )
        response.raise_for_status()
        data = response.json()
        return {"component_subscription": data}

@mcp.tool()
def end_component_subscription(
    contract_id: str, 
    subscription_id: str, 
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    End a component subscription.
    
    Args:
        contract_id: The contract's unique identifier
        subscription_id: The component subscription's unique identifier
        end_date: Optional end date (ISO format)
    """
    with get_client() as client:
        data = {}
        if end_date:
            data["endDate"] = end_date
        response = client.post(
            f"/api/v1/contracts/{contract_id}/componentsubscriptions/{subscription_id}/end",
            json=data
        )
        response.raise_for_status()
        data = response.json()
        return {"component_subscription": data}

# Usage Tracking Tools

@mcp.tool()
def get_usage_by_contract(
    contract_id: str,
    from_datetime: Optional[str] = None,
    until_datetime: Optional[str] = None,
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve usage data for a specific contract.
    
    Args:
        contract_id: The contract's unique identifier
        from_datetime: Start date for usage data (ISO format)
        until_datetime: End date for usage data (ISO format)
        from_cursor: Cursor for pagination
        take: Number of usage records to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if from_datetime:
            params["fromDateTime"] = from_datetime
        if until_datetime:
            params["untilDateTime"] = until_datetime
        if from_cursor:
            params["from"] = from_cursor
        response = client.get(f"/api/v1/contracts/{contract_id}/usage", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"usage": data, "count": len(data)}
        return data

@mcp.tool()
def create_usage_record(contract_id: str, usage_data: MeteredUsageCreate) -> Dict[str, Any]:
    """
    Create a new metered usage record for a contract.
    
    Args:
        contract_id: The contract's unique identifier
        usage_data: Usage record details
    """
    with get_client() as client:
        response = client.post(
            f"/api/v1/contracts/{contract_id}/usage",
            json=usage_data.model_dump()
        )
        response.raise_for_status()
        data = response.json()
        return {"usage_record": data}

@mcp.tool()
def delete_usage_record(contract_id: str, usage_id: str) -> Dict[str, Any]:
    """
    Delete a usage record.
    
    Args:
        contract_id: The contract's unique identifier
        usage_id: The usage record's unique identifier
    """
    with get_client() as client:
        response = client.delete(f"/api/v1/contracts/{contract_id}/usage/{usage_id}")
        response.raise_for_status()
        return {"message": "Usage record deleted successfully"}

# Invoice Management Tools

@mcp.tool()
def get_invoices(
    contract_id: Optional[str] = None,
    search: Optional[str] = None,
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve invoices.
    
    Args:
        contract_id: Filter by contract ID
        search: Search invoices by customer name
        from_cursor: Cursor for pagination
        take: Number of invoices to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if contract_id:
            params["contractId"] = contract_id
        if search:
            params["search"] = search
        if from_cursor:
            params["from"] = from_cursor
        response = client.get("/api/v1/invoices", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"invoices": data, "count": len(data)}
        return data

@mcp.tool()
def get_invoice(invoice_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific invoice by ID.
    
    Args:
        invoice_id: The invoice's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/invoices/{invoice_id}")
        response.raise_for_status()
        data = response.json()
        return {"invoice": data}

@mcp.tool()
def bill_contract(contract_id: str) -> Dict[str, Any]:
    """
    Execute interim billing for a specific contract.
    
    Args:
        contract_id: The contract's unique identifier
    """
    with get_client() as client:
        response = client.post(f"/api/v1/contracts/{contract_id}/bill")
        response.raise_for_status()
        data = response.json()
        return {"billing": data}

# Plan Management Tools

@mcp.tool()
def get_plan_groups(
    from_cursor: Optional[str] = None,
    search: Optional[str] = None,
    show_hidden: bool = False,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve plan groups.
    
    Args:
        from_cursor: Cursor for pagination
        search: Search by plan group name
        show_hidden: Include hidden plan groups
        take: Number of plan groups to return (max 500)
    """
    with get_client() as client:
        params = {"take": take, "showHidden": show_hidden}
        if from_cursor:
            params["from"] = from_cursor
        if search:
            params["search"] = search
        response = client.get("/api/v1/plangroups", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"plan_groups": data, "count": len(data)}
        return data

@mcp.tool()
def get_plan_group(plan_group_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific plan group by ID.
    
    Args:
        plan_group_id: The plan group's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/plangroups/{plan_group_id}")
        response.raise_for_status()
        data = response.json()
        return {"plan_group": data}

@mcp.tool()
def get_plans(
    plan_group_id: Optional[str] = None,
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve plans.
    
    Args:
        plan_group_id: Filter by plan group ID
        from_cursor: Cursor for pagination
        take: Number of plans to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if plan_group_id:
            params["planGroupId"] = plan_group_id
        if from_cursor:
            params["from"] = from_cursor
        response = client.get("/api/v1/plans", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"plans": data, "count": len(data)}
        return data

@mcp.tool()
def get_plan(plan_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific plan by ID.
    
    Args:
        plan_id: The plan's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/plans/{plan_id}")
        response.raise_for_status()
        data = response.json()
        return {"plan": data}

@mcp.tool()
def get_plan_variants(
    plan_id: Optional[str] = None,
    external_id: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve plan variants.
    
    Args:
        plan_id: Filter by plan ID
        external_id: Filter by external ID
        take: Number of plan variants to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if plan_id:
            params["planId"] = plan_id
        if external_id:
            params["externalId"] = external_id
        response = client.get("/api/v1/planvariants", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"plan_variants": data, "count": len(data)}
        return data

@mcp.tool()
def get_plan_variant(plan_variant_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific plan variant by ID.
    
    Args:
        plan_variant_id: The plan variant's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/planvariants/{plan_variant_id}")
        response.raise_for_status()
        data = response.json()
        return {"plan_variant": data}

# Component Management Tools

@mcp.tool()
def get_components(
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve components.
    
    Args:
        from_cursor: Cursor for pagination
        take: Number of components to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if from_cursor:
            params["from"] = from_cursor
        response = client.get("/api/v1/components", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"components": data, "count": len(data)}
        return data

@mcp.tool()
def get_component(component_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific component by ID.
    
    Args:
        component_id: The component's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/components/{component_id}")
        response.raise_for_status()
        data = response.json()
        return {"component": data}

# Payment and Transaction Tools

@mcp.tool()
def get_payment_transactions(
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve payment transactions.
    
    Args:
        from_cursor: Cursor for pagination
        take: Number of transactions to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if from_cursor:
            params["from"] = from_cursor
        response = client.get("/api/v1/paymenttransactions", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"payment_transactions": data, "count": len(data)}
        return data

@mcp.tool()
def get_payment_transaction(transaction_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific payment transaction by ID.
    
    Args:
        transaction_id: The transaction's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/paymenttransactions/{transaction_id}")
        response.raise_for_status()
        data = response.json()
        return {"payment_transaction": data}

@mcp.tool()
def record_contract_payment(
    contract_id: str,
    amount: float,
    currency: str,
    description: str,
    booking_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record an external payment for a contract.
    
    Args:
        contract_id: The contract's unique identifier
        amount: Payment amount (positive for payment, negative for refund)
        currency: Currency code (e.g., EUR, USD)
        description: Payment description
        booking_date: Optional booking date (YYYY-MM-DD format)
    """
    with get_client() as client:
        data = {
            "amount": amount,
            "currency": currency,
            "description": description
        }
        if booking_date:
            data["bookingDate"] = booking_date
        response = client.post(f"/api/v1/contracts/{contract_id}/payment", json=data)
        response.raise_for_status()
        data = response.json()
        return {"payment": data}

# Subscription and Order Tools

@mcp.tool()
def get_subscriptions(
    show_hidden: bool = False,
    search: Optional[str] = None,
    plan_group_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    contract_status: Optional[str] = None,
    from_cursor: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve combined customer and contract subscription data.
    
    Args:
        show_hidden: Include hidden subscriptions
        search: Search term
        plan_group_id: Filter by plan group ID
        plan_id: Filter by plan ID
        contract_status: Filter by contract status
        from_cursor: Cursor for pagination
        take: Number of subscriptions to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take, "showHidden": show_hidden}
        if search:
            params["search"] = search
        if plan_group_id:
            params["planGroupId"] = plan_group_id
        if plan_id:
            params["planId"] = plan_id
        if contract_status:
            params["contractStatus"] = contract_status
        if from_cursor:
            params["from"] = from_cursor
        response = client.get("/api/v1/subscriptions", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"subscriptions": data, "count": len(data)}
        return data

# Reporting Tools

@mcp.tool()
def get_reports(take: int = 50) -> Dict[str, Any]:
    """
    Retrieve available reports.
    
    Args:
        take: Number of reports to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        response = client.get("/api/v1/reports", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"reports": data, "count": len(data)}
        return data

@mcp.tool()
def get_report(report_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific report by ID.
    
    Args:
        report_id: The report's unique identifier
    """
    with get_client() as client:
        response = client.get(f"/api/v1/reports/{report_id}")
        response.raise_for_status()
        data = response.json()
        return {"report": data}

@mcp.tool()
def generate_report(report_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate a report with optional parameters.
    
    Args:
        report_id: The report's unique identifier
        parameters: Optional report parameters
    """
    with get_client() as client:
        data = parameters or {}
        response = client.post(f"/api/v1/reports/{report_id}", json=data)
        response.raise_for_status()
        data = response.json()
        return {"report_result": data}

# Webhook Management Tools

@mcp.tool()
def get_webhooks() -> Dict[str, Any]:
    """
    Retrieve all registered webhooks.
    """
    with get_client() as client:
        response = client.get("/api/v1/webhooks")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"webhooks": data, "count": len(data)}
        return data

@mcp.tool()
def get_webhook_events(
    from_cursor: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    take: int = 50
) -> Dict[str, Any]:
    """
    Retrieve webhook events.
    
    Args:
        from_cursor: Cursor for pagination
        date_from: Filter events from this date (ISO format)
        date_to: Filter events until this date (ISO format)
        status: Filter by event status
        take: Number of events to return (max 500)
    """
    with get_client() as client:
        params: Dict[str, Any] = {"take": take}
        if from_cursor:
            params["from"] = from_cursor
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if status:
            params["status"] = status
        response = client.get("/api/v1/webhookevents", params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return {"webhook_events": data, "count": len(data)}
        return data

# OAuth2 Management Tools

@mcp.tool()
def oauth2_status() -> Dict[str, Any]:
    """
    Check OAuth2 authentication status and configuration.
    
    Returns information about the current OAuth2 configuration and token status.
    """
    status = {
        "oauth2_configured": bool(OAUTH2_CLIENT_ID and OAUTH2_CLIENT_SECRET),
        "bearer_token_configured": bool(API_KEY),
        "legal_entity_id_configured": bool(LEGAL_ENTITY_ID),
        "legal_entity_id": LEGAL_ENTITY_ID if LEGAL_ENTITY_ID else "Not configured",
        "current_auth_method": auth_method,
        "token_storage_file": TOKEN_STORAGE_FILE,
        "oauth2_token_url": OAUTH2_TOKEN_URL,
        "oauth2_scope": OAUTH2_SCOPE
    }
    
    if auth_method == "oauth2":
        token = load_token()
        if token:
            status["token_exists"] = True
            status["token_valid"] = is_token_valid(token)
            status["token_expires_at"] = token.get('expires_at')
            if status["token_expires_at"]:
                expires_datetime = datetime.fromtimestamp(status["token_expires_at"])
                status["token_expires_datetime"] = expires_datetime.isoformat()
        else:
            status["token_exists"] = False
            status["token_valid"] = False
    
    return status

@mcp.tool()
def oauth2_refresh_token() -> Dict[str, Any]:
    """
    Force refresh of OAuth2 token.
    
    This will request a new OAuth2 token regardless of the current token's validity.
    """
    if not OAUTH2_CLIENT_ID or not OAUTH2_CLIENT_SECRET:
        return {
            "success": False,
            "error": "OAuth2 credentials not configured"
        }
    
    try:
        # Remove existing token file to force refresh
        if os.path.exists(TOKEN_STORAGE_FILE):
            os.remove(TOKEN_STORAGE_FILE)
        
        # Get new token
        access_token = get_oauth2_token()
        
        if access_token:
            return {
                "success": True,
                "message": "OAuth2 token refreshed successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to obtain new OAuth2 token"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to refresh OAuth2 token: {str(e)}"
        }

@mcp.tool()
def oauth2_clear_token() -> Dict[str, Any]:
    """
    Clear stored OAuth2 token.
    
    This will remove the stored OAuth2 token file, forcing re-authentication on next request.
    """
    try:
        if os.path.exists(TOKEN_STORAGE_FILE):
            os.remove(TOKEN_STORAGE_FILE)
            return {
                "success": True,
                "message": "OAuth2 token cleared successfully"
            }
        else:
            return {
                "success": True,
                "message": "No OAuth2 token file found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to clear OAuth2 token: {str(e)}"
        }

def main():
    """Main entry point for the MCP server."""
    logger.info("Starting Frisbii Transform MCP Server...")
    mcp.run()

if __name__ == "__main__":
    main()
