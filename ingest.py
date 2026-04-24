"""
ingest.py — script para de ingestão de documentos no ChromaDB.

1 - Lê arquivos no formato .txt e .md disponíveis na pasta ./documents;
2 - Fragmenta em chunks;
3 - Gera os embeddings
4 - Persiste no banco vetorial.
"""

import sys
import config
import logging
import chromadb
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader

# Configura o Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def carregar_documentos() -> list:
    """
        Método responsável por carregar os documentos na pasta DOCUMENTS_DIR.
    """
    log.info(f"Carregando documentos de: {config.DOCUMENTS_DIR}")
    if not config.DOCUMENTS_DIR.exists():
        log.error(f"Pasta '{config.DOCUMENTS_DIR}' não encontrada.")
        sys.exit(1)
    documentos = []
    for extensao in ("**/*.md", "**/*.txt"):
        loader = DirectoryLoader(
            str(config.DOCUMENTS_DIR),
            glob=extensao,
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True,
        )
        documentos.extend(loader.load())
    if not documentos:
        log.error("Nenhum documento .txt ou .md encontrado na pasta documents/.")
        sys.exit(1)
    log.info(f"{len(documentos)} documento(s) carregado(s).")
    return documentos


def fragmentar_em_chunks(documentos: list) -> list:
    """
        Método responsável por quebrar cada documento em blocos, chunks, para facilitar a busca semântica.
        Nota: A classe RecursiveCharacterTextSplitter utiliza separadores textuais (separators)
        como quebras de linha, espaços em branco e pontuações, preservando parte da coerência do texto.
        chunk_size    → tamanho máximo de cada pedaço (em caracteres);
        chunk_overlap → sobreposição entre chunks consecutivos;
    """
    log.info(
        f"Fragmentando documentos em chunks "
        f"(tamanho={config.CHUNK_SIZE}, overlap={config.CHUNK_OVERLAP})..."
    )
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documentos)
    log.info(f"{len(chunks)} chunk(s) gerado(s) a partir dos documentos.")
    return chunks


def gerar_embeddings_e_persistir(chunks: list) -> None:
    """
        Transforma cada chunk em uma sequência de embedding, utilizando o modelo nomic-embed-text.
        E armazena no banco o texto, seus embeddings e os metadados.
    """
    log.info(f"Conectando ao ChromaDB em: {config.CHROMA_DIR}")
    # PersistentClient salva em disco automaticamente
    cliente = chromadb.PersistentClient(path=str(config.CHROMA_DIR))            
    # Pontos importantes:
    # 1. hnsw ou Hierarchical Navigable Small World é o algoritmo de indexação utilizado pelo banco vetorial. 
    # 2. cosine é a métrica de distância utilizada pelo HNSW para medir a "semelhança" entre os vetores. 
    # Essas escolhas definem a geometria do espaço vetorial e afetam diretamente a qualidade dos resultados obtidos.
    colecao = cliente.get_or_create_collection(
        name=config.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    log.info(
        f"Inicializando modelo de embeddings: {config.EMBEDDING_MODEL} "
        f"(via Ollama em {config.OLLAMA_BASE_URL})"
    )
    embeddings_model = OllamaEmbeddings(
        model=config.EMBEDDING_MODEL,
        base_url=config.OLLAMA_BASE_URL,
    )
    log.info(f"Gerando embeddings e persistindo {len(chunks)} chunk(s)...")
    for i, chunk in enumerate(chunks, start=1):
        # Identificador único: fonte + posição no documento
        fonte = chunk.metadata.get("source", "desconhecido")
        chunk_id = f"{Path(fonte).stem}_{i}"
        log.info(f"  [{i}/{len(chunks)}] embeddando chunk de '{Path(fonte).name}'...")
        vetor = embeddings_model.embed_query(chunk.page_content)
        colecao.upsert(
            ids=[chunk_id],
            embeddings=[vetor],
            documents=[chunk.page_content],
            metadatas=[{"source": fonte}],
        )
    log.info(
        f"Ingestão concluída. {len(chunks)} chunk(s) persistido(s) "
        f"na coleção '{config.CHROMA_COLLECTION}'."
    )


def main() -> None:
    """
        Método responsável por orquestrar a ingestão de dados no banco vetorial.
    """
    log.info("=== Iniciando ingestão de documentos ===")
    documentos = carregar_documentos()
    log.info("=== Fragmentando o documento em blocos ===")
    chunks = fragmentar_em_chunks(documentos)
    log.info("=== Gerando e armazenando os em embeddings ===")
    gerar_embeddings_e_persistir(chunks)
    log.info("=== Ingestão de documentos finalizada ===")


if __name__ == "__main__":
    main()
