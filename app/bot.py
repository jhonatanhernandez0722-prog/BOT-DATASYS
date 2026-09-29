import re
import textwrap
import unicodedata
from collections.abc import Mapping

from app.responses import (
    CONTACT_FIELD_PATTERNS,
    COMPANY_LEGAL_NAME,
    DATA_STAGE_INTENTS,
    FALLBACK_RESPONSE,
    INTENT_CONTEXT_SECTIONS,
    INTENT_KEYWORDS,
    INTENT_SECTION_HEADINGS,
    INTENT_SEARCH_TERMS,
    MAX_CONTEXT_SECTION_LENGTH,
    MAX_RESPONSE_FRAGMENT_LENGTH,
    MINIMUM_RELEVANCE_SCORE,
    SECTION_BOUNDARY_HEADINGS,
    SERVICE_LEVEL_INTENTS,
)

STOP_WORDS = {
    "a", "al", "algo", "como", "cual", "cuales", "de", "del", "el", "ella",
    "ellas", "ellos", "en", "es", "esta", "estan", "este", "la", "las", "lo",
    "los", "me", "mi", "para", "por", "que", "se", "su", "un", "una", "y",
}

TOKEN_CANONICAL_FORMS = {
    "horarios": "horario",
    "horas": "hora",
    "atiende": "atender",
    "atienden": "atender",
    "atendemos": "atender",
    "atencion": "atender",
    "abren": "abrir",
    "abre": "abrir",
    "abierto": "abrir",
    "cierran": "cerrar",
    "cierra": "cerrar",
    "ubicado": "ubicacion",
    "ubicados": "ubicado",
    "ubicada": "ubicado",
    "ubicadas": "ubicado",
    "sedes": "sede",
    "encuentra": "encontrar",
    "encuentran": "encontrar",
    "encontramos": "encontrar",
    "servicios": "servicio",
    "ofrecen": "ofrecer",
    "ofrece": "ofrecer",
    "ofrecemos": "ofrecer",
    "hacen": "hacer",
    "hacemos": "hacer",
    "realizan": "realizar",
    "realizamos": "realizar",
    "prestan": "prestar",
    "brindan": "brindar",
    "desarrollan": "desarrollar",
    "am": "hora",
    "pm": "hora",
}


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    without_accents = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    without_punctuation = re.sub(r"[^\w\s]", " ", without_accents)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def _normalize_tokens(text: str) -> set[str]:
    tokens = set()
    for token in _normalize_text(text).split():
        if token in STOP_WORDS or token.isdigit():
            continue
        tokens.add(TOKEN_CANONICAL_FORMS.get(token, token))
    return tokens


def _matches_keyword(normalized_message: str, keyword: str) -> bool:
    normalized_keyword = _normalize_text(keyword)
    pattern = rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)"
    return re.search(pattern, normalized_message) is not None


def _find_intent(message: str) -> str | None:
    normalized_message = _normalize_text(message)

    for intent, (stage_number, _, stage_terms) in DATA_STAGE_INTENTS.items():
        has_stage = any(
            _matches_keyword(normalized_message, term) for term in stage_terms
        )
        has_stage_number = re.search(
            rf"(?<!\w)data\s+0?{stage_number}(?!\w)", normalized_message
        ) is not None
        has_service_context = any(
            _matches_keyword(normalized_message, term)
            for term in (
                "servicio", "servicios", "ofrece", "nivel", "etapa", "fase", "datos"
            )
        )
        if has_stage_number or (has_stage and has_service_context):
            return intent

    if _matches_keyword(normalized_message, "propuesta de valor"):
        if any(
            _matches_keyword(normalized_message, term)
            for term in ("data analytics", "big data", "analitica", "datos")
        ):
            return "propuesta_valor_data"
        if any(
            _matches_keyword(normalized_message, term)
            for term in ("software", "desarrollo", "soluciones web")
        ):
            return "propuesta_valor_software"

    matches = []
    for priority, (intent, keywords) in enumerate(INTENT_KEYWORDS.items()):
        for keyword in keywords:
            if _matches_keyword(normalized_message, keyword):
                matches.append((len(_normalize_text(keyword)), -priority, intent))

    return max(matches)[2] if matches else None


def _iter_fragments(content: str):
    for paragraph in content.splitlines():
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= MAX_RESPONSE_FRAGMENT_LENGTH:
                yield sentence
                continue

            yield from textwrap.wrap(
                sentence,
                width=MAX_RESPONSE_FRAGMENT_LENGTH,
                break_long_words=False,
                break_on_hyphens=False,
            )


def _is_section_boundary(line: str) -> bool:
    normalized_line = _normalize_text(line)
    boundary_headings = {
        _normalize_text(heading) for heading in SECTION_BOUNDARY_HEADINGS
    }
    return (
        normalized_line in boundary_headings
        or normalized_line.startswith("el resultado")
        or re.match(r"^(data|dev)\s+0?\d+\b", normalized_line) is not None
    )


def _find_context_section(
    documents: Mapping[str, str],
    intent: str,
) -> str | None:
    heading, required_context = INTENT_CONTEXT_SECTIONS[intent]
    normalized_heading = _normalize_text(heading)
    best_section = None

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if _normalize_text(line) != normalized_heading:
                continue

            if required_context:
                normalized_context = _normalize_text(required_context)
                context_found = False
                for preceding_line in reversed(lines[max(0, index - 10):index]):
                    normalized_line = _normalize_text(preceding_line)
                    if normalized_context in normalized_line:
                        context_found = True
                        break
                    if _is_section_boundary(preceding_line):
                        break
                if not context_found:
                    continue

            section_lines = [line.strip()]
            section_length = len(section_lines[0])
            for candidate in lines[index + 1:]:
                candidate = candidate.strip()
                if not candidate or _is_section_boundary(candidate):
                    break

                remaining = MAX_CONTEXT_SECTION_LENGTH - section_length - 1
                if remaining <= 0:
                    break
                if len(candidate) > remaining:
                    truncated_candidate = candidate[:remaining].rsplit(" ", 1)[0]
                    if truncated_candidate:
                        section_lines.append(truncated_candidate)
                    break

                section_lines.append(candidate)
                section_length += len(candidate) + 1

            if len(section_lines) > 1:
                section = "\n".join(section_lines)
                if best_section is None or len(section) > len(best_section):
                    best_section = section

    return best_section


def _find_contact_response(
    documents: Mapping[str, str],
    intent: str,
) -> str | None:
    fields = list(CONTACT_FIELD_PATTERNS) if intent == "contacto" else [
        "direccion" if intent == "ubicacion" else intent
    ]
    labels = {
        "telefono": "Teléfono",
        "correo": "Correo",
        "sitio_web": "Sitio web",
        "direccion": "Dirección",
    }
    matches: dict[str, str] = {}

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        for line in content.splitlines():
            for field in fields:
                if field in matches:
                    continue
                match = re.search(CONTACT_FIELD_PATTERNS[field], line, re.IGNORECASE)
                if match:
                    matches[field] = match.group(0).strip(" ,.;")

    if intent == "contacto":
        if not matches:
            return None
        return "Contacto:\n" + "\n".join(
            f"{labels[field]}: {matches[field]}" for field in fields if field in matches
        )

    field = fields[0]
    if field not in matches:
        return None
    return f"{labels[field]}: {matches[field]}"


def _find_company_name(documents: Mapping[str, str]) -> str | None:
    normalized_name = _normalize_text(COMPANY_LEGAL_NAME)
    for content in documents.values():
        if any(normalized_name in _normalize_text(line) for line in content.splitlines()):
            return COMPANY_LEGAL_NAME
    return None


def _find_intent_section(
    documents: Mapping[str, str],
    intent: str,
) -> str | None:
    headings = {
        _normalize_text(heading)
        for heading in INTENT_SECTION_HEADINGS.get(intent, [])
    }
    if not headings:
        return None

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if _normalize_text(line) not in headings:
                continue

            items = []
            for candidate in lines[index + 1:]:
                candidate = candidate.strip()
                if not candidate or re.search(r"[.!?:]$", candidate):
                    break

                proposed_items = [*items, f"- {candidate}"]
                response = f"{line.strip()}:\n" + "\n".join(proposed_items)
                if len(response) > MAX_RESPONSE_FRAGMENT_LENGTH:
                    break
                items = proposed_items

            if items:
                return f"{line.strip()}:\n" + "\n".join(items)

    return None


def _format_level_title(line: str, prefix: str) -> str:
    if prefix == "dev":
        title_end = line.find(")")
        if title_end >= 0:
            return line[:title_end + 1].strip()

    question_end = line.find("?")
    if question_end >= 0:
        return line[:question_end + 1].strip()

    sentence_end = re.search(r"[.!:]", line)
    if sentence_end:
        return line[:sentence_end.start()].strip()
    return line.strip()


def _find_service_levels(
    documents: Mapping[str, str],
    intent: str,
) -> str | None:
    prefix, expected_count, title = SERVICE_LEVEL_INTENTS[intent]
    level_pattern = re.compile(rf"^{re.escape(prefix)}\s+0?(\d+)\b")
    levels: dict[int, str] = {}

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        for line in content.splitlines():
            match = level_pattern.match(_normalize_text(line))
            if match is None:
                continue

            number = int(match.group(1))
            if 1 <= number <= expected_count and number not in levels:
                levels[number] = _format_level_title(line, prefix)

    if set(levels) != set(range(1, expected_count + 1)):
        return None

    level_lines = [f"- {levels[number]}" for number in range(1, expected_count + 1)]
    return f"{title}:\n" + "\n".join(level_lines)


def _find_data_stage_services(
    documents: Mapping[str, str],
    intent: str,
) -> str | None:
    stage_number, stage_name, _ = DATA_STAGE_INTENTS[intent]
    heading_pattern = re.compile(rf"^data\s+0?{stage_number}\b")
    best_items: list[str] = []

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if heading_pattern.match(_normalize_text(line)) is None:
                continue

            in_services = False
            items = []
            for candidate in lines[index + 1:]:
                candidate = candidate.strip()
                if not candidate:
                    continue

                normalized_candidate = _normalize_text(candidate)
                if (
                    re.match(r"^data\s+0?\d+\b", normalized_candidate)
                    or normalized_candidate.startswith("el resultado")
                    or normalized_candidate.startswith("data insight prediction action")
                    or normalized_candidate.startswith("cada dato cuenta")
                ):
                    break
                if normalized_candidate == "servicios":
                    in_services = True
                    continue
                if not in_services:
                    continue

                item = re.sub(r"^[-•]\s*", "", candidate).strip()
                response = f"DATA {stage_number:02d} — {stage_name.upper()}:\n"
                response += "\n".join(f"- {service}" for service in [*items, item])
                if len(response) > MAX_RESPONSE_FRAGMENT_LENGTH:
                    break
                items.append(item)

            if len(items) > len(best_items):
                best_items = items

    if not best_items:
        return None
    return (
        f"DATA {stage_number:02d} — {stage_name.upper()}:\n"
        + "\n".join(f"- {service}" for service in best_items)
    )


def _find_development_services(documents: Mapping[str, str]) -> str | None:
    heading_pattern = re.compile(r"^dev\s+0?(\d+)\b")
    service_pattern = re.compile(r"^servicios\s*:\s*(.+)$", re.IGNORECASE)
    groups: dict[int, tuple[str, list[str]]] = {}

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            match = heading_pattern.match(_normalize_text(line))
            if match is None:
                continue

            number = int(match.group(1))
            if number not in (1, 2, 3):
                continue

            title = _format_level_title(line, "dev")
            services = []
            for candidate in lines[index + 1:]:
                candidate = candidate.strip()
                if not candidate:
                    continue

                normalized_candidate = _normalize_text(candidate)
                if (
                    heading_pattern.match(normalized_candidate)
                    or normalized_candidate.startswith("el resultado")
                    or normalized_candidate.startswith("el diferencial datasys")
                ):
                    break

                service_match = service_pattern.match(candidate)
                if service_match is not None:
                    services.extend(
                        item.strip(" .;")
                        for item in re.split(r",\s*", service_match.group(1))
                        if item.strip(" .;")
                    )

            current = groups.get(number)
            if services and (current is None or len(services) > len(current[1])):
                groups[number] = (title, services)

    if not groups:
        return None

    return "\n\n".join(
        f"{title}\n" + "\n".join(f"- {service}" for service in services)
        for _, (title, services) in sorted(groups.items())
    )


def _find_service_catalog(
    documents: Mapping[str, str],
    include_data: bool = True,
    include_development: bool = True,
) -> str | None:
    sections = []
    if include_data:
        stages = [
            _find_data_stage_services(documents, intent)
            for intent in DATA_STAGE_INTENTS
        ]
        stages = [stage for stage in stages if stage]
        if stages:
            sections.append("DATA ANALYTICS Y BIG DATA\n" + "\n\n".join(stages))

    if include_development:
        development = _find_development_services(documents)
        if development:
            sections.append("NUESTROS SERVICIOS DE DESARROLLO\n" + development)

        additional_services = _find_context_section(
            documents, "servicios_complementarios"
        )
        if additional_services:
            sections.append(additional_services)

    return "\n\n".join(sections) if sections else None


def _score_fragment(
    fragment: str,
    query_tokens: set[str],
    intent_terms: set[str],
) -> int:
    fragment_tokens = _normalize_tokens(fragment)
    intent_matches = len(fragment_tokens & intent_terms)
    query_matches = len(fragment_tokens & query_tokens)
    return intent_matches * 2 + query_matches


def get_bot_response(message: str, documents: Mapping[str, str] | None = None) -> str:
    if not documents:
        return FALLBACK_RESPONSE

    intent = _find_intent(message)
    if intent is None:
        return FALLBACK_RESPONSE

    if intent in {"servicios", "servicios_data"}:
        catalog = _find_service_catalog(
            documents,
            include_data=True,
            include_development=intent == "servicios",
        )
        if catalog is not None:
            return catalog

    if intent == "servicios_software":
        catalog = _find_service_catalog(
            documents, include_data=False, include_development=True
        )
        if catalog is not None:
            return catalog

    if intent in SERVICE_LEVEL_INTENTS:
        return _find_service_levels(documents, intent) or FALLBACK_RESPONSE

    if intent in DATA_STAGE_INTENTS:
        return _find_data_stage_services(documents, intent) or FALLBACK_RESPONSE

    if intent == "nombre_empresa":
        return _find_company_name(documents) or FALLBACK_RESPONSE

    if intent in CONTACT_FIELD_PATTERNS or intent == "contacto":
        contact_response = _find_contact_response(documents, intent)
        if contact_response is not None:
            return contact_response

    if intent in INTENT_CONTEXT_SECTIONS:
        context_section = _find_context_section(documents, intent)
        if context_section is not None:
            return context_section

    section = _find_intent_section(documents, intent)
    if section is not None:
        return section

    query_tokens = _normalize_tokens(message)
    intent_terms = _normalize_tokens(" ".join(INTENT_SEARCH_TERMS.get(intent, [])))
    best_fragment = None
    best_score = MINIMUM_RELEVANCE_SCORE - 1

    for _, content in sorted(
        documents.items(), key=lambda document: (document[0].casefold(), document[0])
    ):
        for fragment in _iter_fragments(content):
            score = _score_fragment(fragment, query_tokens, intent_terms)
            if score > best_score:
                best_fragment = fragment
                best_score = score

    return best_fragment if best_fragment is not None else FALLBACK_RESPONSE