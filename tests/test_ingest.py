import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document
from src.config import Settings
from src.ingest import prepare_documents, ingest_pdf, IngestionError, existing_documents


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(
            api_key="fake", database_url="postgresql+psycopg://localhost/rag",
            embedding_model="text-embedding-3-small", chat_model="gpt-6-luna",
            collection_name="test", pdf_path=Path(__file__).resolve().parents[1] / "document.pdf",
        )

    def test_stable_ids_metadata_and_collection_isolation(self):
        _, chunks, ids = prepare_documents(self.settings)
        self.assertEqual(ids, prepare_documents(self.settings)[2])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotEqual(ids, prepare_documents(replace(self.settings, collection_name="other"))[2])
        self.assertTrue(all(len(c.page_content) <= 1000 for c in chunks))
        self.assertTrue(all("page" in c.metadata and "source" in c.metadata for c in chunks))

    def test_missing_empty_and_invalid_pdf(self):
        with self.assertRaises(IngestionError):
            prepare_documents(replace(self.settings, pdf_path=Path("/nonexistent.pdf")))
        with patch("src.ingest.PyPDFLoader") as loader:
            loader.return_value.load.return_value = [Document(page_content=" ")]
            with self.assertRaises(IngestionError):
                prepare_documents(self.settings)
            loader.return_value.load.side_effect = ValueError("invalid")
            with self.assertRaises(IngestionError):
                prepare_documents(self.settings)

    def test_rerun_skips_stored_chunks(self):
        prepared = prepare_documents(self.settings)
        ids = prepared[2]
        with patch("src.ingest.load_settings", return_value=self.settings), patch(
            "src.ingest.prepare_documents", return_value=prepared
        ), patch("src.ingest.create_vector_store") as factory, patch(
            "src.ingest.existing_documents", side_effect=[set(), set(ids)]
        ), redirect_stdout(StringIO()):
            ingest_pdf()
            ingest_pdf()
            self.assertEqual(factory.return_value.add_documents.call_count, 1)
            self.assertEqual(factory.return_value.add_documents.call_args.kwargs["ids"], ids)

    def test_collection_mismatch_rejected(self):
        with patch("src.ingest.create_engine") as factory:
            connection = factory.return_value.connect.return_value.__enter__.return_value
            connection.execute.return_value.all.return_value = [("id", {"pdf_sha256": "other"})]
            with self.assertRaises(IngestionError):
                existing_documents(self.settings, "current")
            factory.return_value.dispose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
