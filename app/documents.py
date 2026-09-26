import logging
from pathlib import Path

from docx import Document

from app.config import DOCUMENTS_DIRECTORY

logger = logging.getLogger(__name__)


def load_documents(directory: Path = DOCUMENTS_DIRECTORY) -> dict[str, str]:
    """Load paragraph text from each readable DOCX file in a directory."""
    if not directory.is_dir():
        return {}

    try:
        files = sorted(directory.iterdir(), key=lambda path: path.name.casefold())
    except OSError:
        logger.exception("Could not list documents directory: %s", directory)
        return {}

    documents: dict[str, str] = {}
    for file_path in files:
        if not file_path.is_file() or file_path.suffix.casefold() != ".docx":
            continue

        try:
            word_document = Document(file_path)
            paragraphs = [
                paragraph.text.strip()
                for paragraph in word_document.paragraphs
                if paragraph.text.strip()
            ]
            documents[file_path.name] = "\n".join(paragraphs)
        except Exception:
            logger.exception("Could not read document: %s", file_path.name)

    return documents