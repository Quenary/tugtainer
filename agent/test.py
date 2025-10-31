import hmac
import hashlib
import base64
import time
import json
import requests

AGENT_SECRET = "12345678"


def sign_request(body: dict | None, timestamp: int) -> str:
    # Если тела нет — подписываем просто timestamp
    msg_body = (
        b""
        if not body
        else json.dumps(body, separators=(",", ":")).encode()
    )
    msg = msg_body + str(timestamp).encode()
    signature = hmac.new(AGENT_SECRET.encode(), msg, hashlib.sha256).digest()
    return base64.b64encode(signature).decode()


def make_request(url: str, body: dict | None = None):
    timestamp = int(time.time())
    headers = {
        "X-Timestamp": str(timestamp),
        "X-Signature": sign_request(body, timestamp),
    }

    if body:
        response = requests.post(url, json=body, headers=headers)
    else:
        response = requests.get(url, headers=headers)

    return response.json()


# Пример использования
# print(make_request("http://agent.local:8080/status"))
if __name__ == "__main__":
    print(make_request("http://127.0.0.1:8001/api/container/inspect/socket-prox", ))
