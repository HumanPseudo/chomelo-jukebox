from fastapi import Request


def get_client_ip(request: Request, *, trust_proxy: bool = True) -> str:
    """Extrae la IP real del cliente, respetando el primer `X-Forwarded-For` si
    el tráfico viene de un balanceador/proxy (confiável por defecto en Docker)."""
    forwarded_for: str | None = None
    if trust_proxy:
        forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
