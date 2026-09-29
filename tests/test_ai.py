import unittest
from unittest.mock import AsyncMock, patch

from app.ai import SYSTEM_INSTRUCTIONS, get_ai_response
from app.assistant import get_assistant_response


class AIProviderTests(unittest.IsolatedAsyncioTestCase):
    def test_system_prompt_restricts_chat_to_datasys(self) -> None:
        self.assertIn("exclusivamente para consultas relacionadas con DataSys", SYSTEM_INSTRUCTIONS)
        self.assertIn(
            "no respondas ese tema ni des consejos generales", SYSTEM_INSTRUCTIONS
        )

    async def test_openai_failure_uses_gemini_with_document_context(self) -> None:
        documents = {"servicios.txt": "DataSys ofrece analítica de datos."}
        with (
            patch("app.ai.AI_PRIMARY_PROVIDER", "openai"),
            patch("app.ai.AI_FALLBACK_PROVIDER", "gemini"),
            patch("app.ai.OPENAI_API_KEY", "openai-test-key"),
            patch("app.ai.GEMINI_API_KEY", "gemini-test-key"),
            patch("app.ai._request_openai", new_callable=AsyncMock) as openai,
            patch("app.ai._request_gemini", new_callable=AsyncMock) as gemini,
        ):
            openai.side_effect = ValueError("offline")
            gemini.return_value = "DataSys ofrece analítica de datos."

            response = await get_ai_response("¿Qué ofrecen?", documents)

        self.assertEqual(
            response, ("DataSys ofrece analítica de datos.", "gemini")
        )
        openai.assert_awaited_once()
        gemini.assert_awaited_once()
        self.assertIn("DataSys ofrece analítica de datos.", gemini.await_args.args[1])

    async def test_known_answer_is_sent_to_ai_as_context(self) -> None:
        documents = {
            "empresa.txt": (
                "Nuestro horario de atención es de lunes a viernes de 8:00 AM a 5:00 PM."
            )
        }
        with patch(
            "app.assistant.get_ai_response", new_callable=AsyncMock
        ) as ai_response:
            ai_response.return_value = (
                "Atendemos de lunes a viernes, de 8 a 5.",
                "openai",
            )
            response = await get_assistant_response("¿Cuál es el horario?", documents)

        self.assertEqual(
            response,
            ("Atendemos de lunes a viernes, de 8 a 5.", "openai"),
        )
        ai_response.assert_awaited_once()
        context = ai_response.await_args.args[1]
        self.assertIn("Nuestro horario de atención", str(context))

    async def test_greeting_is_also_answered_by_ai(self) -> None:
        with patch(
            "app.assistant.get_ai_response",
            new_callable=AsyncMock,
            return_value=("¡Hola! ¿En qué puedo ayudarte?", "openai"),
        ) as ai_response:
            response = await get_assistant_response("Hola", {})

        self.assertEqual(response, ("¡Hola! ¿En qué puedo ayudarte?", "openai"))
        ai_response.assert_awaited_once_with("Hola", {})

    async def test_unmatched_question_uses_ai_with_documents(self) -> None:
        documents = {"empresa.txt": "DataSys ofrece analítica de datos."}
        with patch(
            "app.assistant.get_ai_response",
            new_callable=AsyncMock,
            return_value=("Respuesta basada en el documento.", "gemini"),
        ) as ai_response:
            response = await get_assistant_response(
                "¿Cómo se integra ese servicio?", documents
            )

        self.assertEqual(response, ("Respuesta basada en el documento.", "gemini"))
        ai_response.assert_awaited_once_with(
            "¿Cómo se integra ese servicio?",
            {"conocimiento_relevante.txt": "[empresa.txt] DataSys ofrece analítica de datos."},
        )


if __name__ == "__main__":
    unittest.main()