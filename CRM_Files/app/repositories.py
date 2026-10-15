"""
Repository Pattern Implementation for Kilowott CRM Integration.
Decouples data persistence mechanisms from core business and agentic workflows.
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.database import get_db_connection, DEFAULT_DB_PATH
from app.models import Customer, Order, CommunicationLog, OrderItem


class CustomerRepository:
    """Handles CRUD operations for Customer entities."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_customer(row)

    def get_by_email(self, email: str) -> Optional[Customer]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers WHERE LOWER(email) = LOWER(?)", (email,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_customer(row)

    def list_all(self, limit: int = 100) -> List[Customer]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customers ORDER BY total_spent DESC, updated_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_customer(r) for r in rows]

    def create(self, customer_data: Dict[str, Any]) -> Customer:
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(customer_data.get("tags", []))
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO customers (
                woocommerce_id, email, first_name, last_name, phone,
                total_spent, order_count, lifecycle_stage, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_data.get("woocommerce_id"),
                customer_data["email"],
                customer_data.get("first_name", "Valued"),
                customer_data.get("last_name", "Customer"),
                customer_data.get("phone", ""),
                customer_data.get("total_spent", 0.0),
                customer_data.get("order_count", 0),
                customer_data.get("lifecycle_stage", "Lead"),
                tags_json,
                now,
                now
            ))
            conn.commit()
            customer_id = cursor.lastrowid
            return self.get_by_id(customer_id)

    def update(self, customer: Customer) -> Customer:
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(customer.tags)
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE customers SET
                first_name = ?,
                last_name = ?,
                phone = ?,
                total_spent = ?,
                order_count = ?,
                lifecycle_stage = ?,
                tags = ?,
                updated_at = ?
            WHERE id = ?
            """, (
                customer.first_name,
                customer.last_name,
                customer.phone,
                customer.total_spent,
                customer.order_count,
                customer.lifecycle_stage,
                tags_json,
                now,
                customer.id
            ))
            conn.commit()
            return self.get_by_id(customer.id)

    def _row_to_customer(self, row) -> Customer:
        tags = []
        try:
            tags = json.loads(row["tags"]) if row["tags"] else []
        except Exception:
            tags = []
        return Customer(
            id=row["id"],
            woocommerce_id=row["woocommerce_id"],
            email=row["email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            total_spent=row["total_spent"],
            order_count=row["order_count"],
            lifecycle_stage=row["lifecycle_stage"],
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


class OrderRepository:
    """Handles CRUD operations for Order entities."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def get_by_woocommerce_id(self, woo_order_id: int) -> Optional[Order]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE woocommerce_order_id = ?", (woo_order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_order(row)

    def list_by_customer_id(self, customer_id: int) -> List[Order]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC", (customer_id,))
            rows = cursor.fetchall()
            return [self._row_to_order(r) for r in rows]

    def list_all(self, limit: int = 100) -> List[Order]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders ORDER BY order_date DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_order(r) for r in rows]

    def create(self, order_data: Dict[str, Any]) -> Order:
        items_json = json.dumps([item.dict() if hasattr(item, "dict") else item for item in order_data.get("items", [])])
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO orders (
                woocommerce_order_id, customer_id, customer_email, total_amount,
                currency, status, items, customer_notes, order_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_data["woocommerce_order_id"],
                order_data["customer_id"],
                order_data["customer_email"],
                order_data["total_amount"],
                order_data.get("currency", "INR"),
                order_data.get("status", "completed"),
                items_json,
                order_data.get("customer_notes", ""),
                order_data.get("order_date", datetime.utcnow().isoformat())
            ))
            conn.commit()
            order_id = cursor.lastrowid
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            return self._row_to_order(cursor.fetchone())

    def _row_to_order(self, row) -> Order:
        items_raw = []
        try:
            items_raw = json.loads(row["items"]) if row["items"] else []
        except Exception:
            items_raw = []
        items = [OrderItem(**item) if isinstance(item, dict) else item for item in items_raw]
        return Order(
            id=row["id"],
            woocommerce_order_id=row["woocommerce_order_id"],
            customer_id=row["customer_id"],
            customer_email=row["customer_email"],
            total_amount=row["total_amount"],
            currency=row["currency"],
            status=row["status"],
            items=items,
            customer_notes=row["customer_notes"],
            order_date=row["order_date"]
        )


class CommunicationRepository:
    """Handles CRUD operations for Communication Log entities."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def list_all(self, limit: int = 100) -> List[CommunicationLog]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM communications ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_comm(r) for r in rows]

    def list_by_customer_id(self, customer_id: int) -> List[CommunicationLog]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM communications WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
            rows = cursor.fetchall()
            return [self._row_to_comm(r) for r in rows]

    def create(self, comm_data: Dict[str, Any]) -> CommunicationLog:
        now = datetime.utcnow().isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO communications (
                customer_id, customer_email, trigger_event, subject, body,
                status, sentiment, agent_reasoning, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comm_data["customer_id"],
                comm_data["customer_email"],
                comm_data["trigger_event"],
                comm_data["subject"],
                comm_data["body"],
                comm_data.get("status", "draft"),
                comm_data.get("sentiment", "neutral"),
                comm_data["agent_reasoning"],
                now
            ))
            conn.commit()
            comm_id = cursor.lastrowid
            cursor.execute("SELECT * FROM communications WHERE id = ?", (comm_id,))
            return self._row_to_comm(cursor.fetchone())

    def update_status(self, comm_id: int, status: str) -> Optional[CommunicationLog]:
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE communications SET status = ? WHERE id = ?", (status, comm_id))
            conn.commit()
            cursor.execute("SELECT * FROM communications WHERE id = ?", (comm_id,))
            row = cursor.fetchone()
            return self._row_to_comm(row) if row else None

    def _row_to_comm(self, row) -> CommunicationLog:
        return CommunicationLog(
            id=row["id"],
            customer_id=row["customer_id"],
            customer_email=row["customer_email"],
            trigger_event=row["trigger_event"],
            subject=row["subject"],
            body=row["body"],
            status=row["status"],
            sentiment=row["sentiment"],
            agent_reasoning=row["agent_reasoning"],
            created_at=row["created_at"]
        )
