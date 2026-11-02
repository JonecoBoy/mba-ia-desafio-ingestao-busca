# Ingestão e busca semântica de PDF

Aplicação Python com LangChain que armazena os trechos de um PDF no PostgreSQL
com pgVector e responde perguntas no terminal usando o conteúdo recuperado.
O [enunciado original](docs/ENUNCIADO.md) foi preservado separadamente.

## Arquitetura

```text
PDF → PyPDFLoader → chunks (1000 / overlap 150) → OpenAIEmbeddings → PGVector
Pergunta → OpenAIEmbeddings → busca k=10 → prompt obrigatório → ChatOpenAI → resposta
```

A ingestão e a busca compartilham configuração, collection e modelo de embeddings
em `src/config.py`. Cada pergunta é independente, sem histórico de conversa.
O prompt obrigatório é preservado em `src/search.py`, acompanhado de instruções
de sistema para manter as respostas no contexto do documento.

## Pré-requisitos

- Python 3.12 (validado com 3.12.15), com suporte a `venv` e `pip`.
- Docker com Docker Compose e daemon em execução.
- Porta 5432 disponível para o PostgreSQL local.
- Chave da API OpenAI com acesso aos modelos configurados e saldo/cota disponível.
- Acesso à internet para instalar dependências e consultar a API.

Os comandos abaixo devem ser executados na raiz do repositório, em um terminal
Linux/macOS. No Windows, use WSL ou adapte a ativação do ambiente virtual.

## Instalação e execução

### 1. Criar o ambiente virtual

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

As versões fornecidas de dependências foram mantidas e verificadas em Python
3.12. O arquivo inclui também a integração Gemini do projeto original; esta
solução usa apenas OpenAI e não exige chave Google.

### 2. Configurar o ambiente

Se ainda não existir um `.env`, copie o exemplo:

```bash
cp .env.example .env
```

Crie sua chave na [plataforma OpenAI](https://platform.openai.com/api-keys) e
preencha `OPENAI_API_KEY` no `.env` local. Preserve um `.env` já configurado.
Esse arquivo é ignorado pelo Git; nunca inclua a chave nos arquivos versionados.

| Variável | Valor do exemplo / finalidade |
| --- | --- |
| `OPENAI_API_KEY` | Vazia no exemplo; preencher com sua chave local |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` |
| `OPENAI_CHAT_MODEL` | `gpt-6-luna` |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5432/rag` |
| `PG_VECTOR_COLLECTION_NAME` | `document_pdf` |
| `PDF_PATH` | `document.pdf` |

O caminho relativo do PDF é resolvido a partir da raiz do projeto.
Variáveis exportadas no terminal têm precedência sobre o `.env`.
As credenciais do banco no Compose são destinadas à execução local da atividade.

Modelos consultados na documentação oficial em 02/11/2026:
[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) e
[embeddings](https://developers.openai.com/api/docs/guides/embeddings).
Ambos foram validados com uma chave real. A disponibilidade depende da sua conta;
chamadas à API consomem a cota ou o saldo correspondente.

### 3. Iniciar o banco

```bash
docker compose up -d
docker compose ps -a
docker compose logs bootstrap_vector_ext
```

Aguarde o serviço `postgres` ficar `healthy` e o `bootstrap_vector_ext` terminar
com `Exited (0)`. O segundo serviço cria a extensão `vector` e encerra normalmente.

### 4. Executar a ingestão

```bash
python src/ingest.py
```

O PDF fornecido possui 34 páginas e gera 67 chunks. A primeira execução gera
embeddings e grava os trechos com metadados de origem e página (índice iniciado
em zero). O modelo configurado gera vetores de 1536 dimensões por padrão.
Chunks têm até 1000 caracteres; o splitter usa overlap 150, que pode ser menor
nas fronteiras naturais do texto.

### 5. Iniciar o chat

```bash
python src/chat.py
```

```text
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: R$ 10.000.000,00

PERGUNTA: Em que ano a SuperTechIABrazil foi fundada?
RESPOSTA: A SuperTechIABrazil foi fundada em 2025.

PERGUNTA: Qual é a capital da França?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

Os dois fatos estão na página 3 do PDF. Digite `sair`, Ctrl+C ou EOF para encerrar.
Entradas vazias são ignoradas. A aplicação recupera até 10 trechos por pergunta,
concatena seus textos no prompt obrigatório e retorna a resposta da LLM.
Nenhum corte arbitrário por score de similaridade é aplicado.

## Reingestão e persistência

Os IDs dos chunks são determinísticos e incluem a collection, o hash do PDF,
o modelo, o índice e o conteúdo. Repetir a ingestão do mesmo documento com a
mesma configuração pula os chunks existentes, sem gerar embeddings novamente
para eles. Execute apenas uma ingestão por collection de cada vez.
Uma falha antes da gravação pode exigir gerar os embeddings novamente.

Se o PDF ou o modelo mudar, use outro `PG_VECTOR_COLLECTION_NAME` e execute a
ingestão novamente. A aplicação recusa misturar documentos ou configurações
na mesma collection. As collections antigas são preservadas; o chat deve usar
a mesma collection e o mesmo modelo de embeddings da nova ingestão.
A ingestão e as consultas de controle usam as tabelas de
`langchain-postgres==0.0.15`; revise a integração antes de atualizar o pacote.

```bash
docker compose restart postgres
```

O reinício preserva o volume `postgres_data`. `docker compose down` também
preserva esse volume. Já `docker compose down -v` **apaga os dados do projeto**;
nesse caso será necessário subir o banco e gerar os embeddings novamente.
Não é necessário apagar o volume para trocar de collection.

## Estrutura

```text
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .python-version
├── document.pdf
├── README.md
├── tasks.md
├── docs/
│   └── ENUNCIADO.md
├── src/
│   ├── config.py
│   ├── ingest.py
│   ├── search.py
│   └── chat.py
└── tests/
    ├── test_ingest.py
    ├── test_search.py
    └── test_chat.py
```

## Testes e validação

```bash
python -m unittest discover -s tests -v
```

Os testes automatizados isolam APIs externas e verificam IDs, reingestão,
metadados, erros de PDF, busca com k=10, montagem do contexto/prompt, ausência
de histórico, collection vazia/incompatível e interação no terminal.

A validação real foi realizada separadamente com PostgreSQL e OpenAI em
02/11/2026: 67 chunks persistidos, reingestão sem duplicação, respostas factuais
sobre faturamento e fundação da SuperTechIABrazil e recusas para capital da
França, clientes em 2024, opinião e pedido para ignorar as regras.
Os registros detalhados estão em [docs/VALIDACAO.md](docs/VALIDACAO.md).

Esses cenários não garantem fidelidade para toda pergunta possível. A resposta
depende dos trechos recuperados e do comportamento do modelo. PDFs sem texto
extraível precisam de OCR externo, que não faz parte desta atividade.

## Problemas comuns

| Problema | Como resolver |
| --- | --- |
| Variável ausente ou chave vazia | Confira `.env`, sem aspas extras nem valores vazios; verifique variáveis exportadas no terminal |
| Autenticação falhou | Confira se a chave OpenAI está válida e vinculada à conta correta |
| Limite ou saldo excedido | Confira saldo/cota na conta OpenAI; o crédito da API é necessário para as chamadas |
| Modelo indisponível ou falha de API | Confira acesso ao modelo configurado, conexão e status do provedor |
| Porta 5432 ocupada | Libere a porta ou altere a porta publicada no Compose e a porta em `DATABASE_URL` |
| Falha de conexão com o banco | Confira `docker compose ps -a`, healthcheck e `DATABASE_URL` |
| Extensão ausente | Confira `docker compose logs bootstrap_vector_ext` e execute `docker compose up -d` |
| Base vazia | Execute a ingestão com a mesma collection configurada para o chat |
| Outro PDF/modelo na collection | Defina uma nova collection e refaça a ingestão |
| PDF ausente, inválido ou sem texto | Confira `PDF_PATH`, proteção do arquivo e necessidade de OCR |

Erros de configuração, API e banco são apresentados separadamente das respostas.
A ingestão retorna status diferente de zero quando falha.
