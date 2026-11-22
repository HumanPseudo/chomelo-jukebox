import hashlib
import hmac
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError

COMPLETED_CHECKOUT_EVENT = "checkout.session.completed"


def _wompi_base() -> str:
    if settings.wompi_sandbox or settings.environment != "production":
        return "https://sandbox.wompi.co"
    return "https://production.wompi.co"


def _tx_to_event(tx: dict, event_id: str, event_type: str):
    status = str(tx.get("status", "")).upper()
    session_id = tx.get("payment_link_id") or tx.get("reference") or tx.get("id")
    created_at = None
    raw_created = tx.get("created_at")
    if isinstance(raw_created, str):
        try:
            created_at = datetime.fromisoformat(raw_created.replace("Z", "+00:00"))
        except ValueError:
            created_at = None
    return ProviderEvent(
        event_id=event_id,
        event_type=event_type,
        checkout_session_id=str(session_id) if session_id else None,
        paid=status == "APPROVED",
        amount_cents=int(tx.get("amount_in_cents", 0) or 0),
        currency=str(tx.get("currency", "cop") or "cop").lower(),
        created_at=created_at,
        raw=tx,
    )


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
    created_at: datetime | None = None
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

    async def verify_transaction(self, transaction_id: str) -> ProviderEvent:
        raise PaymentProviderError("el proveedor no soporta verificación por id")


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
        integrity_secret: str = "",
    ) -> None:
        self._public_key = public_key
        self._private_key = private_key
        self._events_secret = events_secret
        self._integrity_secret = integrity_secret
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
        if self._private_key:
            base = _wompi_base()
            payload = {
                "name": f"{credits} créditos Chomelo",
                "description": f"Compra de {credits} créditos",
                "single_use": True,
                "collect_shipping": False,
                "amount_in_cents": amount_cents,
                "currency": currency.upper(),
                "reference": session_id,
                "redirect_url": success_url,
            }
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(
                        f"{base}/v1/payment_links",
                        json=payload,
                        headers={"Authorization": f"Bearer {self._private_key}"},
                    )
                response.raise_for_status()
                data = response.json().get("data", {})
            except (httpx.HTTPError, ValueError) as exc:
                raise PaymentProviderError("no se pudo crear el link de pago") from exc
            checkout_url = data.get("url") or (
                f"https://checkout.wompi.co/l/{data['id']}" if data.get("id") else ""
            )
            if not checkout_url:
                raise PaymentProviderError("Wompi no devolvió un link de pago")
            if data.get("id"):
                session_id = str(data["id"])
        elif self._public_key and self._integrity_secret:
            integrity = (
                session_id + str(amount_cents) + currency.upper() + self._integrity_secret
            )
            params = {
                "public-key": self._public_key,
                "currency": currency.upper(),
                "amount-in-cents": str(amount_cents),
                "reference": session_id,
                "signature:integrity": hashlib.sha256(integrity.encode("utf-8")).hexdigest(),
                "redirect-url": success_url,
            }
            checkout_url = f"https://checkout.wompi.co/p/?{urlencode(params)}"
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
        return _tx_to_event(
            tx,
            event_id=str(data.get("id", data.get("event", ""))),
            event_type=event_type,
        )

    async def verify_transaction(self, transaction_id: str) -> ProviderEvent:
        if not self._private_key:
            raise PaymentProviderError("Wompi requiere llave privada para verificar pagos")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", transaction_id):
            raise PaymentProviderError("id de transacción inválido")
        base = _wompi_base()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{base}/v1/transactions/{transaction_id}",
                    headers={"Authorization": f"Bearer {self._private_key}"},
                )
            response.raise_for_status()
            data = response.json().get("data", {})
        except (httpx.HTTPError, ValueError) as exc:
            raise PaymentProviderError("no se pudo verificar la transacción") from exc
        return _tx_to_event(
            data,
            event_id=f"wompi_tx:{data.get('id', transaction_id)}",
            event_type=COMPLETED_CHECKOUT_EVENT,
        )


def get_payment_provider() -> PaymentProvider:
    if settings.payment_provider == "stripe":
        if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
            raise PaymentProviderError("Stripe no está configurado")
        return StripePaymentProvider(settings.stripe_secret_key, settings.stripe_webhook_secret)
    if settings.payment_provider == "wompi":
        has_fixed_amount = bool(
            settings.wompi_private_key
            or (settings.wompi_public_key and settings.wompi_integrity_secret)
        )
        if not settings.wompi_payment_link and not has_fixed_amount:
            raise PaymentProviderError("Wompi no está configurado")
        return WompiPaymentProvider(
            settings.wompi_public_key,
            settings.wompi_private_key,
            settings.wompi_events_secret,
            settings.wompi_payment_link,
            settings.wompi_integrity_secret,
        )
    return MockPaymentProvider()
