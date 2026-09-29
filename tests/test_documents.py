import tempfile
import unittest
from pathlib import Path

from docx import Document

from app.documents import load_documents


class DocumentLoaderTests(unittest.TestCase):
    def test_loads_docx_and_curated_utf8_text_but_ignores_other_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            word_document = Document()
            word_document.add_paragraph("Contenido Word")
            word_document.save(directory / "empresa.docx")
            (directory / "sitio.txt").write_text(
                "Governex ayuda con gobernanza corporativa.", encoding="utf-8"
            )
            (directory / "brochure.pdf").write_bytes(b"not parsed")

            documents = load_documents(directory)

        self.assertEqual(documents["empresa.docx"], "Contenido Word")
        self.assertEqual(
            documents["sitio.txt"], "Governex ayuda con gobernanza corporativa."
        )
        self.assertNotIn("brochure.pdf", documents)