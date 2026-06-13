from fastapi import Request

from agent.config import Config
from shared.util.signature import verify_signature_headers


async def verify_signature(req: Request):
    """Verify signature of the request"""
    if Config.ALLOW_UNAUTHENTICATED_AGENT:
        return

    try:
        body = await req.json()
    except Exception:
        raw_body: bytes = await req.body()
        body = raw_body.decode("utf-8", errors="replace")

    params = dict(req.query_params) if req.query_params else None

    verify_signature_headers(
        secret_key=Config.AGENT_SECRET,
        signature_ttl=Config.AGENT_SIGNATURE_TTL,
        headers=dict(req.headers),
        method=req.method,
        path=req.url.path,
        body=body,
        params=params,
    )
