import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from app.api.schemas.payment import CheckoutRequest, PricingUpdate
from app.core.config import settings
from app.core.exceptions import AppError
from app.domain.user import User
from app.main import app
from app.providers.payments import (
    PaymentProvider,
    PaymentProviderError,
    ProviderEvent,
    WompiPaymentProvider,
    get_payment_provider,
)
from app.services import payment_service
from tests.helpers import BASE, auth, transport


async def register_user(client: AsyncClient, email: str) -> str:
    digits = "".join(str(ord(ch) % 10) for ch in email if ch.isalnum())
    r = await client.post(
        "/api/v1/auth/register",
        json={"phone_number": "+57" + digits[:12], "password": "secure123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


class FakePaymentProvider(PaymentProvider):
    key = "fake"

    def __init__(self, signature: str = "valid-sig") -> None:
        self.signature = signature
        self.session_id = "cs_test_123"
        self.event_id = "evt_test_1"
        self._amount_cents = 0

    async def create_checkout(self, **kwargs) -> object:
        from app.providers.payments import CheckoutResult

        self._amount_cents = int(kwargs["amount_cents"])
        return CheckoutResult(session_id=self.session_id, checkout_url="https://pay.test/checkout")

    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        if signature != self.signature:
            raise PaymentProviderError()
        data = json.loads(payload.decode("utf-8"))
        obj = data.get("data", {}).get("object", {})
        return ProviderEvent(
            event_id=data.get("id", self.event_id),
            event_type="checkout.session.completed",
            checkout_session_id=obj.get("id", self.session_id),
            paid=obj.get("payment_status") == "paid",
            amount_cents=int(obj.get("amount_total", self.amount_cents) or 0),
            currency=obj.get("currency", "cop"),
            raw=data,
        )

    async def verify_transaction(self, transaction_id: str) -> ProviderEvent:
        return ProviderEvent(
            event_id=f"wompi_tx:{transaction_id}",
            event_type="checkout.session.completed",
            checkout_session_id=self.session_id,
            paid=True,
            amount_cents=self.amount_cents,
            currency="cop",
            raw={"id": transaction_id},
        )

    @property
    def amount_cents(self) -> int:
        return self._amount_cents


def _use_fake(signature: str = "valid-sig") -> FakePaymentProvider:
    fake = FakePaymentProvider(signature)
    app.dependency_overrides[get_payment_provider] = lambda: fake
    return fake


async def _checkout(client: AsyncClient, token: str, credits: int = 100) -> dict:
    r = await client.post(
        "/api/v1/users/me/payments/checkout",
        headers=auth(token),
        json={"credits": credits},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _webhook(
    client: AsyncClient, provider: FakePaymentProvider, *, event_id: str | None = None
):
    payload = (
        f'{{"id": "{event_id or provider.event_id}", "type": "checkout.session.completed", '
        f'"data": {{"object": {{"id": "{provider.session_id}", "payment_status": "paid", '
        f'"amount_total": {provider.amount_cents}, "currency": "cop"}}}}}}'
    ).encode()
    return await client.post(
        "/api/v1/payments/webhook",
        content=payload,
        headers={"Content-Type": "application/json", "stripe-signature": provider.signature},
    )


async def test_checkout_requires_auth():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.post("/api/v1/users/me/payments/checkout", json={"credits": 100})
        assert r.status_code == 401
        assert (await c.get("/api/v1/users/me/payments")).status_code == 401
        assert (await c.get("/api/v1/payments/pricing")).status_code == 401


async def test_pricing_returns_server_values():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "price@test.com")
        r = await c.get("/api/v1/payments/pricing", headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["cents_per_credit"] == settings.cents_per_credit
    assert body["currency"] == settings.payment_currency.lower()
    assert body["credit_amounts"] == [100, 500, 1000]


async def test_webhook_invalid_signature_400():
    _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay0@test.com")
        await _checkout(c, token)
        r = await c.post(
            "/api/v1/payments/webhook",
            content=b"{}",
            headers={"stripe-signature": "wrong"},
        )
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_signature"


async def test_checkout_creates_pending_payment():
    _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay1@test.com")
        out = await _checkout(c, token, credits=100)
        payments = (await c.get("/api/v1/users/me/payments", headers=auth(token))).json()
    assert out["checkout_url"] == "https://pay.test/checkout"
    assert out["payment"]["status"] == "PENDING"
    assert out["payment"]["credits"] == 100
    assert out["payment"]["amount_cents"] == 1000  # 100 créditos * 10 cents
    assert payments[0]["status"] == "PENDING"


async def test_checkout_rejects_bad_amount():
    _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay2@test.com")
        for bad in (0, 4, 20000):
            r = await c.post(
                "/api/v1/users/me/payments/checkout",
                headers=auth(token),
                json={"credits": bad},
            )
            assert r.status_code == 422, (bad, r.text)


async def test_webhook_completed_grants_credits_once():
    provider = _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay3@test.com")
        await _checkout(c, token, credits=100)
        first = await _webhook(c, provider)
        payments = (await c.get("/api/v1/users/me/payments", headers=auth(token))).json()
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
        # reintento idempotente con el mismo provider_event_id
        dup = await _webhook(c, provider)

    assert first.status_code == 200, first.text
    assert dup.status_code == 200, dup.text
    assert dup.json()["duplicate"] is True
    assert payments[0]["status"] == "CREDITS_GRANTED"
    assert wallet["credits"] == 100
    payment_tx = next(t for t in wallet["transactions"] if t["kind"] == "payment")
    assert payment_tx["amount"] == 100


async def test_duplicate_event_does_not_double_credit():
    provider = _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay4@test.com")
        await _checkout(c, token, credits=100)
        await _webhook(c, provider)
        await _webhook(c, provider)
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert wallet["credits"] == 100


async def test_new_event_for_same_session_no_double_credit():
    provider = _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay5@test.com")
        await _checkout(c, token, credits=100)
        await _webhook(c, provider, event_id="evt_test_1")
        # el proveedor reenvía un evento NUEVO (otro id) para la misma sesión
        await _webhook(c, provider, event_id="evt_test_2")
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
        payments = (await c.get("/api/v1/users/me/payments", headers=auth(token))).json()
    assert wallet["credits"] == 100
    assert payments[0]["status"] == "CREDITS_GRANTED"


async def test_webhook_unknown_session_safe():
    _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay6@test.com")
        r = await c.post(
            "/api/v1/payments/webhook",
            content=(
                b'{"id": "evt_x", "type": "checkout.session.completed", '
                b'"data": {"object": {"id": "cs_ghost", "payment_status": "paid",'
                b' "amount_total": 100, "currency": "cop"}}}'
            ),
            headers={"stripe-signature": "valid-sig"},
        )
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert r.status_code == 200
    assert wallet["credits"] == 0


async def test_checkout_rejects_client_selected_jukebox_price():
    _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay7@test.com")
        r = await c.post(
            "/api/v1/users/me/payments/checkout",
            headers=auth(token),
            json={"credits": 100, "jukebox_id": 1},
        )
    assert r.status_code == 422


async def test_webhook_unpaid_event_does_not_grant_credits():
    provider = _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay8@test.com")
        await _checkout(c, token, credits=100)
        payload = (
            f'{{"id": "evt_unpaid", "type": "checkout.session.completed", '
            f'"data": {{"object": {{"id": "{provider.session_id}", "payment_status": "unpaid", '
            f'"amount_total": {provider.amount_cents}, "currency": "cop"}}}}}}'
        ).encode()
        r = await c.post(
            "/api/v1/payments/webhook",
            content=payload,
            headers={"Content-Type": "application/json", "stripe-signature": provider.signature},
        )
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert r.status_code == 200
    assert r.json()["ignored"] == "payment_not_confirmed"
    assert wallet["credits"] == 0


async def test_webhook_amount_mismatch_does_not_grant_credits():
    provider = _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay9@test.com")
        await _checkout(c, token, credits=100)
        provider._amount_cents += 1
        r = await _webhook(c, provider)
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert r.status_code == 200
    assert r.json()["ignored"] == "payment_not_confirmed"
    assert wallet["credits"] == 0


async def test_wompi_rejects_webhooks_without_events_secret():
    provider = WompiPaymentProvider("pub", "priv", "", "https://checkout.wompi.co/l/x")
    with pytest.raises(PaymentProviderError):
        await provider.verify_event(b'{"id":"evt_1"}', "anything")


async def test_wompi_rejects_unsigned_event():
    provider = WompiPaymentProvider("pub", "priv", "secret", "https://checkout.wompi.co/l/x")
    payload = (
        b'{"id":"evt_1","event":"transaction.updated","timestamp":123,'
        b'"data":{"transaction":{"reference":"wompi_1","status":"APPROVED",'
        b'"amount_in_cents":1000,"currency":"cop"}}}'
    )
    with pytest.raises(PaymentProviderError):
        await provider.verify_event(payload, "")


async def test_wompi_accepts_signed_event():
    provider = WompiPaymentProvider("pub", "priv", "secret", "https://checkout.wompi.co/l/x")
    checksum = hashlib.sha256(b"wompi_1123secret").hexdigest()
    data = {
        "id": "evt_1",
        "event": "transaction.updated",
        "timestamp": 123,
        "data": {
            "transaction": {
                "reference": "wompi_1",
                "status": "APPROVED",
                "amount_in_cents": 1000,
                "currency": "cop",
            }
        },
        "signature": {"properties": ["data.transaction.reference"], "checksum": checksum},
    }
    event = await provider.verify_event(json.dumps(data).encode(), "")
    assert event.checkout_session_id == "wompi_1"
    assert event.paid is True


def test_production_config_rejects_weak_secrets(monkeypatch):
    monkeypatch.setenv("CHOMELO_ENVIRONMENT", "production")
    monkeypatch.setenv("CHOMELO_JWT_SECRET", "short")
    with pytest.raises(ValueError):
        settings.__class__(_env_file=None)
    monkeypatch.setenv("CHOMELO_JWT_SECRET", "x" * 32)
    config = settings.__class__(_env_file=None)
    assert config.jwt_secret == "x" * 32


async def test_wompi_web_checkout_sends_amount_and_integrity():
    provider = WompiPaymentProvider(
        "pub_test_x", "", "", "https://checkout.wompi.co/l/fallback", "integrity_secret"
    )
    result = await provider.create_checkout(
        amount_cents=9500000,
        currency="cop",
        credits=100,
        metadata={},
        success_url="https://jukebox.chomelo.org/wallet?status=success",
        cancel_url="https://jukebox.chomelo.org/wallet?status=cancelled",
    )
    params = parse_qs(urlparse(result.checkout_url).query)
    assert params["amount-in-cents"] == ["9500000"]
    assert params["currency"] == ["COP"]
    assert params["reference"] == [result.session_id]
    expected = hashlib.sha256(
        f"{result.session_id}9500000COPintegrity_secret".encode()
    ).hexdigest()
    assert params["signature:integrity"] == [expected]


@pytest.mark.asyncio
async def test_admin_pricing_changes_checkout_amount(db_session):
    user = User(phone_number="+573001234999", password_hash="hash")
    db_session.add(user)
    await db_session.commit()
    pricing = await payment_service.update_pricing(
        db_session,
        user.id,
        PricingUpdate(cents_per_credit=250, currency="cop", credit_amounts=[100, 250]),
    )
    assert pricing.cents_per_credit == 250
    assert pricing.credit_amounts == [100, 250]

    provider = FakePaymentProvider()
    checkout = await payment_service.create_checkout(
        db_session, user, provider, CheckoutRequest(credits=250)
    )
    assert checkout.payment.amount_cents == 62500
    assert checkout.payment.currency == "cop"

    with pytest.raises(AppError) as exc:
        await payment_service.create_checkout(
            db_session, user, provider, CheckoutRequest(credits=500)
        )
    assert exc.value.code == "invalid_amount"


async def test_confirm_payment_from_redirect_is_idempotent():
    _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "confirm@test.com")
        await _checkout(c, token, credits=100)
        first = await c.post(
            "/api/v1/users/me/payments/confirm",
            headers=auth(token),
            json={"transaction_id": "01-1531231271-19365"},
        )
        second = await c.post(
            "/api/v1/users/me/payments/confirm",
            headers=auth(token),
            json={"transaction_id": "01-1531231271-19365"},
        )
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert first.status_code == 200
    assert first.json()["status"] == "CREDITS_GRANTED"
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert wallet["credits"] == 100
