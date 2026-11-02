import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from src.search import NO_INFORMATION, search_prompt, validate_collection, SearchError
from src.config import ConfigurationError


class SearchTests(unittest.TestCase):
    def build_chain(self, results):
        self.store = MagicMock()
        self.store.similarity_search_with_score.return_value = results
        self.messages = []
        def model(prompt):
            self.messages.append(prompt.to_messages())
            return AIMessage(content="Resposta baseada no PDF.")
        with patch("src.search.load_settings"), patch(
            "src.search.create_vector_store", return_value=self.store
        ), patch("src.search.validate_collection"), patch(
            "src.search.create_llm", return_value=RunnableLambda(model)
        ):
            return search_prompt()

    def test_retrieval_and_prompt_without_history(self):
        chain = self.build_chain([(Document(page_content="Faturamento R$ 10.000.000,00"), 0.2)])
        self.assertEqual(chain.invoke("Pergunta A"), "Resposta baseada no PDF.")
        self.store.similarity_search_with_score.assert_called_with("Pergunta A", k=10)
        chain.invoke("Pergunta B")
        self.assertIn("Faturamento R$ 10.000.000,00", self.messages[0][-1].content)
        self.assertIn("Pergunta A", self.messages[0][-1].content)
        self.assertNotIn("Pergunta A", self.messages[1][-1].content)
        self.assertIn(NO_INFORMATION, self.messages[0][-1].content)

    def test_no_documents_does_not_call_llm(self):
        chain = self.build_chain([])
        self.assertEqual(chain.invoke("Pergunta"), NO_INFORMATION)
        self.assertEqual(self.messages, [])

    def test_empty_question_does_not_search(self):
        chain = self.build_chain([])
        with self.assertRaises(ValueError):
            chain.invoke(" ")
        self.store.similarity_search_with_score.assert_not_called()

    def test_api_failure_is_not_a_factual_answer(self):
        chain = self.build_chain([])
        self.store.similarity_search_with_score.side_effect = RuntimeError("network")
        with self.assertRaises(RuntimeError):
            chain.invoke("Pergunta")

    def test_empty_collection_and_model_mismatch(self):
        settings = SimpleNamespace(database_url="unused", collection_name="test", embedding_model="expected")
        with patch("src.search.create_engine") as factory:
            rows = factory.return_value.connect.return_value.__enter__.return_value.execute.return_value.scalars.return_value
            rows.all.return_value = []
            with self.assertRaisesRegex(SearchError, "ingest.py"):
                validate_collection(settings)
            rows.all.return_value = [{"embedding_model": "other"}]
            with self.assertRaises(ConfigurationError):
                validate_collection(settings)
