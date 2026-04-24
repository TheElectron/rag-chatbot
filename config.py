"""
config.py — Centraliza os parâmetros de execução do projeto.
"""

from pathlib import Path


BACKEND_URL = "http://localhost:8000"

# ───────────────────────────────────────────────────────────── Diretórios ─────────────────────────────────────────────────────────────

# Raiz do projeto (pasta onde este arquivo está)
BASE_DIR = Path(__file__).parent

# Pasta com os documentos que serão ingeridos pelo ingest.py
DOCUMENTS_DIR = BASE_DIR / "documents"

# Pasta onde o ChromaDB persiste os vetores em disco
CHROMA_DIR = BASE_DIR / "chroma_db"

# Nome da coleção dentro do ChromaDB
CHROMA_COLLECTION = "workshop_docs"

# ───────────────────────────────────────────────────────────── Modelos ─────────────────────────────────────────────────────────────

# URL padrão da API do Ollama
OLLAMA_BASE_URL = "http://localhost:11434"

# Modelo utilizado para gerar os embeddings dos documentos e das queries do usuário.
# Nota: É leve, ~274 MB,  e produz vetores até 768 dimensões.
EMBEDDING_MODEL = "nomic-embed-text"

# Modelo utilizado para conversação com o usuário.
GENERATION_MODEL = "llama3.2:1b"

# ───────────────────────────────────────────────────────────── Chunking ─────────────────────────────────────────────────────────────

# Tamanho de cada chunk em caracteres.
# Nota: Considere o trade off entre:
# chunks menores para buscas mais precisa X chunks maiores para mais contexto por bloco recuperado.
CHUNK_SIZE = 800

# Sobreposição de caracteres entre chunks consecutivos.
# Nota: Evita que uma ideia seja cortada exatamente na divisão entre dois chunks.
CHUNK_OVERLAP = 100

# ───────────────────────────────────────────────────────────── Retrieval ─────────────────────────────────────────────────────────────

# Quantos chunks recuperar do ChromaDB por query (top-k).
# Aumentar traz mais contexto, mas também mais ruído e prompts maiores.
RETRIEVAL_K = 3

# ───────────────────────────────────────────────────────────── Generation ─────────────────────────────────────────────────────────────

# Temperatura do modelo utilizado para conversação: 
# Nota: Utilize temperaturas mais baixas para respostas determinísticas, para respostas mais criativas é necessário aumentar a temperatura.
TEMPERATURE = 0.1

# Número máximo de tokens na resposta gerada.
MAX_TOKENS = 512
