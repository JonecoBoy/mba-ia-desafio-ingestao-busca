"""Configuração compartilhada pela ingestão e pela busca."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    """Configuração ausente ou inválida, sem exposição de credenciais."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    database_url: str = field(repr=False)
    embedding_model: str
    chat_model: str
    collection_name: str
    pdf_path: Path


def load_settings() -> Settings:
    # Variáveis exportadas no terminal têm precedência sobre o .env.
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    names = (
        "OPENAI_EMBEDDING_MODEL", "OPENAI_CHAT_MODEL", "DATABASE_URL",
        "PG_VECTOR_COLLECTION_NAME", "PDF_PATH",
    )
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise ConfigurationError("Configure no .env: " + ", ".join(missing))
    try:
        url = make_url(values["DATABASE_URL"])
        if url.drivername != "postgresql+psycopg" or not url.database:
            raise ValueError
        # Valida a porta sem incluir a URL em mensagens de erro.
        _ = url.port
    except (ArgumentError, ValueError):
        raise ConfigurationError(
            "DATABASE_URL deve usar postgresql+psycopg:// e informar o banco."
        ) from None
    path = Path(values["PDF_PATH"]).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return Settings(
        api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        database_url=values["DATABASE_URL"],
        embedding_model=values["OPENAI_EMBEDDING_MODEL"],
        chat_model=values["OPENAI_CHAT_MODEL"],
        collection_name=values["PG_VECTOR_COLLECTION_NAME"],
        pdf_path=path.resolve(),
    )


def require_api_key(settings: Settings) -> str:
    if not settings.api_key:
        raise ConfigurationError("Preencha OPENAI_API_KEY no .env para usar a API.")
    return settings.api_key


def create_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model, api_key=require_api_key(settings),
        request_timeout=60, max_retries=2,
    )


def create_llm(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.chat_model, api_key=require_api_key(settings),
        timeout=60, max_retries=2,
    )


def create_vector_store(settings: Settings) -> PGVector:
    return PGVector(
        embeddings=create_embeddings(settings),
        connection=settings.database_url,
        collection_name=settings.collection_name,
        use_jsonb=True,
        create_extension=False,  # A extensão é preparada pelo Docker Compose.
        engine_args={"connect_args": {"connect_timeout": 5}},
    )
