"""
backend.py — FastAPI, componente responsável pela resposta para o usuário.

1 - GET  /health  → verifica se Ollama e ChromaDB estão prontos;
2 - POST /chat    → recebe mensagem + histórico + flag RAG e retorna resposta + fontes;
3 - POST /ingest  → dispara a ingestão de documentos via HTTP.
4 - Delete /collection → limpa o banco vetorial
"""

import httpx
import config
import ingest
import logging
import chromadb
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import OllamaEmbeddings, OllamaLLM


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
app = FastAPI(title="Chatbot + RAG", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ───────────────────────────────────────────────────────────── Clientes ─────────────────────────────────────────────────────────────

_chroma = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
_colecao = _chroma.get_or_create_collection(
    name=config.CHROMA_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)

# O modelo de embeddings deve ser o mesmo usado no ingest.py
# Vetores gerados por modelos diferentes são incompatíveis.
_embeddings = OllamaEmbeddings(model=config.EMBEDDING_MODEL, base_url=config.OLLAMA_BASE_URL)

_llm = OllamaLLM(
    model=config.GENERATION_MODEL,
    base_url=config.OLLAMA_BASE_URL,
    temperature=config.TEMPERATURE,
    num_predict=config.MAX_TOKENS,
)


# ───────────────────────────────────────────────────────────── Schemas ─────────────────────────────────────────────────────────────

class Mensagem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    mensagem: str
    historico: list[Mensagem] = []
    rag_enabled: bool = True


class ChatResponse(BaseModel):
    resposta: str
    fontes: list[str]
    rag_enabled: bool


class IngestResponse(BaseModel):
    status: str
    mensagem: str


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    chromadb: bool
    documentos_no_banco: int


# ───────────────────────────────────────────────────────────── Pipeline ─────────────────────────────────────────────────────────────


def recuperar_chunks(query: str) -> tuple[list[str], list[str]]:
    """
        Método responsãvel pela etapa de retrieval
        - Gera o embedding da query;
        - Busca os top-k chunks mais similares no ChromaDB.
        Retorna os textos dos chunks e os caminhos dos arquivos de origem.
    """
    log.info(f"[RAG] Gerando os embeddings para a query: '{query[:60]}'")
    vetor_query = _embeddings.embed_query(query)
    # Limita n_results ao total disponível — evita o aviso do ChromaDB quando
    # o banco tem menos chunks do que o k configurado (ex: logo após a ingestão)
    k = min(config.RETRIEVAL_K, _colecao.count())
    log.info(f"[RAG] Buscando {k} chunk(s) no ChromaDB (k={config.RETRIEVAL_K}, disponíveis={_colecao.count()})...")
    resultado = _colecao.query(
        query_embeddings=[vetor_query],
        n_results=k,
        include=["documents", "metadatas"],
    )
    textos: list[str] = resultado["documents"][0]
    fontes: list[str] = [m.get("source", "desconhecido") for m in resultado["metadatas"][0]]
    log.info(f"[RAG] {len(textos)} chunk(s) recuperado(s) de: {set(fontes)}")
    return textos, fontes


def montar_prompt(mensagem: str, historico: list[Mensagem], contexto: str | None = None) -> str:
    """
        Método responsãvel pela etapa de generation
        Constrói o prompt aumentado — instrução + contexto recuperado + histórico + mensagem do usuário.
        Nota: Quando rag_enabled=False, contexto é None e o modelo responde só com seu conhecimento de treinamento.
    """
    partes: list[str] = []
    if contexto:
        partes.append(
            "Você é um assistente conversacional."
            "Responda à pergunta do usuário com base EXCLUSIVAMENTE no contexto abaixo.\n"
            f"\nContexto:\n{contexto}\n"
            "Se a resposta não estiver no contexto, retorne a seguinte mensagem para o usuário.\n"
            "Infelizmente essa pergunta vai além dos meus conhecimentos, que tal tentar outra?"
        )
    else:
        partes.append("Você é um assistente conversacional. Responda à pergunta do usuário.\n")
    for msg in historico:
        prefixo = "Usuário" if msg.role == "user" else "Assistente"
        partes.append(f"{prefixo}: {msg.content}")
    partes.append(f"Usuário: {mensagem}")
    partes.append("Assistente:")
    return "\n".join(partes)


# ───────────────────────────────────────────────────────────── Endpoints ─────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
        Verifica se o ambiente está operacional.
    """
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception:
        pass
    chroma_ok = False
    docs_count = 0
    try:
        docs_count = _colecao.count()
        chroma_ok = True
    except Exception:
        pass
    log.info(f"[Health] ollama={ollama_ok}, chromadb={chroma_ok}, docs={docs_count}")
    return HealthResponse(
        status="ok" if (ollama_ok and chroma_ok) else "degradado",
        ollama=ollama_ok,
        chromadb=chroma_ok,
        documentos_no_banco=docs_count,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
        Orquestra a geração da resposta para o usuário.
    """
    log.info(f"[Chat] Mensagem recebida (rag={'on' if req.rag_enabled else 'off'}): '{req.mensagem[:60]}'")
    fontes: list[str] = []
    contexto: str | None = None
    if req.rag_enabled:
        # Etapas 2 e 3: embedding da query + busca no ChromaDB
        chunks, fontes = recuperar_chunks(req.mensagem)
        # Etapa 4: monta o prompt aumentado com o contexto recuperado
        log.info("[RAG] Montando prompt aumentado com o contexto...")
        contexto = "\n\n---\n\n".join(chunks)
    # Etapa 5: LLM gera a resposta (sempre executada, com ou sem RAG)
    log.info(f"[Chat] Chamando LLM ({config.GENERATION_MODEL})...")
    resposta: str = _llm.invoke(montar_prompt(req.mensagem, req.historico, contexto))
    log.info(f"[Chat] Resposta gerada ({len(resposta)} caracteres).")
    return ChatResponse(
        resposta=resposta.strip(),
        fontes=list(set(fontes)),
        rag_enabled=req.rag_enabled,
    )


@app.post("/ingest", response_model=IngestResponse)
def ingerir() -> IngestResponse:
    """
        Método responsável pela ingestão de documentos via HTTP, reutilizando as funções do ingest.py.
    """
    log.info("[Ingest] Ingestão disparada via endpoint HTTP...")
    try:
        documentos = ingest.carregar_documentos()
        chunks = ingest.fragmentar_em_chunks(documentos)
        ingest.gerar_embeddings_e_persistir(chunks)
        return IngestResponse(status="ok", mensagem=f"{len(chunks)} chunk(s) ingerido(s) com sucesso.")
    except Exception as e:
        log.error(f"[Ingest] Erro durante ingestão: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/collection", response_model=IngestResponse)
def limpar_colecao() -> IngestResponse:
    """
        Remove todos os documentos da coleção no ChromaDB.
        Nota: a coleção é recriada vazia — o banco continua operacional após a limpeza.
    """
    log.info("[Collection] Limpando coleção do ChromaDB...")
    try:
        total = _colecao.count()
        _chroma.delete_collection(config.CHROMA_COLLECTION)
        # Recria a coleção vazia com as mesmas configurações
        globals()["_colecao"] = _chroma.get_or_create_collection(
            name=config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        log.info(f"[Collection] {total} chunk(s) removido(s).")
        return IngestResponse(status="ok", mensagem=f"{total} chunk(s) removido(s) do banco.")
    except Exception as e:
        log.error(f"[Collection] Erro ao limpar coleção: {e}")
        raise HTTPException(status_code=500, detail=str(e))
