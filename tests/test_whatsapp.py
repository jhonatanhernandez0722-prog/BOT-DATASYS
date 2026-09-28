import hashlib
import hmac
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from app.main import app
from app.whatsapp import (
    handle_incoming_messages,
    is_valid_webhook_signature,
    is_valid_webhook_verification,
    send_whatsapp_message,
)


class WhatsAppWebhookTests(unittest.IsolatedAsyncioTestCase):
    async def test_verification_route_is_available_at_whatsapp_path(self) -> None:
        with patch("app.main.WHATSAPP_VERIFY_TOKEN", "verify-secret"):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                for path in ("/webhook/whatsapp", "/webhook"):
                    response = await client.get(
                        path,
                        params={
                            "hub.mode": "subscribe",
                            "hub.verify_token": "verify-secret",
                            "hub.challenge": "challenge-value",
                        },
                    )
                    with self.subTest(path=path):
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.text, "challenge-value")

    async def test_signed_message_event_is_accepted_at_whatsapp_path(self) -> None:
        payload = b'{"entry":[]}'
        signature = hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
        with (
            patch("app.main.WHATSAPP_APP_SECRET", "app-secret"),
            patch("app.main.WHATSAPP_ACCESS_TOKEN", "access-token"),
            patch("app.main.WHATSAPP_PHONE_NUMBER_ID", "phone-id"),
            patch("app.main.handle_incoming_messages", new_callable=AsyncMock) as handle,
        ):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/webhook/whatsapp",
                    content=payload,
                    headers={"X-Hub-Signature-256": f"sha256={signature}"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        handle.assert_awaited_once_with({"entry": []}, app.state.documents)

    def test_webhook_verification_requires_matching_subscribe_token(self) -> None:
        self.assertTrue(is_valid_webhook_verification("subscribe", "secret", "secret"))
        self.assertFalse(is_valid_webhook_verification("unsubscribe", "secret", "secret"))
        self.assertFalse(is_valid_webhook_verification("subscribe", "wrong", "secret"))
        self.assertFalse(is_valid_webhook_verification("subscribe", "secret", ""))

    def test_webhook_signature_uses_meta_sha256_header(self) -> None:
        payload = b'{"object":"whatsapp_business_account"}'
        digest = hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
        self.assertTrue(
            is_valid_webhook_signature(payload, f"sha256={digest}", "app-secret")
        )
        self.assertFalse(is_valid_webhook_signature(payload, "sha256=wrong", "app-secret"))
        self.assertFalse(is_valid_webhook_signature(payload, None, "app-secret"))

    async def test_incoming_text_message_gets_a_bot_reply(self) -> None:
        event = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "573001112233",
                            "type": "text",
                            "text": {"body": "¿Cuál es el horario?"},
                        }]
                    }
                }]
            }]
        }
        documents = {
            "empresa.docx": "Nuestro horario de atención es de lunes a viernes de 8:00 AM a 5:00 PM."
        }

        with patch("app.whatsapp.send_whatsapp_message", new_callable=AsyncMock) as send:
            await handle_incoming_messages(event, documents)

        send.assert_awaited_once_with(
            "573001112233",
            "Nuestro horario de atención es de lunes a viernes de 8:00 AM a 5:00 PM.",
        )

    async def test_non_text_events_are_ignored(self) -> None:
        event = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{"from": "573001112233", "type": "image"}]
                    }
                }]
            }]
        }

        with patch("app.whatsapp.send_whatsapp_message", new_callable=AsyncMock) as send:
            await handle_incoming_messages(event, {})

        send.assert_not_awaited()

    async def test_send_uses_phone_number_messages_endpoint(self) -> None:
        response = Mock()
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response

        with (
            patch("app.whatsapp.WHATSAPP_API_VERSION", "v23.0"),
            patch("app.whatsapp.WHATSAPP_PHONE_NUMBER_ID", "phone-id"),
            patch("app.whatsapp.WHATSAPP_ACCESS_TOKEN", "access-token"),
            patch("app.whatsapp.httpx.AsyncClient", return_value=client),
        ):
            await send_whatsapp_message("573001112233", "Hola")

        client.post.assert_awaited_once_with(
            "https://graph.facebook.com/v23.0/phone-id/messages",
            headers={"Authorization": "Bearer access-token"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": "573001112233",
                "type": "text",
                "text": {"body": "Hola"},
            },
        )
        response.raise_for_status.assert_called_once_with()