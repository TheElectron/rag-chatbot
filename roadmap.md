# Workshop IA — Projeto prático: Chatbot com RAG

## Contexto

Vou construir um chatbot com RAG como **projeto prático de workshop** sobre a evolução da IA. O público são engenheiros de software. O projeto ilustra o "Ato III" da apresentação — Generative Learning — e serve como material didático.

**Restrição fundamental:** tudo roda **localmente** em qualquer hardware. Zero dependência de APIs pagas ou nuvem.

## Objetivo

Chatbot com interface web que responde perguntas usando RAG sobre uma base de documentos local. A interface deve ter um **toggle para ligar/desligar o RAG** durante a conversação, permitindo que os alunos comparem os dois modos lado a lado.

## Stack

- **Python** 3.10+
- **Ollama** — runtime local de LLMs (serve tanto geração quanto embeddings)
- **LangChain** — orquestração do pipeline RAG
- **ChromaDB** — vector store local, persistido em disco
- **FastAPI** — backend REST
- **Streamlit** — frontend de chat

## Arquitetura (3 camadas)

```
Usuário → Frontend (Streamlit) → Backend (FastAPI + LangChain) → { Ollama, ChromaDB }
```

**Frontend — responsabilidade única é UI:**
- `st.chat_input` + `st.chat_message` para o chat
- `st.toggle` na sidebar para o RAG on/off
- Histórico em `st.session_state`
- Chama o backend via HTTP — **nunca** conversa direto com Ollama ou ChromaDB

**Backend — toda inteligência vive aqui:**
- `POST /chat` — recebe mensagem + histórico + flag RAG; retorna resposta + fontes
- `POST /ingest` — ingere documentos (chunking + embeddings + persistência)
- `GET /health` — verifica Ollama e ChromaDB
- Fluxo condicional: se `rag_enabled=True`, faz retrieve + augment antes de gerar

**LLM + Vector Store:**
- Ollama serve dois modelos: `llama3.2:1b` (geração) e `nomic-embed-text` (embeddings)
- ChromaDB persistido em `./chroma_db/`
- Script `ingest.py` standalone para popular o banco antes do chat rodar

## Pipeline RAG — as 5 etapas explícitas

1. Mensagem do usuário chega
2. Embedding da mensagem via Ollama
3. Busca no ChromaDB (top-k chunks mais similares)
4. Prompt aumentado (mensagem + contexto + instrução para citar fontes)
5. LLM gera resposta via Ollama

Sem RAG: apenas as etapas 1 e 5. **O `if rag_enabled:` é didaticamente o coração do projeto.**

## Estrutura do repositório

```
chatbot-rag/
├── README.md              # Setup, arquitetura, como rodar
├── requirements.txt       # Versões travadas
├── setup.sh               # Baixa modelos Ollama + cria venv
├── config.py              # Parâmetros (modelos, paths, k, chunk size)
├── frontend.py            # Streamlit app
├── backend.py             # FastAPI + LangChain
├── ingest.py              # Script standalone de ingestão
├── documents/             # Docs de exemplo para ingestão
│   ├── intro.md
│   └── conceitos.md
└── chroma_db/             # Vector store (gerado)
```

## Preferências de código

1. **Código didático, não production-hardened.** Clareza > performance.
2. **Separação de responsabilidades estrita.** Frontend não importa ChromaDB nem chama Ollama direto.
3. **Comentários explicam o "por quê"**, não o "o quê". Especialmente nas etapas 2-4 do pipeline.
4. **LangChain sem abstrações mágicas.** Nada de `RetrievalQA.from_chain_type()` escondendo o prompt. Os alunos precisam **ver** retrieve e generate separados no código.
5. **Type hints** em todos os parâmetros e retornos.
6. **Logs informativos** nas etapas do pipeline — o aluno deve ver no terminal "embeddando query", "buscando 3 chunks", "chamando LLM" etc.

## Modelos por tier de hardware (mencionar no README)

| Tier | LLM | RAM |
|---|---|---|
| CPU modesta | `llama3.2:1b` | ~4GB |
| Máquina decente | `llama3.1:8b` | ~10GB |
| GPU | `llama3.1:8b`+ | ~10GB VRAM |

## Ordem de entrega

1. `README.md` — visão geral, arquitetura, setup
2. `requirements.txt` e `setup.sh`
3. `config.py`
4. `ingest.py` — funcionando standalone primeiro
5. `backend.py` — com os 3 endpoints
6. `frontend.py` — chat com toggle RAG

**Após cada entregável, me mostre o código e aguarde meu OK antes de seguir.** Quero revisar passo a passo para poder explicar depois aos alunos.

Vamos começar pelo README e pela estrutura do repositório.