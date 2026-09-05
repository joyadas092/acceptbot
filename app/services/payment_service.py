from abc import ABC, abstractmethod
from typing import Dict, Any

from app.services.subscription_service import SubscriptionService
from app.core.logging import get_logger

class PaymentProvider(ABC):
    """Abstract interface for payment providers."""
    
    @abstractmethod
    async def create_invoice(
        self,
        user_id: int,
        plan_id: str,
        amount: float,
        currency: str = 'USD'
    ) -> Dict[str, Any]:
        """Create a payment invoice. Returns {invoice_id, payment_url, ...}"""
    
    @abstractmethod
    async def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """Verify payment status. Returns {status, user_id, plan_id, ...}"""
    
    @abstractmethod
    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming payment webhook."""


class StubPaymentProvider(PaymentProvider):
    """Stub implementation for development. Replace with real provider."""
    
    async def create_invoice(self, user_id, plan_id, amount, currency='USD'):
        return {'invoice_id': f'stub_{user_id}_{plan_id}', 'payment_url': '#', 'status': 'pending'}
    
    async def verify_payment(self, payment_id):
        return {'status': 'pending', 'payment_id': payment_id}
    
    async def handle_webhook(self, payload):
        return {'status': 'ok'}


class PaymentService:
    def __init__(
        self,
        provider: PaymentProvider,
        subscription_service: SubscriptionService
    ):
        self.provider = provider
        self.subscription_service = subscription_service
        self.logger = get_logger('payment_service')

    async def initiate_upgrade(
        self,
        user_id: int,
        plan_id: str
    ) -> Dict[str, Any]:
        """Start upgrade flow. Returns invoice URL."""
        # Typically amount would be fetched from PlanService
        invoice = await self.provider.create_invoice(user_id, plan_id, 9.99)
        self.logger.info(f"Initiated upgrade for user {user_id} to {plan_id}")
        return invoice

    async def handle_successful_payment(
        self,
        payment_id: str
    ) -> bool:
        """Called after verified payment. Activates subscription."""
        payment_data = await self.provider.verify_payment(payment_id)
        if payment_data.get("status") == "success":
            user_id = payment_data["user_id"]
            plan_id = payment_data["plan_id"]
            await self.subscription_service.assign_plan(user_id, plan_id, duration_days=30)
            self.logger.info(f"Activated subscription for user {user_id} plan {plan_id}")
            return True
        return False

    async def handle_payment_webhook(self, payload: Dict[str, Any]) -> None:
        """Entry point for payment provider webhook."""
        result = await self.provider.handle_webhook(payload)
        if result.get("status") == "paid":
            await self.handle_successful_payment(result["payment_id"])
