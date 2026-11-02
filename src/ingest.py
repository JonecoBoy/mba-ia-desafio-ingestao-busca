"""Ingestão de PDF com reexecução sem duplicação."""

import hashlib
import sys

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import APIError, AuthenticationError, RateLimitError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

if __package__:
    from .config import ConfigurationError, create_vector_store, load_settings
else:
    from config import ConfigurationError, create_vector_store, load_settings


class IngestionError(ValueError):
    """PDF inválido ou incompatibilidade da collection."""


def prepare_documents(settings):
    if not settings.pdf_path.is_file():
        raise IngestionError("PDF não encontrado. Confira PDF_PATH no .env.")
    try:
        fingerprint = hashlib.sha256(settings.pdf_path.read_bytes()).hexdigest()
        pages = PyPDFLoader(str(settings.pdf_path)).load()
    except Exception:
        raise IngestionError("Não foi possível ler o PDF. Confira o arquivo e sua proteção.") from None
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150,
    ).split_documents([page for page in pages if page.page_content.strip()])
    if not chunks:
        raise IngestionError("O PDF não contém texto utilizável. PDFs digitalizados precisam de OCR.")
    ids = []
    for index, chunk in enumerate(chunks):
        chunk.metadata.update(
            pdf_sha256=fingerprint, embedding_model=settings.embedding_model,
            chunk_index=index, chunk_size=1000, chunk_overlap=150,
        )
        # Os IDs do PGVector são globais; incluir a collection evita colisões.
        identity = f"{settings.collection_name}:{fingerprint}:{settings.embedding_model}:{index}:{chunk.page_content}"
        ids.append(hashlib.sha256(identity.encode()).hexdigest())
    return len(pages), chunks, ids


def existing_documents(settings, fingerprint):
    """Valida a collection antes de enviar texto à API."""
    engine = create_engine(settings.database_url, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("""
                SELECT e.id, e.cmetadata
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                WHERE c.name = :name
            """), {"name": settings.collection_name}).all()
        for _, metadata in rows:
            if (not metadata or metadata.get("pdf_sha256") != fingerprint
                    or metadata.get("embedding_model") != settings.embedding_model
                    or metadata.get("chunk_size") != 1000
                    or metadata.get("chunk_overlap") != 150):
                raise IngestionError(
                    "A collection contém outro PDF ou configuração. "
                    "Use um novo PG_VECTOR_COLLECTION_NAME e refaça a ingestão."
                )
        return {row.id for row in rows}
    finally:
        engine.dispose()


def ingest_pdf():
    settings = load_settings()
    page_count, chunks, ids = prepare_documents(settings)
    store = create_vector_store(settings)
    existing = existing_documents(settings, chunks[0].metadata["pdf_sha256"])
    pending = [(chunk, id_) for chunk, id_ in zip(chunks, ids) if id_ not in existing]
    if pending:
        print(f"Gerando embeddings e salvando {len(pending)} chunks...", flush=True)
        store.add_documents(
            [chunk for chunk, _ in pending], ids=[id_ for _, id_ in pending],
        )
    print(
        f"Ingestão concluída: {page_count} páginas, {len(chunks)} chunks; "
        f"{len(pending)} novos, {len(chunks) - len(pending)} já existentes."
    )


def main():
    try:
        ingest_pdf()
    except (ConfigurationError, IngestionError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except AuthenticationError:
        print("Erro: autenticação na OpenAI falhou. Confira OPENAI_API_KEY.", file=sys.stderr)
        return 1
    except RateLimitError:
        print("Erro: limite ou saldo da API excedido. Confira sua conta OpenAI.", file=sys.stderr)
        return 1
    except APIError:
        print("Erro: não foi possível gerar embeddings na API OpenAI. Tente novamente.", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("Erro: falha no PostgreSQL. Confira conexão, extensão vector e compatibilidade dos embeddings.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Ingestão interrompida.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
