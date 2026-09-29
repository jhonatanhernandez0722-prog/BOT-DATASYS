import logging
from pathlib import Path

from docx import Document

from app.config import DOCUMENTS_DIRECTORY

logger = logging.getLogger(__name__)


def load_documents(directory: Path = DOCUMENTS_DIRECTORY) -> dict[str, str]:
    """Load readable DOCX files and curated UTF-8 text documents."""
    if not directory.is_dir():
        return {}

    try:
        files = sorted(directory.iterdir(), key=lambda path: path.name.casefold())
    except OSError:
        logger.exception("Could not list documents directory: %s", directory)
        return {}

    documents: dict[str, str] = {}
    for file_path in files:
        if not file_path.is_file():
            continue

        try:
            suffix = file_path.suffix.casefold()
            if suffix == ".docx":
                word_document = Document(file_path)
                paragraphs = [
                    paragraph.text.strip()
                    for paragraph in word_document.paragraphs
                    if paragraph.text.strip()
                ]
                content = "\n".join(paragraphs)
            elif suffix == ".txt":
                content = file_path.read_text(encoding="utf-8").strip()
            else:
                continue

            if content:
                documents[file_path.name] = content
        except Exception:
            logger.exception("Could not read document: %s", file_path.name)

    return documents