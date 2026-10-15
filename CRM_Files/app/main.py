"""
FastAPI Application Entrypoint for Kilowott CRM.
Provides RESTful APIs, WooCommerce Webhook Receivers, and Interactive Simulator Endpoints.
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.database import init_db, DEFAULT_DB_PATH
from app.repositories import CustomerRepository, OrderRepository, CommunicationRepository
from app.agent import AgenticCustomerEngine
from app.services import CRMService
from app.models import WooCommerceWebhookOrder

# Ensure database tables exist
init_db(DEFAULT_DB_PATH)

app = FastAPI(
    title="Kilowott CRM - WooCommerce Integration",
    description="Agentic CRM integrating WooCommerce Customer Data, Order Tracking, and Autonomous Communication Workflows.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
customer_repo = CustomerRepository(DEFAULT_DB_PATH)
order_repo = OrderRepository(DEFAULT_DB_PATH)
comm_repo = CommunicationRepository(DEFAULT_DB_PATH)
agent_engine = AgenticCustomerEngine()
crm_service = CRMService(customer_repo, order_repo, comm_repo, agent_engine)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Kilowott CRM API is running. Access /docs for interactive Swagger UI."}


@app.get("/api/health")
def healthcheck():
    return {"status": "healthy", "service": "kilowott-crm", "version": "1.0.0"}


@app.get("/api/metrics")
def get_metrics():
    return crm_service.get_dashboard_metrics()


@app.get("/api/customers")
def list_customers():
    return customer_repo.list_all()


@app.get("/api/customers/{customer_id}")
def get_customer_detail(customer_id: int):
    customer = customer_repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    orders = order_repo.list_by_customer_id(customer_id)
    comms = comm_repo.list_by_customer_id(customer_id)
    return {
        "customer": customer,
        "orders": orders,
        "communications": comms
    }


@app.get("/api/orders")
def list_orders():
    return order_repo.list_all()


@app.get("/api/communications")
def list_communications():
    return comm_repo.list_all()


@app.post("/api/communications/{comm_id}/send")
def send_communication(comm_id: int):
    updated = comm_repo.update_status(comm_id, "sent")
    if not updated:
        raise HTTPException(status_code=404, detail="Communication not found")
    return {"status": "success", "message": f"Communication #{comm_id} sent successfully", "communication": updated}


@app.post("/api/webhooks/woocommerce/order")
async def receive_woocommerce_order(request: Request):
    """
    Standard WooCommerce order webhook listener.
    Accepts raw JSON payload from WooCommerce hook `action: woocommerce_order_status_changed`
    or `woocommerce_new_order`.
    """
    try:
        payload = await request.json()
        result = crm_service.process_woocommerce_order_webhook(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class SimulatorOrderRequest(BaseModel):
    scenario: str = "first_time"  # first_time, repeat_purchase, vip_purchase, cancelled_dissatisfied, negative_feedback
    customer_name: Optional[str] = "Priya Sharma"
    customer_email: Optional[str] = "priya.sharma@example.com"
    order_amount: Optional[float] = None
    product_name: Optional[str] = None
    notes: Optional[str] = None


@app.post("/api/simulator/trigger-order")
def simulate_order(sim: SimulatorOrderRequest):
    """
    Hackathon Demo Simulator: Emulates real WooCommerce webhook triggers with rich scenarios
    to easily demonstrate the Agentic AI in action.
    """
    import random
    order_id = random.randint(10000, 99999)

    first_name = sim.customer_name.split()[0] if sim.customer_name else "Valued"
    last_name = sim.customer_name.split()[-1] if len(sim.customer_name.split()) > 1 else "Customer"

    scenarios = {
        "first_time": {
            "status": "completed",
            "total": str(sim.order_amount or 2499.00),
            "product": sim.product_name or "Wireless Ergonomic Keyboard",
            "notes": sim.notes or "Please pack securely.",
            "currency": "INR"
        },
        "vip_purchase": {
            "status": "completed",
            "total": str(sim.order_amount or 18500.00),
            "product": sim.product_name or "Premium 4K Smart Monitor",
            "notes": sim.notes or "Delighted with my previous orders!",
            "currency": "INR"
        },
        "repeat_purchase": {
            "status": "completed",
            "total": str(sim.order_amount or 4200.00),
            "product": sim.product_name or "Noise Cancelling Headphones",
            "notes": sim.notes or "Loved the fast delivery last time.",
            "currency": "INR"
        },
        "negative_feedback": {
            "status": "completed",
            "total": str(sim.order_amount or 3100.00),
            "product": sim.product_name or "Mechanical Gaming Mouse",
            "notes": sim.notes or "Urgent delivery needed, last time the package was delayed and damaged!",
            "currency": "INR"
        },
        "cancelled_dissatisfied": {
            "status": "cancelled",
            "total": str(sim.order_amount or 5500.00),
            "product": sim.product_name or "Smart Fitness Tracker",
            "notes": sim.notes or "Cancelling due to unexpected delay.",
            "currency": "INR"
        }
    }

    selected = scenarios.get(sim.scenario, scenarios["first_time"])

    payload = {
        "id": order_id,
        "status": selected["status"],
        "currency": selected["currency"],
        "total": selected["total"],
        "billing": {
            "first_name": first_name,
            "last_name": last_name,
            "email": sim.customer_email,
            "phone": "+91 98765 43210"
        },
        "line_items": [
            {
                "product_id": random.randint(101, 999),
                "name": selected["product"],
                "quantity": 1,
                "total": selected["total"],
                "price": selected["total"]
            }
        ],
        "customer_note": selected["notes"]
    }

    result = crm_service.process_woocommerce_order_webhook(payload)
    return result


@app.post("/api/simulator/seed-demo")
def seed_demo_data():
    """Seeds realistic demo customers, orders, and AI workflows."""
    demo_scenarios = [
        SimulatorOrderRequest(scenario="first_time", customer_name="Rohan Verma", customer_email="rohan.verma@example.com", order_amount=1999.0, product_name="Studio Mic Pro"),
        SimulatorOrderRequest(scenario="repeat_purchase", customer_name="Aarti Patel", customer_email="aarti.patel@example.com", order_amount=4500.0, product_name="Ultra HD Webcam"),
        SimulatorOrderRequest(scenario="vip_purchase", customer_name="Vikram Mehta", customer_email="vikram.mehta@example.com", order_amount=22000.0, product_name="Enterprise Server Rack"),
        SimulatorOrderRequest(scenario="negative_feedback", customer_name="Ananya Sen", customer_email="ananya.sen@example.com", order_amount=3200.0, product_name="Wireless Earbuds"),
        SimulatorOrderRequest(scenario="cancelled_dissatisfied", customer_name="Devendra Naik", customer_email="devendra.naik@example.com", order_amount=6200.0, product_name="Smart Home Hub")
    ]
    results = []
    for s in demo_scenarios:
        res = simulate_order(s)
        results.append(res["message"])
    return {"status": "success", "message": f"Seeded {len(results)} demo scenarios successfully"}
