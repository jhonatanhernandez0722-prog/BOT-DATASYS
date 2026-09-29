import unittest

from app.bot import get_bot_response
from app.responses import DOCUMENTS_UNAVAILABLE_RESPONSE, GREETING_RESPONSE


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
            get_bot_response("¿Dónde están ubicados?", documents),
            "La tecnología trabaja donde su equipo la necesita.",
        )

    def test_greetings_have_a_dedicated_reply_and_mixed_questions_keep_their_intent(self) -> None:
        for greeting in ("Hola", "¡Hola!", "Buenos días", "Hola, ¿qué tal?"):
            with self.subTest(greeting=greeting):
                self.assertEqual(
                    get_bot_response(greeting, self.documents), GREETING_RESPONSE
                )

        self.assertEqual(
            get_bot_response("Hola, ¿qué servicios ofrecen?", self.documents),
            "Ofrecemos consultoría, analítica de datos y automatización.",
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

    def test_general_services_are_grouped_by_data_and_development_core(self) -> None:
        documents = {
            "servicios.docx": (
                "DATA 01 — CONOCER ¿Qué está pasando en mi empresa?\n"
                "Servicios\nDashboards ejecutivos\nPower BI\n"
                "DATA 02 — ENTENDER ¿Por qué está pasando?\n"
                "Servicios\nAnalítica exploratoria\n"
                "DATA 03 — PREDECIR ¿Qué probablemente va a pasar?\n"
                "Servicios\nForecasting\nMachine Learning\n"
                "DATA 04 — DECIDIR ¿Qué debería hacer?\n"
                "Servicios\nIA generativa sobre datos empresariales\n"
                "NUESTROS SERVICIOS DE DESARROLLO\n"
                "DEV 01 — PRESENCIA DIGITAL Y E-COMMERCE (Sitios Web Inteligentes)\n"
                "Servicios: Sitios web corporativos, Landing pages, E-commerce.\n"
                "DEV 02 — SOFTWARE A LA MEDIDA (Sistemas Corporativos)\n"
                "Servicios: CRMs personalizados, Automatización de procesos.\n"
                "DEV 03 — RESCATE Y MANTENIMIENTO (Proyectos Externos)\n"
                "Servicios: Auditoría de código, Optimización de rendimiento."
            )
        }

        response = get_bot_response("¿Qué servicios ofrecen?", documents)
        self.assertIn("DATA ANALYTICS Y BIG DATA", response)
        self.assertIn("DATA 01 — CONOCER", response)
        self.assertIn("DATA 04 — DECIDIR", response)
        self.assertIn("NUESTROS SERVICIOS DE DESARROLLO", response)
        self.assertIn("DEV 03 — RESCATE Y MANTENIMIENTO", response)
        self.assertIn("- E-commerce", response)
        self.assertIn("- Automatización de procesos", response)

    def test_official_site_intents_select_the_requested_topics(self) -> None:
        documents = {
            "sitio.txt": (
                "SERVICIOS COMPLEMENTARIOS\n"
                "- Cloud y DevOps: infraestructura en la nube y despliegue continuo.\n"
                "- Ciberseguridad: protección mediante buenas prácticas.\n"
                "CLOUD Y DEVOPS\n"
                "DataSys ofrece infraestructura en la nube, automatización y despliegue continuo.\n"
                "GOVERNEX\n"
                "Governex es una plataforma para gestionar gobierno corporativo, cumplimiento y decisiones.\n"
                "POLÍTICA DE COTIZACIÓN\n"
                "El valor se define después de un diagnóstico a la medida, sin cotizaciones estandarizadas.\n"
                "SECTORES ATENDIDOS\n"
                "Empresas, sector público, educación, salud, comercio e inmobiliario.\n"
                "METODOLOGÍA DE TRABAJO\n"
                "Descubrimos las necesidades, diseñamos, desarrollamos, integramos, implementamos y evolucionamos."
            )
        }

        cloud = get_bot_response("¿Qué servicios de Cloud ofrecen?", documents)
        complementary = get_bot_response(
            "¿Qué servicios complementarios ofrecen?", documents
        )
        governex = get_bot_response("¿Qué es Governex?", documents)
        sectors = get_bot_response("¿A qué sectores atienden?", documents)
        methodology = get_bot_response("¿Cómo trabajan?", documents)
        quote = get_bot_response("¿Cómo solicito una cotización?", documents)

        self.assertIn("infraestructura en la nube", cloud)
        self.assertIn("CLOUD Y DEVOPS", cloud)
        self.assertIn("Ciberseguridad", complementary)
        self.assertIn("Governex es una plataforma", governex)
        self.assertIn("educación", sectors)
        self.assertIn("Descubrimos", methodology)
        self.assertIn("diagnóstico a la medida", quote)
        self.assertIn("sin cotizaciones estandarizadas", quote)
        self.assertNotIn("certificación ISO", complementary)

    def test_data_and_development_service_questions_show_their_full_group(self) -> None:
        documents = {
            "services.docx": (
                "DATA 01 — CONOCER\nServicios\nDashboards\n"
                "DATA 02 — ENTENDER\nServicios\nAnalítica exploratoria\n"
                "DATA 03 — PREDECIR\nServicios\nForecasting\n"
                "DATA 04 — DECIDIR\nServicios\nAgentes de IA\n"
                "DEV 01 — PRESENCIA DIGITAL (Sitios Web)\n"
                "Servicios: Sitios web corporativos, E-commerce.\n"
                "DEV 02 — SOFTWARE A LA MEDIDA (Sistemas)\n"
                "Servicios: CRMs, Automatización de procesos.\n"
                "DEV 03 — RESCATE Y MANTENIMIENTO (Proyectos)\n"
                "Servicios: Auditoría de código."
            )
        }

        data_response = get_bot_response("¿Qué servicios de Data Analytics ofrecen?", documents)
        software_response = get_bot_response("¿Qué servicios de desarrollo ofrecen?", documents)
        self.assertIn("DATA 04 — DECIDIR", data_response)
        self.assertNotIn("NUESTROS SERVICIOS DE DESARROLLO", data_response)
        self.assertIn("NUESTROS SERVICIOS DE DESARROLLO", software_response)
        self.assertIn("DEV 01 — PRESENCIA DIGITAL", software_response)
        self.assertIn("DEV 03 — RESCATE Y MANTENIMIENTO", software_response)

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

    def test_unknown_question_uses_the_closest_available_document_fragment(self) -> None:
        response = get_bot_response("¿Cuánto cuesta el almuerzo?", self.documents)
        self.assertIn(response, self.documents["empresa.docx"].splitlines())

    def test_known_intent_without_exact_match_uses_the_closest_fragment(self) -> None:
        documents = {"empresa.docx": "Ofrecemos consultoría de datos."}
        self.assertEqual(
            get_bot_response("¿Cuál es el horario?", documents),
            "Ofrecemos consultoría de datos.",
        )

    def test_existing_intents_without_exact_match_use_available_document_content(self) -> None:
        for question in ("Preguntas frecuentes", "Quiero hablar con un asesor"):
            with self.subTest(question=question):
                self.assertIn(
                    get_bot_response(question, self.documents),
                    self.documents["empresa.docx"].splitlines(),
                )

    def test_empty_documents_use_an_infrastructure_message(self) -> None:
        self.assertEqual(
            get_bot_response("¿Quiénes son?", {}), DOCUMENTS_UNAVAILABLE_RESPONSE
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
    def test_company_overview_accepts_ambiguous_wording(self) -> None:
        documents = {
            "perfil.docx": (
                "QUIÉNES SOMOS\n"
                "Somos DataSys Latam Group, una startup tecnológica que transforma retos empresariales en soluciones digitales. "
                "Integramos software, datos e inteligencia artificial para optimizar procesos y ayudar a las empresas a tomar mejores decisiones."
            ),
            "data.docx": (
                "DATA ANALYTICS Y BIG DATA\n"
                "Transformamos datos en conocimiento estratégico para tomar decisiones."
            ),
        }
        for question in (
            "¿A qué se dedica la empresa?",
            "¿Qué hace la empresa?",
            "Dame información de DataSys",
            "Quiero conocer la empresa",
            "Cuéntame sobre la empresa",
            "¿A qué se dedican?",
            "¿A qué se dedica esta empresa?",
            "¿Qué hace esta empresa?",
            "¿Cómo me pueden ayudar con mi empresa?",
            "Cuéntame de DataSys",
            "Háblame de la empresa",
        ):
            with self.subTest(question=question):
                response = get_bot_response(question, documents)
                self.assertIn("startup tecnológica", response)
                self.assertIn("soluciones digitales", response)

        specific = get_bot_response(
            "¿A qué se dedica la empresa en Data Analytics?", documents
        )
        self.assertIn("DATA ANALYTICS Y BIG DATA", specific)
        self.assertIn("conocimiento estratégico", specific)

        software_documents = {
            "empresa.docx": "DEV 01 — PRESENCIA DIGITAL (Sitios Web)\nServicios: Sitios web corporativos, E-commerce."
        }
        software = get_bot_response("¿Qué hace la empresa en software?", software_documents)
        self.assertIn("NUESTROS SERVICIOS DE DESARROLLO", software)
        self.assertIn("DEV 01 — PRESENCIA DIGITAL", software)

    def test_ambiguous_business_needs_route_to_the_closest_known_topic(self) -> None:
        documents = {
            "data.docx": (
                "DATA ANALYTICS Y BIG DATA\n"
                "Integramos datos dispersos para mejorar decisiones y generar información confiable."
            ),
            "operaciones.txt": (
                "DIGITALIZACIÓN DE OPERACIONES\n"
                "Automatizamos y centralizamos procesos de negocio para mejorar productividad."
            ),
        }
        cases = (
            ("Necesito mejorar mis decisiones con datos", "DATA ANALYTICS Y BIG DATA"),
            ("Me interesa automatizar los procesos de mi negocio", "DIGITALIZACIÓN DE OPERACIONES"),
            ("Busco centralizar mi información", "DIGITALIZACIÓN DE OPERACIONES"),
        )

        for question, expected_section in cases:
            with self.subTest(question=question):
                self.assertIn(expected_section, get_bot_response(question, documents))

    def test_unrelated_price_question_uses_the_closest_company_fragment(self) -> None:
        documents = {
            "comercial.txt": (
                "El valor de servicios y proyectos se define tras un diagnóstico a la medida."
            )
        }
        response = get_bot_response("¿Cuánto cuesta el almuerzo?", documents)
        self.assertIn("diagnóstico a la medida", response)
        self.assertNotIn("No encontré información", response)

    def test_unknown_but_related_question_returns_closest_fragment(self) -> None:
        documents = {
            "data.docx": (
                "Data Analytics y Big Data\n"
                "Realizamos análisis exploratorio de datos y análisis de correlaciones "
                "para identificar patrones y relaciones en la información."
            )
        }
        response = get_bot_response(
            "¿Me pueden contar del análisis exploratorio de datos?", documents
        )
        self.assertIn("análisis exploratorio de datos", response)
        self.assertTrue(response)

    def test_unrelated_greeting_uses_its_dedicated_response(self) -> None:
        self.assertEqual(
            get_bot_response("Hola, ¿qué tal?", {}), GREETING_RESPONSE
        )

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

    def test_each_data_stage_returns_its_own_services(self) -> None:
        documents = {
            "data.docx": (
                "DATA 01 — CONOCER ¿Qué está pasando en mi empresa?\n"
                "Servicios\nDashboards ejecutivos y operativos\nPower BI\n"
                "El resultado: una visión clara.\n"
                "DATA 02 — ENTENDER ¿Por qué está pasando?\n"
                "Servicios\nAnalítica exploratoria\nAnálisis de correlaciones\n"
                "El resultado: comprender las causas.\n"
                "DATA 03 — PREDECIR ¿Qué probablemente va a pasar?\n"
                "Servicios\nForecasting\nMachine Learning\nModelos de riesgo\n"
                "El resultado: anticiparse.\n"
                "DATA 04 — DECIDIR ¿Qué debería hacer?\n"
                "Servicios\nIA generativa sobre datos empresariales\nAgentes de IA\n"
                "DATA → INSIGHT → PREDICTION → ACTION\n"
                "Cada dato cuenta. Cada análisis revela. Cada predicción anticipa."
            )
        }
        cases = (
            ("¿Qué servicios ofrece DATA 01?", "Dashboards ejecutivos", "Power BI", "Forecasting"),
            ("¿Qué servicios hay para entender?", "Analítica exploratoria", "Análisis de correlaciones", "Agentes de IA"),
            ("¿Qué servicios tiene el nivel de predicción?", "Forecasting", "Modelos de riesgo", "Power BI"),
            ("¿Qué servicios incluye DATA 04?", "IA generativa", "Agentes de IA", "Analítica exploratoria"),
        )

        for question, expected, also_expected, excluded in cases:
            with self.subTest(question=question):
                response = get_bot_response(question, documents)
                self.assertIn(expected, response)
                self.assertIn(also_expected, response)
                self.assertNotIn(excluded, response)
                if "DATA 04" in question:
                    self.assertNotIn("Cada dato cuenta", response)

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

    def test_contact_questions_support_common_wording(self) -> None:
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
            get_bot_response("¿Cuál es el número de contacto?", documents),
        )
        self.assertIn(
            "contacto@datasyslatam.com",
            get_bot_response("¿Cuál es el email de contacto?", documents),
        )
        self.assertIn(
            "www.datasyslatam.com",
            get_bot_response("¿Cuál es el dominio?", documents),
        )
        self.assertIn(
            "Barranquilla, Colombia",
            get_bot_response("¿Cómo llegar a la oficina?", documents),
        )

    def test_data_analytics_overview_matches_broad_questions(self) -> None:
        documents = {
            "data.docx": (
                "Data Analytics y Big Data\n"
                "DataSys Latam Group S.A.S.\n"
                "Nit: 902051334-5\n"
                "DATA ANALYTICS Y BIG DATA\n"
                "Tus datos ya tienen valor. Nosotros los convertimos en inteligencia.\n"
                "DataSys Latam Group.\n"
                "En DataSys Latam Group S.A.S. transformamos los datos de las organizaciones "
                "en conocimiento estratégico para impulsar mejores decisiones, eficiencia "
                "e innovación. Integramos ingeniería de datos, Big Data, analítica avanzada "
                "e inteligencia artificial para conectar información dispersa, convertirla "
                "en conocimiento confiable y llevarla desde el análisis hasta la acción.\n"
                "NUESTRA PROPUESTA DE VALOR\n"
                "No queremos ser simplemente otro proveedor de Business Intelligence."
            )
        }

        for question in (
            "Cuéntame sobre Data Analytics y Big Data",
            "¿Qué hace DataSys en analítica de datos?",
            "¿Qué es Big Data?",
        ):
            with self.subTest(question=question):
                response = get_bot_response(question, documents)
                self.assertIn("Tus datos ya tienen valor", response)
                self.assertIn("desde el análisis hasta la acción", response)
                self.assertNotIn("NUESTRA PROPUESTA DE VALOR", response)

    def test_value_proposition_uses_the_service_area_named_in_question(self) -> None:
        documents = {
            "perfil.docx": "Más que tecnología, diseñamos funcionalidad.",
            "data.docx": (
                "Data Analytics y Big Data\n"
                "NUESTRA PROPUESTA DE VALOR\n"
                "No queremos ser simplemente otro proveedor de Business Intelligence.\n"
                "Queremos generar capacidad instalada para evolucionar:\n"
                "De datos dispersos a datos conectados\n"
                "De datos conectados a información confiable\n"
                "De información confiable a inteligencia empresarial\n"
                "De inteligencia empresarial a decisiones inteligentes\n"
                "Y de decisiones inteligentes a acciones automatizada.\n"
                "Brindamos 4 niveles de servicios:"
            ),
        }

        response = get_bot_response(
            "¿Cuál es la propuesta de valor de la línea de Data Analytics?", documents
        )
        self.assertIn("NUESTRA PROPUESTA DE VALOR", response)
        self.assertIn("De datos dispersos a datos conectados", response)
        self.assertIn("acciones automatizada", response)
        self.assertNotIn("Más que tecnología", response)


if __name__ == "__main__":
    unittest.main()