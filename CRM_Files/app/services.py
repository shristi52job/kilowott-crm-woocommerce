"""
Service Layer for Kilowott CRM.
Coordinates business logic between Repositories, WooCommerce Webhooks,
and the Agentic AI Engine.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.repositories import CustomerRepository, OrderRepository, CommunicationRepository
from app.agent import AgenticCustomerEngine
from app.models import Customer, Order, CommunicationLog, OrderItem


class CRMService:
    """Orchestrates CRM business domain operations and agentic automation."""

    def __init__(
        self,
        customer_repo: CustomerRepository,
        order_repo: OrderRepository,
        comm_repo: CommunicationRepository,
        agent_engine: Optional[AgenticCustomerEngine] = None
    ):
        self.customer_repo = customer_repo
        self.order_repo = order_repo
        self.comm_repo = comm_repo
        self.agent_engine = agent_engine or AgenticCustomerEngine()

    def process_woocommerce_order_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests an incoming WooCommerce order webhook payload.
        Idempotent: updates existing order if duplicate, or creates fresh record.
        Automatically updates customer LTV and triggers agentic intelligence.
        """
        woo_order_id = payload.get("id")
        if not woo_order_id:
            raise ValueError("Invalid webhook payload: missing order ID")

        # 1. Parse Customer details from billing
        billing = payload.get("billing", {})
        email = billing.get("email") or payload.get("customer_email") or f"customer_{woo_order_id}@example.com"
        first_name = billing.get("first_name") or "Valued"
        last_name = billing.get("last_name") or "Customer"
        phone = billing.get("phone", "")

        customer = self.customer_repo.get_by_email(email)
        total_amount = float(payload.get("total", 0.0))
        status = payload.get("status", "completed").lower()

        if not customer:
            customer = self.customer_repo.create({
                "woocommerce_id": payload.get("customer_id") or None,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "total_spent": total_amount if status not in ["cancelled", "refunded"] else 0.0,
                "order_count": 1 if status not in ["cancelled", "refunded"] else 0,
                "lifecycle_stage": "New Customer"
            })
        else:
            # Update existing customer aggregates
            if status not in ["cancelled", "refunded"]:
                customer.total_spent += total_amount
                customer.order_count += 1
            customer.first_name = first_name
            customer.last_name = last_name
            if phone:
                customer.phone = phone
            customer = self.customer_repo.update(customer)

        # 2. Extract Line Items
        raw_items = payload.get("line_items", [])
        items: List[OrderItem] = []
        for it in raw_items:
            items.append(OrderItem(
                product_id=it.get("product_id", 0),
                name=it.get("name", "Product Item"),
                quantity=it.get("quantity", 1),
                price=float(it.get("price", it.get("total", 0.0)))
            ))

        # 3. Create or Update Order Record
        order_date = payload.get("date_created") or datetime.utcnow().isoformat()
        existing_order = self.order_repo.get_by_woocommerce_id(woo_order_id)
        if existing_order:
            order = existing_order
        else:
            order = self.order_repo.create({
                "woocommerce_order_id": woo_order_id,
                "customer_id": customer.id,
                "customer_email": customer.email,
                "total_amount": total_amount,
                "currency": payload.get("currency", "INR"),
                "status": status,
                "items": items,
                "customer_notes": payload.get("customer_note") or "",
                "order_date": order_date
            })

        # 4. Trigger Autonomous Agent Loop
        all_customer_orders = self.order_repo.list_by_customer_id(customer.id)
        updated_customer, comm_draft_data = self.agent_engine.analyze_and_act(
            customer=customer,
            recent_order=order,
            all_orders=all_customer_orders
        )
        self.customer_repo.update(updated_customer)
        comm_log = self.comm_repo.create(comm_draft_data)

        return {
            "status": "success",
            "message": "Order processed and agent workflow generated",
            "order": order,
            "customer": updated_customer,
            "communication": comm_log
        }

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates high-level business intelligence metrics for the dashboard."""
        customers = self.customer_repo.list_all(1000)
        orders = self.order_repo.list_all(1000)
        comms = self.comm_repo.list_all(1000)

        total_revenue = sum(o.total_amount for o in orders if o.status not in ["cancelled", "refunded"])
        total_customers = len(customers)
        vip_count = sum(1 for c in customers if c.lifecycle_stage == "VIP Customer")
        at_risk_count = sum(1 for c in customers if c.lifecycle_stage == "At Risk")
        pending_comms = sum(1 for cm in comms if cm.status == "draft")

        return {
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "total_orders": len(orders),
            "vip_count": vip_count,
            "at_risk_count": at_risk_count,
            "pending_comms": pending_comms
        }
