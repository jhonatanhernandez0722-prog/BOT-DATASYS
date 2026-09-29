import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env(*names: str, default: str = "") -> str:
    """Return the first environment variable that has a non-empty value."""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


COMPANY_NAME = os.getenv("COMPANY_NAME", "Nombre de la empresa")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIRECTORY = PROJECT_ROOT / "public" / "documents"
DOCUMENT_PREVIEW_LENGTH = 1000

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v23.0")

# --- Selección de modelo: gratuito frente a de pago ------------------------
#
# Cada proveedor pertenece a un nivel («tier») de coste:
#   free -> Gemini  (cuota gratuita de Google AI Studio)
#   paid -> OpenAI  (facturación por token)
#
# AI_TIER decide qué niveles puede usar el asistente:
#   auto (por defecto) -> proveedor principal y, si falla, el de respaldo.
#   free               -> SOLO el proveedor gratuito. Nunca genera costes.
#   paid               -> SOLO el proveedor de pago.
#
# El valor por defecto «auto» reproduce exactamente el comportamiento previo,
# por lo que actualizar el proyecto no cambia el gasto de nadie.
AI_TIER = _env("AI_TIER", default="auto").lower()
AI_FREE_PROVIDER = _env("AI_FREE_PROVIDER", default="gemini").lower()
AI_PAID_PROVIDER = _env("AI_PAID_PROVIDER", default="openai").lower()

AI_PRIMARY_PROVIDER = _env(
    "AI_PRIMARY_PROVIDER", "AI_PROVIDER", default="openai"
).lower()
AI_FALLBACK_PROVIDER = _env("AI_FALLBACK_PROVIDER", default="gemini").lower()

# Proveedor de pago (OpenAI). AI_MODEL_PAID y AI_MODEL son alias admitidos.
OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_API_URL = _env(
    "OPENAI_API_URL", default="https://api.openai.com/v1"
).rstrip("/")
OPENAI_MODEL = _env(
    "OPENAI_MODEL", "AI_MODEL_PAID", "AI_MODEL", default="gpt-4o-mini"
)

# Proveedor gratuito (Gemini). AI_MODEL_FREE y AI_FALLBACK_MODEL son alias.
#
# AI_FREE_MODEL se acepta por compatibilidad: en la configuración antigua ese
# nombre guardaba la *clave* de Gemini, no un modelo. Se avisa al arrancar para
# poder migrarla a GEMINI_API_KEY sin cortar el servicio mientras tanto.
_LEGACY_GEMINI_KEY = _env("AI_FREE_MODEL")
GEMINI_API_KEY = _env("GEMINI_API_KEY") or _LEGACY_GEMINI_KEY
GEMINI_API_URL = _env(
    "GEMINI_API_URL", default="https://generativelanguage.googleapis.com/v1beta"
).rstrip("/")
GEMINI_MODEL = _env(
    "GEMINI_MODEL", "AI_MODEL_FREE", "AI_FALLBACK_MODEL", default="gemini-3.6-flash"
)

if _LEGACY_GEMINI_KEY and not _env("GEMINI_API_KEY"):
    logger.warning(
        "AI_FREE_MODEL se está usando como clave de Gemini. Renómbrala a "
        "GEMINI_API_KEY en el archivo .env; el nombre antiguo dejará de "
        "admitirse en una versión futura."
    )

AI_TIMEOUT_SECONDS = float(_env("AI_TIMEOUT_SECONDS", default="20"))
AI_MAX_OUTPUT_TOKENS = int(_env("AI_MAX_OUTPUT_TOKENS", default="400"))
MAX_HISTORY_MESSAGES = int(_env("MAX_HISTORY_MESSAGES", default="10"))

# Vacío = sin middleware CORS, es decir solo mismo origen (comportamiento
# actual, ya que la interfaz se sirve desde este mismo backend).
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _env("ALLOWED_ORIGINS").split(",")
    if origin.strip()
]

RATE_LIMIT_REQUESTS = int(_env("RATE_LIMIT_REQUESTS", default="20"))
RATE_LIMIT_WINDOW_SECONDS = float(_env("RATE_LIMIT_WINDOW_SECONDS", default="60"))
