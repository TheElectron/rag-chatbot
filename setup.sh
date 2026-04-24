#!/usr/bin/env bash
# setup.sh — prepara o ambiente completo para o projeto RAG Chatbot
#
# O que este script faz:
#   1. Verifica pré-requisitos (Python 3.10+ e Ollama)
#   2. Cria um virtualenv isolado em ./venv
#   3. Instala as dependências Python do requirements.txt
#   4. Baixa os dois modelos Ollama necessários:
#      - nomic-embed-text  → gera embeddings dos documentos e das queries
#      - llama3.2:1b       → LLM de geração de resposta (roda em ~4 GB de RAM)
#
# Uso:
#   chmod +x setup.sh
#   ./setup.sh

set -e  # aborta imediatamente se qualquer comando falhar

# ── Cores para output legível ──────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # sem cor

info()    { echo -e "${GREEN}[setup]${NC} $1"; }
warning() { echo -e "${YELLOW}[aviso]${NC} $1"; }
error()   { echo -e "${RED}[erro]${NC} $1"; exit 1; }

# ── 1. Verificar Python 3.10+ ──────────────────────────────────────────────────
info "Verificando Python..."

if ! command -v python3 &>/dev/null; then
    error "Python3 não encontrado. Instale Python 3.10 ou superior."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    error "Python $PYTHON_VERSION encontrado, mas é necessário 3.10+."
fi

info "Python $PYTHON_VERSION encontrado. OK."

# ── 2. Verificar Ollama ────────────────────────────────────────────────────────
info "Verificando Ollama..."

if ! command -v ollama &>/dev/null; then
    error "Ollama não encontrado. Instale em https://ollama.com e tente novamente."
fi

# Verifica se o serviço está rodando (ollama serve)
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    warning "O serviço Ollama não está rodando. Iniciando em background..."
    ollama serve &>/dev/null &
    sleep 3  # aguarda o serviço subir

    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        error "Não foi possível conectar ao Ollama em http://localhost:11434. Rode 'ollama serve' manualmente."
    fi
fi

info "Ollama encontrado e rodando. OK."

# ── 3. Criar virtualenv ────────────────────────────────────────────────────────
if [ -d "venv" ]; then
    warning "Pasta ./venv já existe — pulando criação."
else
    info "Criando virtualenv em ./venv..."
    python3 -m venv venv
    info "Virtualenv criado. OK."
fi

# ── 4. Instalar dependências Python ───────────────────────────────────────────
info "Instalando dependências do requirements.txt..."
./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet
info "Dependências instaladas. OK."

# ── 5. Baixar modelos Ollama ───────────────────────────────────────────────────
# nomic-embed-text: modelo leve especializado em embeddings (~274 MB)
info "Baixando modelo de embeddings: nomic-embed-text..."
ollama pull nomic-embed-text

# llama3.2:1b: LLM de geração, menor da família LLaMA 3.2 (~1.3 GB)
# Para hardware mais robusto, troque por llama3.1:8b em config.py
info "Baixando modelo de geração: llama3.2:1b (pode demorar na primeira vez)..."
ollama pull llama3.2:1b

# ── Concluído ──────────────────────────────────────────────────────────────────
echo ""
info "Setup concluído! Próximos passos:"
echo ""
echo "  1. Ative o virtualenv:"
echo "       source venv/bin/activate"
echo ""
echo "  2. Ingira os documentos de exemplo:"
echo "       python ingest.py"
echo ""
echo "  3. Suba o backend (terminal 1):"
echo "       uvicorn backend:app --reload --port 8000"
echo ""
echo "  4. Suba o frontend (terminal 2):"
echo "       streamlit run frontend.py"
echo ""
echo "  Acesse: http://localhost:8501"
