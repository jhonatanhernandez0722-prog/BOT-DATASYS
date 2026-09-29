import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.main import app


class PublicChatPageTests(unittest.IsolatedAsyncioTestCase):
    async def test_homepage_serves_chat_interface(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Asistente DataSys", response.text)
        self.assertIn('id="chat-form"', response.text)
        self.assertIn('alt="DataSys Latam Group"', response.text)
        self.assertNotIn("Asistente virtual", response.text)
        self.assertIn('href="https://wa.me/573246249237"', response.text)
        self.assertIn(
            'href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;to=contacto%40datasyslatam.com"',
            response.text,
        )
        self.assertIn('href="https://datasyslatam.com/"', response.text)
        self.assertIn('href="https://www.google.com/maps/search/', response.text)
        self.assertIn('data-question="¿Cuál es la dirección?"', response.text)
        self.assertIn('rel="noopener noreferrer"', response.text)
        self.assertNotIn('data-question="¿Cuál es el horario?', response.text)
        self.assertEqual(response.text.count('class="quick-link"'), 4)

    async def test_chat_api_and_meta_webhook_routes_remain_available(self) -> None:
        paths = {
            (route.path, method)
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        self.assertIn(("/chat", "POST"), paths)
        self.assertIn(("/webhook/whatsapp", "GET"), paths)
        self.assertIn(("/webhook/whatsapp", "POST"), paths)
        self.assertIn(("/webhook", "GET"), paths)
        self.assertIn(("/webhook", "POST"), paths)

        with patch(
            "app.main.get_assistant_response",
            new_callable=AsyncMock,
            return_value=("Respuesta generada por IA.", "openai"),
        ) as assistant:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/chat", json={"message": "¿Cuál es el NIT?"}
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["response"], "Respuesta generada por IA.")
        self.assertEqual(response.json()["provider"], "openai")
        assistant.assert_awaited_once()

    async def test_chat_serializes_the_real_assistant_result(self) -> None:
        """Sin mockear el asistente: detecta desajustes de contrato en /chat.

        El asistente devuelve (texto, proveedor); si una capa intermedia olvida
        desempaquetar la tupla, FastAPI falla al serializar y este test lo ve.
        """
        with patch("app.ai.OPENAI_API_KEY", ""), patch("app.ai.GEMINI_API_KEY", ""):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/chat", json={"message": "¿Cuál es el teléfono de contacto?"}
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload["response"], str)
        self.assertTrue(payload["response"].strip())
        self.assertEqual(payload["provider"], "local")

    async def test_company_logo_is_served_as_png(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/documents/Logo.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertTrue(response.content.startswith(b"\x89PNG\r\n\x1a\n"))