from httpx import AsyncClient

from app.main import app
from app.providers.payments import (
    PaymentProvider,
    PaymentProviderError,
    ProviderEvent,
    get_payment_provider,
)
from tests.helpers import BASE, auth, register_user, transport


class FakePaymentProvider(PaymentProvider):
    key = "fake"

    def __init__(self, signature: str = "valid-sig") -> None:
        self.signature = signature
        self.session_id = "cs_test_123"
        self.event_id = "evt_test_1"

    async def create_checkout(self, **kwargs) -> object:
        from app.providers.payments import CheckoutResult

        return CheckoutResult(session_id=self.session_id, checkout_url="https://pay.test/checkout")

    async def verify_event(self, payload: bytes, signature: str) -> ProviderEvent:
        if signature != self.signature:
            raise PaymentProviderError()
        return ProviderEvent(
            event_id=self.event_id,
            event_type="checkout.session.completed",
            checkout_session_id=self.session_id,
            paid=True,
            amount_cents=self.amount_cents,
            currency="eur",
            raw={},
        )

    @property
    def amount_cents(self) -> int:
        return 0


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
        f'"amount_total": {provider.amount_cents}, "currency": "eur"}}}}}}'
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
        await _checkout(c, token, credits=50)
        await _webhook(c, provider)
        await _webhook(c, provider)
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert wallet["credits"] == 50


async def test_new_event_for_same_session_no_double_credit():
    provider = _use_fake()
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        token = await register_user(c, "pay5@test.com")
        await _checkout(c, token, credits=30)
        await _webhook(c, provider, event_id="evt_test_1")
        # el proveedor reenvía un evento NUEVO (otro id) para la misma sesión
        await _webhook(c, provider, event_id="evt_test_2")
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
        payments = (await c.get("/api/v1/users/me/payments", headers=auth(token))).json()
    assert wallet["credits"] == 30
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
                b' "amount_total": 100, "currency": "eur"}}}'
            ),
            headers={"stripe-signature": "valid-sig"},
        )
        wallet = (await c.get("/api/v1/users/me/wallet", headers=auth(token))).json()
    assert r.status_code == 200
    assert wallet["credits"] == 0
