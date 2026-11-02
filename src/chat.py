"""Chat no terminal, com perguntas independentes sobre o PDF."""

import sys

from openai import APIError, AuthenticationError, RateLimitError
from sqlalchemy.exc import SQLAlchemyError

if __package__:
    from .config import ConfigurationError
    from .search import SearchError, search_prompt
else:
    from config import ConfigurationError
    from search import SearchError, search_prompt


def error_message(exc):
    if isinstance(exc, (ConfigurationError, SearchError, ValueError)):
        return str(exc)
    if isinstance(exc, AuthenticationError):
        return "Autenticação falhou. Confira OPENAI_API_KEY no .env."
    if isinstance(exc, RateLimitError):
        return "Limite ou saldo da API excedido. Confira sua conta OpenAI."
    if isinstance(exc, APIError):
        return "Falha na API OpenAI. Confira conexão e acesso aos modelos configurados."
    return "Falha no PostgreSQL. Confira se o banco está ativo e a configuração está correta."


HANDLED_ERRORS = (ConfigurationError, SearchError, ValueError, APIError, SQLAlchemyError)


def main():
    try:
        chain = search_prompt()
    except HANDLED_ERRORS as exc:
        print("Erro ao iniciar: " + error_message(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130

    print("Chat sobre o PDF. Digite sair para encerrar.")
    while True:
        try:
            question = input("PERGUNTA: ").strip()
            if question.casefold() == "sair":
                return 0
            if not question:
                continue
            response = chain.invoke(question)
            print(f"RESPOSTA: {response}\n")
        except (EOFError, KeyboardInterrupt):
            print("\nChat encerrado.")
            return 0
        except HANDLED_ERRORS as exc:
            print("Erro: " + error_message(exc), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
