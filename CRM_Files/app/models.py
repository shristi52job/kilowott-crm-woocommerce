"""
Domain Models and Pydantic Schemas for Kilowott CRM Integration.
Implements data validation and strict typing across entities.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class CustomerBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    woocommerce_id: Optional[int] = None


class CustomerCreate(CustomerBase):
    pass


class Customer(CustomerBase):
    id: int
    total_spent: float = 0.0
    order_count: int = 0
    lifecycle_stage: str = "Lead"  # Lead, New Customer, Promising, VIP, At Risk, Churn
    tags: List[str] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OrderItem(BaseModel):
    product_id: int
    name: str
    quantity: int
    price: float


class OrderBase(BaseModel):
    woocommerce_order_id: int
    customer_email: str
    total_amount: float
    currency: str = "INR"
    status: str = "completed"  # pending, processing, completed, refunded, cancelled
    items: List[OrderItem] = []
    customer_notes: Optional[str] = None


class Order(OrderBase):
    id: int
    customer_id: int
    order_date: str

    class Config:
        from_attributes = True


class CommunicationLog(BaseModel):
    id: int
    customer_id: int
    customer_email: str
    trigger_event: str
    subject: str
    body: str
    status: str = "draft"  # draft, sent
    sentiment: str = "neutral"
    agent_reasoning: str
    created_at: str

    class Config:
        from_attributes = True


class WooCommerceWebhookOrder(BaseModel):
    id: int
    status: str
    currency: str = "INR"
    total: str
    billing: Dict[str, Any]
    line_items: List[Dict[str, Any]]
    customer_note: Optional[str] = None
    date_created: Optional[str] = None
