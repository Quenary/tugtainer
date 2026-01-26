from fastapi import Request
from agent.config import Config
from shared.util.signature import verify_signature_headers


async def verify_signature(req: Request):
    """Verify signature of the request"""
    if not Config.AGENT_SECRET:
        return
    try:
        body = await req.json()
    except:
        body = None
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
