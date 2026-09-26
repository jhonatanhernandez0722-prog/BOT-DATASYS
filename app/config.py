import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

COMPANY_NAME = os.getenv("COMPANY_NAME", "Nombre de la empresa")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIRECTORY = PROJECT_ROOT / "public" / "documents"
DOCUMENT_PREVIEW_LENGTH = 1000