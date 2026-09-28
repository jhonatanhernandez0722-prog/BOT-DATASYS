import hashlib
import hmac
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.whatsapp import (
    handle_incoming_messages,
    is_valid_webhook_signature,
    is_valid_webhook_verification,
    send_whatsapp_message,
)


class WhatsAppWebhookTests(unittest.IsolatedAsyncioTestCase):
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