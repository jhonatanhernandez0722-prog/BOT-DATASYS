import unittest

from app.bot import get_bot_response
from app.responses import FALLBACK_RESPONSE


class BotDocumentSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = {
            "empresa.docx": (
                "Nuestro horario de atención es de lunes a viernes de 8:00 AM a 5:00 PM.\n"
                "Nuestra oficina se encuentra en Avenida Central 123.\n"
                "Ofrecemos consultoría, analítica de datos y automatización."
            )
        }

    def test_finds_hours_for_both_question_variants(self) -> None:
        expected = "Nuestro horario de atención es de lunes a viernes de 8:00 AM a 5:00 PM."
        self.assertEqual(
            get_bot_response("¿Cuál es el horario?", self.documents), expected
        )
        self.assertEqual(
            get_bot_response("¿A qué horas atienden?", self.documents), expected
        )

    def test_finds_location(self) -> None:
        expected = "Nuestra oficina se encuentra en Avenida Central 123."
        for question in ("¿Dónde están ubicados?", "¿Dónde?"):
            with self.subTest(question=question):
                self.assertEqual(get_bot_response(question, self.documents), expected)

    def test_figurative_where_does_not_count_as_location_evidence(self) -> None:
        documents = {"empresa.docx": "La tecnología trabaja donde su equipo la necesita."}
        self.assertEqual(
            get_bot_response("¿Dónde están ubicados?", documents), FALLBACK_RESPONSE
        )

    def test_finds_services(self) -> None:
        self.assertEqual(
            get_bot_response("¿Qué servicios ofrecen?", self.documents),
            "Ofrecemos consultoría, analítica de datos y automatización.",
        )

    def test_returns_the_services_list_under_its_heading(self) -> None:
        documents = {
            "analitica.docx": (
                "Por eso no ofrecemos soluciones genéricas: analizamos y diseñamos.\n"
                "Servicios\n"
                "Dashboards ejecutivos y operativos\n"
                "Power BI\n"
                "Diseño y gestión de KPIs\n"
                "Integración de fuentes de información\n"
                "Automatización de reportes\n"
                "Indicadores comerciales, financieros y operativos\n"
                "El resultado: una visión clara de la organización."
            )
        }
        self.assertEqual(
            get_bot_response("¿Qué servicios tiene?", documents),
            "Servicios:\n"
            "- Dashboards ejecutivos y operativos\n"
            "- Power BI\n"
            "- Diseño y gestión de KPIs\n"
            "- Integración de fuentes de información\n"
            "- Automatización de reportes\n"
            "- Indicadores comerciales, financieros y operativos",
        )

    def test_four_data_levels_are_distinct_from_service_offerings(self) -> None:
        documents = {
            "analitica.docx": (
                "Servicios\n"
                "Dashboards ejecutivos y operativos\n"
                "DATA 01 — CONOCER ¿Qué está pasando en mi empresa?\n"
                "DATA 02 — ENTENDER ¿Por qué está pasando?\n"
                "DATA 03 — PREDECIR ¿Qué probablemente va a pasar?\n"
                "DATA 04 — DECIDIR ¿Qué debería hacer?"
            )
        }
        response = get_bot_response("¿Cuáles son los 4 niveles de servicios?", documents)
        self.assertIn("DATA 01 — CONOCER", response)
        self.assertIn("DATA 04 — DECIDIR", response)
        self.assertNotIn("Dashboards", response)

    def test_three_dev_levels_are_separate_from_data_levels(self) -> None:
        documents = {
            "desarrollo.docx": (
                "DEV 01 — PRESENCIA DIGITAL Y E-COMMERCE (Sitios Web Inteligentes) "
                "Construimos sitios corporativos.\n"
                "DEV 02 — SOFTWARE A LA MEDIDA (Sistemas y Aplicaciones Corporativas) "
                "Desarrollamos plataformas.\n"
                "DEV 03 — RESCATE, MANTENIMIENTO Y EVOLUCIÓN (Para Proyectos Externos) "
                "Asumimos el control técnico."
            )
        }
        response = get_bot_response("¿Cuáles son los 3 niveles de desarrollo?", documents)
        self.assertIn("DEV 01 — PRESENCIA DIGITAL Y E-COMMERCE (Sitios Web Inteligentes)", response)
        self.assertIn("DEV 03 — RESCATE, MANTENIMIENTO Y EVOLUCIÓN (Para Proyectos Externos)", response)
        self.assertNotIn("Construimos", response)

    def test_unknown_question_uses_fallback(self) -> None:
        self.assertEqual(
            get_bot_response("¿Cuánto cuesta el almuerzo?", self.documents),
            FALLBACK_RESPONSE,
        )

    def test_known_intent_without_document_match_uses_fallback(self) -> None:
        documents = {"empresa.docx": "Ofrecemos consultoría de datos."}
        self.assertEqual(
            get_bot_response("¿Cuál es el horario?", documents), FALLBACK_RESPONSE
        )

    def test_existing_intents_without_document_match_use_fallback(self) -> None:
        for question in ("Preguntas frecuentes", "Quiero hablar con un asesor"):
            with self.subTest(question=question):
                self.assertEqual(
                    get_bot_response(question, self.documents), FALLBACK_RESPONSE
                )

    def test_result_is_deterministic_across_document_order(self) -> None:
        documents = {
            "zeta.docx": "Ofrecemos soporte de aplicaciones.",
            "alfa.docx": "Ofrecemos analítica de datos.",
        }
        reversed_documents = dict(reversed(list(documents.items())))
        question = "¿Qué servicios ofrecen?"
        self.assertEqual(
            get_bot_response(question, documents),
            get_bot_response(question, reversed_documents),
        )
        self.assertEqual(
            get_bot_response(question, documents), "Ofrecemos analítica de datos."
        )


class KnowledgeBaseIntentTests(unittest.TestCase):
    def test_company_name_and_nit(self) -> None:
        documents = {
            "perfil.docx": (
                "DataSys Latam Group S.A.S.\n"
                "Nit: 902051334-5"
            )
        }
        self.assertEqual(
            get_bot_response("¿Cómo se llama la empresa?", documents),
            "DataSys Latam Group S.A.S.",
        )
        self.assertEqual(
            get_bot_response("¿Cuál es el NIT?", documents), "Nit: 902051334-5"
        )

    def test_company_proposal_intents_select_distinct_sections(self) -> None:
        documents = {
            "perfil.docx": (
                "Más que tecnología, diseñamos funcionalidad.\n"
                "Comprendemos las necesidades de cada organización y creamos soluciones.\n"
                "Lo que nos diferencia\n"
                "Diseñamos tecnología para cada negocio."
            ),
            "data.docx": (
                "Data Analytics y Big Data\n"
                "NUESTRA PROPUESTA DE VALOR\n"
                "Conectamos datos y los convertimos en inteligencia.\n"
                "Brindamos 4 niveles de servicios:"
            ),
            "software.docx": (
                "Desarrollo de software y soluciones web\n"
                "NUESTRA PROPUESTA DE VALOR\n"
                "Llevamos procesos manuales a flujos automatizados.\n"
                "Nuestros servicios de desarrollo"
            ),
        }
        general = get_bot_response("¿Cuál es la propuesta de valor?", documents)
        data = get_bot_response(
            "¿Cuál es la propuesta de valor de Data Analytics?", documents
        )
        software = get_bot_response(
            "¿Cuál es la propuesta de valor del software?", documents
        )
        self.assertIn("Más que tecnología", general)
        self.assertIn("Conectamos datos", data)
        self.assertIn("flujos automatizados", software)
        self.assertEqual(len({general, data, software}), 3)

    def test_mission_and_vision_are_separate(self) -> None:
        documents = {
            "perfil.docx": (
                "Misión\nImpulsar la transformación digital de las organizaciones.\n"
                "Visión\nSer líderes en Latinoamérica en consultoría tecnológica.\n"
                "Nuestros principios"
            )
        }
        mission = get_bot_response("¿Cuál es la misión?", documents)
        vision = get_bot_response("¿Cuál es la visión?", documents)
        self.assertIn("Impulsar la transformación digital", mission)
        self.assertIn("Ser líderes en Latinoamérica", vision)
        self.assertNotEqual(mission, vision)

    def test_data_and_ai_service_queries_select_their_own_lists(self) -> None:
        documents = {
            "data.docx": (
                "DATA 03 — PREDECIR ¿Qué probablemente va a pasar?\n"
                "Servicios\nForecasting\nMachine Learning\nModelos de riesgo\n"
                "El resultado: anticiparse a los acontecimientos.\n"
                "DATA 04 — DECIDIR ¿Qué debería hacer?\n"
                "Servicios\nInteligencia artificial aplicada al negocio\n"
                "IA generativa sobre datos empresariales\nAgentes de IA\n"
                "El resultado: decisiones inteligentes."
            )
        }
        machine_learning = get_bot_response(
            "¿Qué servicios de Machine Learning ofrecen?", documents
        )
        artificial_intelligence = get_bot_response(
            "¿Qué servicios de IA ofrecen?", documents
        )
        self.assertIn("Forecasting", machine_learning)
        self.assertIn("Modelos de riesgo", machine_learning)
        self.assertIn("IA generativa", artificial_intelligence)
        self.assertIn("Agentes de IA", artificial_intelligence)
        self.assertNotIn("Modelos de riesgo", artificial_intelligence)

    def test_contact_questions_extract_each_field(self) -> None:
        documents = {
            "contacto.docx": (
                "Teléfono: +57 324 624 9237\n"
                "Correo electrónico: contacto@datasyslatam.com\n"
                "Sitio web: www.datasyslatam.com\n"
                "Dirección: Carrera 51B N° 106 - 250, Barranquilla, Colombia"
            )
        }
        self.assertIn(
            "+57 324 624 9237",
            get_bot_response("¿Cuál es el número de teléfono?", documents),
        )
        self.assertIn(
            "contacto@datasyslatam.com",
            get_bot_response("¿Cuál es el correo electrónico?", documents),
        )
        self.assertIn(
            "www.datasyslatam.com",
            get_bot_response("¿Cuál es el sitio web?", documents),
        )
        self.assertIn(
            "Carrera 51B",
            get_bot_response("¿Cuál es la dirección?", documents),
        )


if __name__ == "__main__":
    unittest.main()