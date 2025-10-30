import hmac, hashlib, base64, time, json
from fastapi import FastAPI, Request, HTTPException
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
    verify_signature_headers(
        Config.AGENT_SECRET,
        Config.AGENT_SIGNATURE_TTL,
        dict(req.headers),
        req.method,
        str(req.url),
        body,
    )
