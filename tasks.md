# Checklist de entrega

Estado consolidado em 02/11/2026. Evidências em [docs/VALIDACAO.md](docs/VALIDACAO.md).

## 1. Ambiente e modelos

- [x] Fork e clone com estrutura obrigatória e `document.pdf`.
- [x] Provedor OpenAI; modelos consultados na documentação oficial.
- [x] Embeddings `text-embedding-3-small`, dimensão observada 1536.
- [x] Modelo de resposta `gpt-6-luna`, acesso real confirmado.
- [x] Python 3.12.15 e ambiente virtual.
- [x] Dependências originais fixadas, instaladas e verificadas sem conflitos.
- [x] Documentação LangChain consultada via Context7; imports validados.

## 2. Configuração e banco

- [x] `.env.example` completo e `.env` local ignorado pelo Git.
- [x] Configuração compartilhada e validação de variáveis, URL e chave.
- [x] Modelos, collection e resolução do caminho do PDF compartilhados.
- [x] PostgreSQL saudável, bootstrap corrigido e extensão vector 0.8.7 ativa.
- [x] Conexão real via SQLAlchemy/psycopg.
- [x] Persistência validada após reiniciar o banco isolado.

## 3. Ingestão

- [x] Extração via PyPDFLoader, chunks 1000 e overlap configurado 150.
- [x] Metadados de origem, página, índice, hash e modelo preservados.
- [x] Embeddings reais gerados e 67 chunks persistidos.
- [x] IDs determinísticos; reexecução sem duplicação ou nova geração.
- [x] Collection com outro PDF/modelo/configuração recusada.
- [x] Mensagens de sucesso e erros de PDF, configuração, banco e API.

## 4. Busca e CLI

- [x] Vetorização da pergunta e busca `similarity_search_with_score(..., k=10)`.
- [x] Prompt obrigatório preservado e contexto concatenado.
- [x] Respostas textuais via LLM; frase obrigatória quando faltar informação.
- [x] Base vazia e modelo de embeddings incompatível tratados.
- [x] Loop de perguntas independentes, sem histórico.
- [x] Entradas vazias, sair, EOF e Ctrl+C tratados.
- [x] Falhas técnicas exibidas como erros separados das respostas.

## 5. Validação

- [x] 12 testes automatizados passaram, isolando APIs externas.
- [x] Faturamento e fundação da SuperTechIABrazil conferidos na página 3.
- [x] Recusas reais para conhecimento geral, clientes em 2024 e opinião.
- [x] Recusa real para tentativa de ignorar as regras.
- [x] Chunks, metadados, IDs e dimensões conferidos no PostgreSQL.
- [x] Erros de PDF/configuração, base vazia, banco indisponível e API verificados.
- [x] Fluxo completo reproduzido com ambiente virtual e banco novos.
- [x] Reinício preservou os 67 chunks e seus IDs no banco isolado.
- [x] Registros distinguem testes simulados e execução real.

## 6. Documentação e publicação

- [x] README da solução com arquitetura, estrutura e pré-requisitos.
- [x] Enunciado original preservado em `docs/ENUNCIADO.md`.
- [x] Instalação, configuração da chave e ordem de execução documentadas.
- [x] Exemplos factuais e de recusa registrados.
- [x] Reingestão, troca de collection/modelo, persistência e erros documentados.
- [x] Revisão dos arquivos publicáveis sem encontrar chaves ou arquivos locais.
- [x] Repositório público confirmado no GitHub.
- [x] Fazer commit da entrega e push no fork (`5f78166`, branch `main`).

## Decisões e limites

- As dependências originais foram mantidas após instalação limpa e `pip check`.
  A integração Gemini permanece instalada, mas não é usada pela solução.
- Um PDF por collection; troca de PDF ou modelo pede uma collection nova.
- Nenhuma interface web, memória de conversa ou OCR foi adicionado.
- Prompt e testes cobrem os cenários registrados; não garantem ausência de
  invenções em toda pergunta possível.
