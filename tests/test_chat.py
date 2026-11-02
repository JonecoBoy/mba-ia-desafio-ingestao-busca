import unittest
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import patch, MagicMock
from src.chat import main
from src.search import SearchError


class ChatTests(unittest.TestCase):
    def test_blank_input_multiple_questions_and_exit(self):
        chain = MagicMock()
        chain.invoke.return_value = "Resposta"
        with patch("src.chat.search_prompt", return_value=chain), patch(
            "builtins.input", side_effect=[" ", "Primeira", "Segunda", "SAIR"]
        ), redirect_stdout(StringIO()) as output:
            self.assertEqual(main(), 0)
        self.assertEqual(chain.invoke.call_count, 2)
        self.assertIn("RESPOSTA: Resposta", output.getvalue())

    def test_eof_and_interrupt(self):
        for exception in (EOFError, KeyboardInterrupt):
            with self.subTest(exception=exception), patch("src.chat.search_prompt"), patch(
                "builtins.input", side_effect=exception
            ), redirect_stdout(StringIO()):
                self.assertEqual(main(), 0)

    def test_initialization_failure(self):
        with patch("src.chat.search_prompt", side_effect=SearchError("Base vazia")), redirect_stderr(StringIO()) as output:
            self.assertEqual(main(), 1)
        self.assertIn("Base vazia", output.getvalue())
