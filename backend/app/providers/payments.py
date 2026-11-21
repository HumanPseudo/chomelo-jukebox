import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from uuid import uuid4

from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError

COMPLETED_CHECKOUT_EVENT = "checkout.session.completed"


class CheckoutResult(BaseModel):
    session_id: str
    checkout_url: str


class ProviderEvent(BaseModel):
    """Evento normalizado del proveedor de pagos (independiente del vendor)."""

    event_id: str
    event_type: str
    checkout_session_id: str | None = None
    paid: bool = False
    amount_cents: int = 0
    currency: str = "eur"
    raw: dict

    @property
    def is_completed_checkout(self) -> bool:
        return self.event_type == COMPLETED_CHECKOUT_EVENT and self.checkout_session_id is not None


class PaymentProviderError(AppError):
    """La firma del webhook no es válida o el proveedor rechazó la operación."""

    def __init__(self, message: str = "firma de pago inválida") -> None:
        super().__init__(message, code="invalid_signature", status_code=400)


class PaymentProvider(ABC):
    key: str = "generic"

    @abstractmethod
    async def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        credits: int,
        metadata: dict,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResult: ...

    @abstractmethod
    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        """Verifica la firma y devuelve el evento normalizado.

        Lanza PaymentProviderError si la firma no es válida.
        """
        ...


class StripePaymentProvider(PaymentProvider):
    key = "stripe"

    def __init__(self, secret_key: str, webhook_secret: str) -> None:
        self._stripe = __import__("stripe")
        self._stripe.api_key = secret_key
        self._webhook_secret = webhook_secret

    async def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        credits: int,
        metadata: dict,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResult:
        try:
            session = self._stripe.checkout.Session.create(
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "unit_amount": amount_cents,
                            "product_data": {"name": f"{credits} créditos de Chomelo"},
                        },
                        "quantity": 1,
                    }
                ],
                metadata=metadata,
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except Exception as exc:
            raise PaymentProviderError("el proveedor de pagos no está disponible") from exc
        return CheckoutResult(session_id=session.id, checkout_url=session.url)

    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        try:
            event = self._stripe.Webhook.construct_event(payload, signature, self._webhook_secret)
        except Exception as exc:
            raise PaymentProviderError() from exc
        return _normalize_event(event.to_dict_recursive())


class MockPaymentProvider(PaymentProvider):
    """Proveedor ficticio SOLO para desarrollo/verificación sin credenciales.

    No debe usarse en producción: ignora la autenticidad del emisor.
    """

    key = "mock"

    def __init__(self, webhook_secret: str = "test-signature") -> None:
        self._webhook_secret = webhook_secret

    async def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        credits: int,
        metadata: dict,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResult:
        token = uuid4().hex[:12]
        return CheckoutResult(
            session_id=f"cs_mock_{token}", checkout_url=f"https://pay.local/checkout/{token}"
        )

    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        if signature != self._webhook_secret:
            raise PaymentProviderError()
        data = _json_loads(payload)
        return _normalize_event(data)


def _json_loads(payload: bytes) -> dict:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise PaymentProviderError() from exc
    if not isinstance(data, dict):
        raise PaymentProviderError()
    return data


def _normalize_event(data: dict) -> ProviderEvent:
    """Normaliza un evento (Stripe o simulado) a ProviderEvent."""
    obj = data.get("data", {}).get("object", {}) if isinstance(data.get("data"), dict) else {}
    return ProviderEvent(
        event_id=str(data.get("id", "")),
        event_type=str(data.get("type", "")),
        checkout_session_id=str(obj.get("id")) if obj.get("id") else None,
        paid=(obj.get("payment_status") == "paid"),
        amount_cents=int(obj.get("amount_total", 0) or 0),
        currency=str(obj.get("currency", "eur") or "eur"),
        raw=data,
    )



class WompiPaymentProvider(PaymentProvider):
    key = "wompi"

    def __init__(
        self,
        public_key: str,
        private_key: str,
        events_secret: str,
        payment_link: str = "",
    ) -> None:
        self._public_key = public_key
        self._private_key = private_key
        self._events_secret = events_secret
        self._payment_link = payment_link or "https://checkout.wompi.co/l/VPOS_yJJIDR"

    async def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        credits: int,
        metadata: dict,
        success_url: str,
        cancel_url: str,
    ) -> CheckoutResult:
        session_id = f"wompi_{uuid4().hex}"
        if self._public_key:
            params = {
                "public-key": self._public_key,
                "currency": currency.upper(),
                "amount-in-cents": str(amount_cents),
                "reference": session_id,
                "redirect-url": success_url,
            }
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            checkout_url = f"https://checkout.wompi.co/p/?{qs}"
        else:
            checkout_url = self._payment_link
        return CheckoutResult(session_id=session_id, checkout_url=checkout_url)

    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        if not self._events_secret:
            raise PaymentProviderError("Wompi requiere events_secret para webhooks")
        data = _json_loads(payload)
        sig = data.get("signature", {}) if isinstance(data.get("signature"), dict) else {}
        props = sig.get("properties", [])
        timestamp = data.get("timestamp")
        values = []
        for prop in props:
            cur = data
            for part in str(prop).split("."):
                if isinstance(cur, dict):
                    cur = cur.get(part)
                else:
                    cur = None
            values.append("" if cur is None else str(cur))
        concat = "".join(values) + str(timestamp) + self._events_secret
        expected = hashlib.sha256(concat.encode("utf-8")).hexdigest()
        checksum = sig.get("checksum") or signature
        if not checksum or not hmac.compare_digest(str(checksum), expected):
            raise PaymentProviderError()
        payload_data = data.get("data", {})
        tx = payload_data.get("transaction", {}) if isinstance(payload_data, dict) else {}
        status = str(tx.get("status", "")).upper()
        event_type = (
            COMPLETED_CHECKOUT_EVENT if status == "APPROVED" else str(data.get("event", ""))
        )
        session_id = tx.get("reference") or tx.get("id")
        return ProviderEvent(
            event_id=str(data.get("id", data.get("event", ""))),
            event_type=event_type,
            checkout_session_id=str(session_id) if session_id else None,
            paid=(status == "APPROVED"),
            amount_cents=int(tx.get("amount_in_cents", 0) or 0),
            currency=str(tx.get("currency", "cop") or "cop"),
            raw=data,
        )


def get_payment_provider() -> PaymentProvider:
    if settings.payment_provider == "stripe":
        if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
            raise PaymentProviderError("Stripe no está configurado")
        return StripePaymentProvider(settings.stripe_secret_key, settings.stripe_webhook_secret)
    if settings.payment_provider == "wompi":
        if not settings.wompi_payment_link:
            raise PaymentProviderError("Wompi no está configurado")
        return WompiPaymentProvider(
            settings.wompi_public_key,
            settings.wompi_private_key,
            settings.wompi_events_secret,
            settings.wompi_payment_link,
        )
    return MockPaymentProvider()
