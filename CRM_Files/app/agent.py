"""
Autonomous Agentic AI Engine for Customer Intelligence & Workflow Orchestration.
Evaluates customer profiles, detects intent and sentiment, performs RFM segmentation,
and autonomously initiates personalized communication workflows with transparent reasoning.
"""

from typing import Dict, Any, List, Tuple
from app.models import Customer, Order, CommunicationLog


class AgenticCustomerEngine:
    """
    Autonomous Agent that continuously monitors customer actions,
    infers sentiment and lifecycle trajectory, and executes communication decisions.
    """

    def analyze_and_act(
        self,
        customer: Customer,
        recent_order: Order,
        all_orders: List[Order]
    ) -> Tuple[Customer, CommunicationLog]:
        """
        Executes the agent's perception-reasoning-action loop:
        1. Perception: Ingests profile, current order, and historical velocity.
        2. Reasoning: Calculates customer lifecycle stage, churn risk, and sentiment.
        3. Decision: Chooses the optimal engagement strategy.
        4. Action: Formulates targeted communication with rationale and updates tags.
        """
        # Step 1: Analyze Sentiment & Notes
        sentiment = self._extract_sentiment(recent_order.customer_notes)
        
        # Step 2: Compute RFM & Lifecycle Stage
        new_lifecycle, updated_tags = self._evaluate_lifecycle(customer, recent_order, all_orders)
        customer.lifecycle_stage = new_lifecycle
        customer.tags = updated_tags

        # Step 3: Autonomous Workflow Formulation
        subject, body, reasoning = self._synthesize_communication(
            customer=customer,
            order=recent_order,
            sentiment=sentiment,
            lifecycle=new_lifecycle
        )

        comm_draft_data = {
            "customer_id": customer.id,
            "customer_email": customer.email,
            "trigger_event": f"woocommerce_order_{recent_order.status}",
            "subject": subject,
            "body": body,
            "status": "draft",  # Can be auto-sent or queued for human-in-the-loop review
            "sentiment": sentiment,
            "agent_reasoning": reasoning
        }

        return customer, comm_draft_data

    def _extract_sentiment(self, notes: str) -> str:
        """Heuristic and NLP-inspired sentiment scoring on order notes/feedback."""
        if not notes:
            return "neutral"
        notes_lower = notes.lower()
        negative_signals = ["delay", "urgent", "wrong", "damaged", "poor", "hate", "cancel", "disappointed", "refund", "issue", "bad"]
        positive_signals = ["love", "excited", "great", "awesome", "fast", "thank", "best", "perfect", "favorite"]

        neg_count = sum(1 for word in negative_signals if word in notes_lower)
        pos_count = sum(1 for word in positive_signals if word in notes_lower)

        if neg_count > pos_count:
            return "negative / support needed"
        elif pos_count > neg_count:
            return "delighted / positive"
        return "neutral"

    def _evaluate_lifecycle(
        self,
        customer: Customer,
        recent_order: Order,
        all_orders: List[Order]
    ) -> Tuple[str, List[str]]:
        """Applies RFM heuristic clustering to dynamically classify the customer."""
        tags = set(customer.tags)
        total_spent = customer.total_spent
        order_count = customer.order_count

        # Order status checks
        if recent_order.status in ["cancelled", "refunded"]:
            tags.add("Needs Retention Attention")
            return "At Risk", list(tags)

        # High Value Tier (Monetary check)
        if total_spent >= 15000 or (order_count >= 3 and total_spent >= 10000):
            tags.add("VIP Tier")
            tags.discard("First-Time Buyer")
            tags.add("High LTV")
            return "VIP Customer", list(tags)

        # Growth Tier (Frequency check)
        if order_count >= 2:
            tags.add("Repeat Buyer")
            tags.discard("First-Time Buyer")
            return "Promising / Loyal", list(tags)

        # First time buyer
        tags.add("First-Time Buyer")
        return "New Customer", list(tags)

    def _synthesize_communication(
        self,
        customer: Customer,
        order: Order,
        sentiment: str,
        lifecycle: str
    ) -> Tuple[str, str, str]:
        """
        Synthesizes human-grade, hyper-personalized messaging and supplies
        transparent reasoning logs for the review dashboard.
        """
        item_names = [item.name for item in order.items]
        primary_item = item_names[0] if item_names else "your item"
        first_name = customer.first_name if customer.first_name else "there"

        # Case 1: Refund or Cancellation -> Immediate empathetic intervention
        if order.status in ["cancelled", "refunded"]:
            reasoning = (
                f"Agent detected {order.status.upper()} status for Order #{order.woocommerce_order_id}. "
                f"Customer marked 'At Risk'. Formulating proactive retention outreach to safeguard customer relationship."
            )
            subject = f"We are genuinely sorry about your order, {first_name}"
            body = (
                f"Hi {first_name},\n\n"
                f"We noticed that order #{order.woocommerce_order_id} was recently {order.status}. "
                f"Your satisfaction is our absolute priority, and we deeply apologize for any inconvenience.\n\n"
                f"If there is anything our team can do to make things right—or if you would like us to arrange an alternative product—"
                f"please reply directly to this email. We are here to help.\n\n"
                f"Warm regards,\nKilowott Customer Care"
            )
            return subject, body, reasoning

        # Case 2: Negative sentiment detected in order notes
        if sentiment == "negative / support needed":
            reasoning = (
                f"Agent detected negative customer sentiment in order notes ('{order.customer_notes}'). "
                f"Escalated priority to Customer Experience triage."
            )
            subject = f"Priority Support for Order #{order.woocommerce_order_id}"
            body = (
                f"Hi {first_name},\n\n"
                f"Thank you for your order! We noted your remark: '{order.customer_notes}'. "
                f"Our fulfillment team has been personally briefed on your instructions to ensure seamless handling.\n\n"
                f"If you need any immediate assistance, our dedicated lead is on standby.\n\n"
                f"Best,\nKilowott Priority Team"
            )
            return subject, body, reasoning

        # Case 3: VIP Customer
        if lifecycle == "VIP Customer":
            reasoning = (
                f"Customer crossed VIP threshold with Total Spent of ₹{customer.total_spent:,.2f} across {customer.order_count} orders. "
                f"Agent autonomously granted VIP Tier perks and formulated executive appreciation note."
            )
            subject = f"Exclusive VIP Perks for you, {first_name} | Order #{order.woocommerce_order_id}"
            body = (
                f"Dear {first_name},\n\n"
                f"Thank you for choosing us once again! Your recent order for '{primary_item}' is currently being prepared.\n\n"
                f"Because you are one of our most valued VIP customers, we have unlocked complimentary priority shipping and "
                f"a private 20% privilege code (VIP-LOYALTY-20) for your next visit.\n\n"
                f"Thank you for being such an integral part of our community.\n\n"
                f"Warmly,\nExecutive Customer Success Team"
            )
            return subject, body, reasoning

        # Case 4: Repeat Customer (Promising)
        if lifecycle == "Promising / Loyal":
            reasoning = (
                f"Repeat order confirmed ({customer.order_count} total orders). "
                f"Agent initiating post-purchase loyalty reinforcement and cross-sell recommendation."
            )
            subject = f"Welcome back, {first_name}! Your order #{order.woocommerce_order_id} is confirmed"
            body = (
                f"Hi {first_name},\n\n"
                f"It is wonderful to have you back! We are preparing your '{primary_item}' right away.\n\n"
                f"Since you enjoy products in this category, we have curated a few companion items we think you will love on your dashboard.\n\n"
                f"Track your package anytime or reach out if you have any questions.\n\n"
                f"Cheers,\nKilowott Experience Team"
            )
            return subject, body, reasoning

        # Case 5: First-Time Buyer
        reasoning = (
            f"New customer onboarding triggered. Order value: ₹{order.total_amount:,.2f}. "
            f"Agent generating introductory welcome sequence and brand assurance message."
        )
        subject = f"Welcome to our store, {first_name}! Order #{order.woocommerce_order_id} Confirmed"
        body = (
            f"Hi {first_name},\n\n"
            f"Welcome to the family! We are thrilled to fulfill your first order for '{primary_item}'.\n\n"
            f"Our team is carefully packing your items and we will send a notification with tracking details as soon as it leaves our warehouse.\n\n"
            f"Have questions or need tips on getting the most out of your purchase? We are just a reply away!\n\n"
            f"Best wishes,\nKilowott Customer Team"
        )
        return subject, body, reasoning
