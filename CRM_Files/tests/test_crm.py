"""
Comprehensive Automated Test Suite for Kilowott CRM Integration.
Demonstrates Software Engineering Best Practices:
- Unit Testing for Models, Repositories, and Agentic Reasoning
- End-to-End (E2E) Integration Testing for WooCommerce Webhooks and REST Endpoints
"""

import unittest
import os
import json
from fastapi.testclient import TestClient

TEST_DB = "/tmp/test_crm_isolated.db"
os.environ["CRM_DB_PATH"] = TEST_DB

from app.database import init_db
from app.repositories import CustomerRepository, OrderRepository, CommunicationRepository
from app.agent import AgenticCustomerEngine
from app.models import OrderItem, Order, Customer
from app.main import app, customer_repo, order_repo, comm_repo, crm_service


class TestCRMRepositories(unittest.TestCase):
    """Unit tests for the Data Access Layer (Repository Pattern)."""

    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_db(TEST_DB)
        self.cust_repo = CustomerRepository(TEST_DB)
        self.order_repo = OrderRepository(TEST_DB)
        self.comm_repo = CommunicationRepository(TEST_DB)

    def test_customer_creation_and_retrieval(self):
        customer = self.cust_repo.create({
            "email": "test_repo@example.com",
            "first_name": "Rahul",
            "last_name": "Dravid",
            "phone": "+919999999999",
            "tags": ["Cricket", "VIP"]
        })
        self.assertIsNotNone(customer.id)
        self.assertEqual(customer.email, "test_repo@example.com")
        self.assertIn("VIP", customer.tags)

        # Retrieve by email
        fetched = self.cust_repo.get_by_email("test_repo@example.com")
        self.assertEqual(fetched.id, customer.id)
        self.assertEqual(fetched.first_name, "Rahul")

    def test_order_creation_and_line_items(self):
        customer = self.cust_repo.create({
            "email": "order_test@example.com",
            "first_name": "Sita",
            "last_name": "Ram"
        })
        order = self.order_repo.create({
            "woocommerce_order_id": 9901,
            "customer_id": customer.id,
            "customer_email": customer.email,
            "total_amount": 1500.0,
            "status": "completed",
            "items": [OrderItem(product_id=1, name="Keyboard", quantity=1, price=1500.0)]
        })
        self.assertEqual(order.woocommerce_order_id, 9901)
        self.assertEqual(len(order.items), 1)
        self.assertEqual(order.items[0].name, "Keyboard")


class TestAgenticAIEngine(unittest.TestCase):
    """Unit tests for the Perception-Reasoning-Action loop in Agentic AI."""

    def setUp(self):
        self.agent = AgenticCustomerEngine()

    def test_first_time_customer_flow(self):
        customer = Customer(
            id=1, email="new@example.com", first_name="Aman", last_name="Gupta",
            total_spent=2000.0, order_count=1, lifecycle_stage="Lead", tags=[],
            created_at="2026-10-15T10:00:00", updated_at="2026-10-15T10:00:00"
        )
        order = Order(
            id=1, woocommerce_order_id=5001, customer_id=1, customer_email="new@example.com",
            total_amount=2000.0, status="completed", items=[OrderItem(product_id=1, name="Desk Mat", quantity=1, price=2000.0)],
            customer_notes="", order_date="2026-10-15T10:00:00"
        )

        updated_customer, comm = self.agent.analyze_and_act(customer, order, [order])
        self.assertEqual(updated_customer.lifecycle_stage, "New Customer")
        self.assertIn("First-Time Buyer", updated_customer.tags)
        self.assertIn("Welcome to our store", comm["subject"])

    def test_vip_tier_qualification(self):
        customer = Customer(
            id=2, email="vip@example.com", first_name="Vikram", last_name="Mehta",
            total_spent=25000.0, order_count=4, lifecycle_stage="Lead", tags=[],
            created_at="2026-10-15T10:00:00", updated_at="2026-10-15T10:00:00"
        )
        order = Order(
            id=2, woocommerce_order_id=5002, customer_id=2, customer_email="vip@example.com",
            total_amount=10000.0, status="completed", items=[OrderItem(product_id=2, name="High-End Workstation", quantity=1, price=10000.0)],
            customer_notes="", order_date="2026-10-15T10:00:00"
        )

        updated_customer, comm = self.agent.analyze_and_act(customer, order, [order])
        self.assertEqual(updated_customer.lifecycle_stage, "VIP Customer")
        self.assertIn("VIP Tier", updated_customer.tags)
        self.assertIn("Exclusive VIP Perks", comm["subject"])

    def test_negative_sentiment_and_cancellation(self):
        customer = Customer(
            id=3, email="upset@example.com", first_name="Kavita", last_name="Rao",
            total_spent=0.0, order_count=0, lifecycle_stage="Lead", tags=[],
            created_at="2026-10-15T10:00:00", updated_at="2026-10-15T10:00:00"
        )
        order = Order(
            id=3, woocommerce_order_id=5003, customer_id=3, customer_email="upset@example.com",
            total_amount=4000.0, status="cancelled", items=[OrderItem(product_id=3, name="Smart Bulb", quantity=1, price=4000.0)],
            customer_notes="Item arrived damaged previously, cancel this now!", order_date="2026-10-15T10:00:00"
        )

        updated_customer, comm = self.agent.analyze_and_act(customer, order, [order])
        self.assertEqual(updated_customer.lifecycle_stage, "At Risk")
        self.assertIn("Needs Retention Attention", updated_customer.tags)
        self.assertIn("sorry", comm["subject"].lower())


class TestE2EIntegration(unittest.TestCase):
    """End-to-End integration tests simulating live WooCommerce webhook ingestion and REST APIs."""

    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_db(TEST_DB)
        customer_repo.db_path = TEST_DB
        order_repo.db_path = TEST_DB
        comm_repo.db_path = TEST_DB
        crm_service.customer_repo.db_path = TEST_DB
        crm_service.order_repo.db_path = TEST_DB
        crm_service.comm_repo.db_path = TEST_DB
        self.client = TestClient(app)

    def test_healthcheck(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

    def test_e2e_woocommerce_webhook_flow(self):
        webhook_payload = {
            "id": 88123,
            "status": "completed",
            "currency": "INR",
            "total": "4500.00",
            "billing": {
                "first_name": "Neha",
                "last_name": "Kapoor",
                "email": "neha.kapoor@example.com",
                "phone": "+91 9123456780"
            },
            "line_items": [
                {
                    "product_id": 12,
                    "name": "Wireless Charging Stand",
                    "quantity": 1,
                    "total": "4500.00"
                }
            ],
            "customer_note": "Please deliver during business hours."
        }

        # 1. Post Webhook
        post_res = self.client.post("/api/webhooks/woocommerce/order", json=webhook_payload)
        self.assertEqual(post_res.status_code, 200)
        resp_data = post_res.json()
        self.assertEqual(resp_data["status"], "success")

        # 2. Verify Customer created
        cust_res = self.client.get("/api/customers")
        self.assertEqual(cust_res.status_code, 200)
        customers = cust_res.json()
        neha = next((c for c in customers if c["email"] == "neha.kapoor@example.com"), None)
        self.assertIsNotNone(neha)
        self.assertEqual(neha["total_spent"], 4500.0)

        # 3. Verify Order recorded
        orders_res = self.client.get("/api/orders")
        orders = orders_res.json()
        order_match = next((o for o in orders if o["woocommerce_order_id"] == 88123), None)
        self.assertIsNotNone(order_match)

        # 4. Verify AI Communication Draft generated
        comms_res = self.client.get("/api/communications")
        comms = comms_res.json()
        comm_match = next((c for c in comms if c["customer_email"] == "neha.kapoor@example.com"), None)
        self.assertIsNotNone(comm_match)
        self.assertEqual(comm_match["status"], "draft")

        # 5. Approve and send communication
        approve_res = self.client.post(f"/api/communications/{comm_match['id']}/send")
        self.assertEqual(approve_res.status_code, 200)
        self.assertEqual(approve_res.json()["communication"]["status"], "sent")


if __name__ == "__main__":
    unittest.main()
