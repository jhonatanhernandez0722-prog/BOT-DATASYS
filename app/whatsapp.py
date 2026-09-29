import hashlib
import hmac
from collections.abc import Mapping

import httpx

from app.assistant import get_assistant_response
from app.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_VERIFY_TOKEN,
)


def is_valid_webhook_verification(
    mode: str | None,
    token: str | None,
    expected_token: str,
) -> bool:
    return bool(
        expected_token
        and mode == "subscribe"
        and token
        and hmac.compare_digest(token, expected_token)
    )


def is_valid_webhook_signature(
    payload: bytes,
    signature: str | None,
    app_secret: str,
) -> bool:
    if not app_secret or not signature or not signature.startswith("sha256="):
        return False
    expected_signature = hmac.new(
        app_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected_signature)


async def send_whatsapp_message(recipient: str, message: str) -> None:
    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"body": message},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()


async def handle_incoming_messages(
    event: Mapping[str, object],
    documents: Mapping[str, str],
) -> None:
    entries = event.get("entry", [])
    if not isinstance(entries, list):
        return

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes", [])
        if not isinstance(changes, list):
            continue

        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value", {})
            if not isinstance(value, dict):
                continue
            messages = value.get("messages", [])
            if not isinstance(messages, list):
                continue

            for incoming in messages:
                if not isinstance(incoming, dict) or incoming.get("type") != "text":
                    continue
                sender = incoming.get("from")
                text = incoming.get("text")
                if not isinstance(sender, str) or not isinstance(text, dict):
                    continue
                body = text.get("body")
                if not isinstance(body, str) or not body.strip():
                    continue

                reply, _provider = await get_assistant_response(body, documents)
                await send_whatsapp_message(sender, reply)