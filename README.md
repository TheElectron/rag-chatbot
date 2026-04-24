# Chatbot com RAG

Chatbot com interface web que responde perguntas usando **RAG (Retrieval-Augmented Generation)**.

Com destaque para o toggle **RAG on/off** na interface: permitindo ao usuário comparar as respostas do modelo com e sem contexto externo.

---

## Arquitetura

```
Usuário → Frontend (Streamlit) → Backend (FastAPI + LangChain) → { Ollama, ChromaDB }
```

O projeto é dividido em três camadas com responsabilidades claras:

| Camada | Tecnologia | Responsabilidade |
|---|---|---|
| Frontend | Streamlit | Interface com o usuário |
| Backend | FastAPI + LangChain | Processa as mensagens do usuário e orquestra o pipeline de RAG |
| Modelo/Vector Store | Ollama + ChromaDB | Geração de texto, embeddings, busca vetorial |

---

## Estrutura do Repositório

```
chatbot-rag/
├── README.md              # Este arquivo
├── requirements.txt       # Dependências com versões travadas
├── setup.sh               # Cria venv e baixa os modelos do Ollama
├── config.py              # Parâmetros centralizados (modelos, paths, chunk size, k)
├── ingest.py              # Script standalone: lê documentos e popula o ChromaDB
├── backend.py             # FastAPI + pipeline RAG via LangChain
├── frontend.py            # Interface Streamlit com toggle RAG
├── documents/             # Documentos para ingestão (.txt e .md)
└── chroma_db/             # Vector store persistido em disco (gerado pelo ingest.py)
```

---

## Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.com)

> Utilize o comando `ollama serve` para validar a instalação e a execução.

### Hardware e Modelos

| Config | LLM | Embedding |
|---|---|---|
| CPU (8 GB) | `llama3.2:1b` | `nomic-embed-text` |
| CPU (16 GB) | `llama3.1:8b` | `nomic-embed-text` |
| GPU (+16 GB) | Have fun! | Have fun! |

Por padrão, o projeto usa `llama3.2:1b`, compatível com qualquer hardware.
Para alterar, edite o arquivo `config.py`.

---

## RAG — Um pipeline em 5 etapas

Quando o RAG está **ligado**, cada pergunta passa por:

```
1. Mensagem do usuário chega ao backend
2. Embedding da mensagem (nomic-embed-text)
3. Busca semântica no ChromaDB (top-k chunks mais similares)
4. Prompt aumentado (contexto + mensagem do usuário + instrução)
5. LLM gera a resposta (llama3.2:1b)
```

Quando o RAG está **desligado**, apenas as etapas **1** e **5** são executadas.

### Como usar o Toggle RAG

1. Na sidebar, use o toggle **"Retrieval-Augmented Generation"** para ligar ou desligar o modo RAG.
2. Faça a mesma pergunta com RAG ligado e desligado.
3. Compare os resultados!

---

## Endpoints disponíveis

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Verifica se Ollama e ChromaDB estão prontos |
| `POST` | `/chat` | Recebe (mensagem + histórico + flag) → retorna resposta e fontes utilizadas |
| `POST` | `/ingest` | Ingere documentos (chunking → embeddings → ChromaDB) |
| `DELETE` | `/collection` | Remove todos os chunks do banco vetorial |

---

## Setup

```bash
# 1. Clone o repositório
git clone https://github.com/TheElectron/rag-chatbot.git
cd chatbot-rag

# 2. Rode o script de setup (cria venv + baixa modelos Ollama)
chmod +x setup.sh
./setup.sh

# 3. Ative o ambiente virtual
source venv/bin/activate

# 4. Ingira os documentos
python ingest.py

# 5. Suba o backend (terminal 1)
uvicorn backend:app --reload --port 8000

# 6. Suba o frontend (terminal 2)
streamlit run frontend.py
```

Acesse `http://localhost:8501` para abrir o chat.

---

## Gerenciando documentos pela interface

A sidebar da aplicação oferece controles completos sem precisar do terminal:

- **⬆ Ingerir documentos** — processa os arquivos da pasta `documents/` e atualiza o ChromaDB
- **✕ Limpar banco vetorial** — remove todos os chunks (útil para reiniciar do zero)
- **Status dos serviços** — indicadores em tempo real de Ollama e ChromaDB

Para adicionar seus próprios documentos, coloque arquivos `.txt` ou `.md` na pasta `documents/` e clique em **Ingerir documentos** na sidebar.

---

## Expondo via Cloudflare Tunnel

Para compartilhar o chatbot em uma rede (ex: workshop), use o `cloudflared`:

```bash
cloudflared tunnel --url http://localhost:8501
```

O terminal exibirá uma URL pública `*.trycloudflare.com` acessível por qualquer dispositivo, sem necessidade de conta ou configuração adicional.

> Apenas a porta 8501 (frontend) precisa ser exposta — as chamadas ao backend em `localhost:8000` acontecem na máquina.
