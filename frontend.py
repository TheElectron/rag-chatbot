"""
frontend.py — interface Streamlit do Chatbot.

Responsabilidade única: UI.
Este arquivo nunca importa ChromaDB, Ollama ou LangChain.
Toda a inteligência vive no backend — o frontend só faz chamadas HTTP.
"""

import httpx
import streamlit as st

from config import BACKEND_URL

st.set_page_config(page_title="Chatbot + RAG", page_icon="⚡", layout="centered")

# Nota: st.session_state persiste o histórico entre os re-renders da página.
# Cada interação do usuário dispara um re-render no Streamlit.
if "historico" not in st.session_state:
    st.session_state.historico = []  # lista de {"role": ..., "content": ..., "fontes": [...]}

# ───────────────────────────────────────────────────────────── Estilos ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
  /* ── Fonte e fundo ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .stApp { background-color: #0f1117; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #1e2535;
  }

  [data-testid="stSidebar"] h1 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    letter-spacing: 0.03em;
    padding-bottom: 0.25rem;
  }

  /* ── Badge RAG ── */
  .rag-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin-bottom: 0.5rem;
  }
  .rag-on  { background: #0d2b1e; color: #34d399; border: 1px solid #065f46; }
  .rag-off { background: #2b1a0d; color: #fb923c; border: 1px solid #7c2d12; }

  /* ── Cabeçalho principal ── */
  .main-header {
    padding: 2rem 0 1.5rem;
    border-bottom: 1px solid #1e2535;
    margin-bottom: 1.5rem;
  }
  .main-header h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f1f5f9;
    margin: 0 0 0.25rem;
    letter-spacing: -0.02em;
  }
  .main-header p {
    font-size: 0.82rem;
    color: #64748b;
    margin: 0;
  }

  /* ── Modo atual (pill abaixo do título) ── */
  .mode-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 500;
    margin-top: 0.6rem;
  }
  .mode-pill.on  { background:#0d2b1e; color:#34d399; border:1px solid #065f46; }
  .mode-pill.off { background:#2b1a0d; color:#fb923c; border:1px solid #7c2d12; }

  /* ── Mensagens do chat ── */
  [data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.25rem 0 !important;
  }

  /* Balão do usuário */
  [data-testid="stChatMessage"][data-testid*="user"] .stMarkdown p,
  [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {
    background: #1e3a5f;
    border: 1px solid #1e40af33;
    border-radius: 16px 16px 4px 16px;
    padding: 0.75rem 1rem;
    color: #e2e8f0;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  /* Balão do assistente */
  [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    background: #1a1f2e;
    border: 1px solid #1e2535;
    border-radius: 16px 16px 16px 4px;
    padding: 0.75rem 1rem;
    color: #cbd5e1;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  /* ── Expander de fontes ── */
  [data-testid="stExpander"] {
    background: #111827 !important;
    border: 1px solid #1e2535 !important;
    border-radius: 8px !important;
    margin-top: 0.5rem;
  }
  [data-testid="stExpander"] summary {
    color: #64748b !important;
    font-size: 0.75rem !important;
  }

  /* ── Input ── */
  [data-testid="stChatInput"] textarea {
    background: #161b27 !important;
    border: 1px solid #1e2535 !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.9rem !important;
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px #3b82f620 !important;
  }

  /* ── Botões sidebar ── */
  [data-testid="stSidebar"] .stButton button {
    background: #1e2535;
    border: 1px solid #2d3748;
    color: #94a3b8;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
    transition: all 0.15s ease;
  }
  [data-testid="stSidebar"] .stButton button:hover {
    background: #2d3748;
    color: #e2e8f0;
    border-color: #3b82f6;
  }

  /* Botão destrutivo (limpar banco) */
  [data-testid="stSidebar"] .btn-danger button {
    background: #2b0d0d;
    border: 1px solid #7f1d1d;
    color: #f87171;
  }
  [data-testid="stSidebar"] .btn-danger button:hover {
    background: #450a0a;
    border-color: #dc2626;
    color: #fca5a5;
  }

  /* ── Status de serviços ── */
  .service-status {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 0.5rem 0;
  }
  .status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #1a1f2e;
    border: 1px solid #1e2535;
    border-radius: 8px;
    padding: 6px 12px;
  }
  .status-label {
    font-size: 0.78rem;
    color: #64748b;
    font-weight: 500;
  }
  .status-flag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
  }
  .flag-ok  { background: #0d2b1e; color: #34d399; border: 1px solid #065f46; }
  .flag-nok { background: #2b0d0d; color: #f87171; border: 1px solid #7f1d1d; }
  .status-chunks {
    font-size: 0.72rem;
    color: #475569;
    text-align: right;
    margin-top: 2px;
  }

  /* ── Divider ── */
  hr { border-color: #1e2535 !important; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 4px; }

  /* ── Toggle ── */
  [data-testid="stToggle"] label { color: #94a3b8 !important; font-size: 0.85rem !important; }

  /* ── Responsividade ── */

  /* Tablet (até 1024px) — ajusta padding do cabeçalho e tamanho dos balões */
  @media (max-width: 1024px) {
    .main-header { padding: 1.5rem 0 1rem; }
    .main-header h1 { font-size: 1.35rem; }
  }

  /* Mobile (até 768px) — sidebar vira gaveta (Streamlit nativo), conteúdo ocupa a tela toda */
  @media (max-width: 768px) {
    .main-header { padding: 1rem 0 0.75rem; }
    .main-header h1 { font-size: 1.1rem; }
    .main-header p { font-size: 0.75rem; }

    .mode-pill { font-size: 0.65rem; padding: 2px 8px; }

    /* Balões ocupam largura total sem margem excessiva */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown,
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
      padding: 0.6rem 0.75rem;
      font-size: 0.85rem;
      border-radius: 12px;
    }

    /* Input levemente menor */
    [data-testid="stChatInput"] textarea { font-size: 0.85rem !important; }
  }

  /* Mobile pequeno (até 480px) — compacta ainda mais */
  @media (max-width: 480px) {
    .main-header h1 { font-size: 1rem; }
    .rag-badge { font-size: 0.68rem; padding: 3px 8px; }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown,
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
      font-size: 0.82rem;
      padding: 0.5rem 0.65rem;
    }
  }
</style>
""", unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────── Comunicação com o backend ─────────────────────────────────────────────────────────────

def verificar_saude() -> dict:
    """
        Chama GET /health e retorna o status dos serviços.
    """
    try:
        resp = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.json()
    except Exception:
        return {"status": "indisponível", "ollama": False, "chromadb": False, "documentos_no_banco": 0}


def enviar_mensagem(mensagem: str, rag_enabled: bool) -> dict:
    """
        Chama POST /chat com a mensagem, o histórico completo e a flag RAG.
    """
    payload = {
        "mensagem": mensagem,
        "historico": st.session_state.historico,
        "rag_enabled": rag_enabled,
    }
    resp = httpx.post(f"{BACKEND_URL}/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def disparar_ingestao() -> dict:
    """
        Chama POST /ingest para re-ingerir os documentos sem usar o terminal.
    """
    resp = httpx.post(f"{BACKEND_URL}/ingest", timeout=300)
    resp.raise_for_status()
    return resp.json()


def limpar_banco() -> dict:
    """
        Chama DELETE /collection para remover todos os chunks do ChromaDB.
    """
    resp = httpx.delete(f"{BACKEND_URL}/collection", timeout=30)
    resp.raise_for_status()
    return resp.json()


# ───────────────────────────────────────────────────────────── Sidebar ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚡ Chatbot + RAG")

    st.markdown("---")

    # Toggle RAG — o destaque didático do projeto.
    # Ligado:    pipeline completo (retrieve → augment → generate)
    # Desligado: apenas o LLM base, sem acesso aos documentos
    rag_enabled: bool = st.toggle(
        "Retrieval-Augmented Generation",
        value=True,
        help=(
            "Ligado: o modelo busca trechos relevantes nos documentos antes de responder.\n\n"
            "Desligado: o modelo responde apenas com seu conhecimento de treinamento."
        ),
    )

    st.markdown("---")

    # Status verificado automaticamente a cada re-render — sem necessidade de botão
    saude = verificar_saude()

    def _flag(ok: bool) -> str:
        return '<span class="status-flag flag-ok">⬤ OK</span>' if ok else '<span class="status-flag flag-nok">⬤ NOK</span>'

    st.markdown("##### Serviços")
    st.markdown(f"""
    <div class="service-status">
      <div class="status-row">
        <span class="status-label">Ollama</span>{_flag(saude["ollama"])}
      </div>
      <div class="status-row">
        <span class="status-label">ChromaDB</span>{_flag(saude["chromadb"])}
      </div>
    </div>
    <div class="status-chunks">📦 {saude["documentos_no_banco"]} chunks no banco</div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("##### Documentos")

    if st.button("⬆ Ingerir documentos", use_container_width=True):
        with st.spinner("Processando..."):
            try:
                resultado = disparar_ingestao()
                st.success(resultado["mensagem"])
            except Exception as e:
                st.error(f"Erro: {e}")

    st.markdown('<div class="btn-danger">', unsafe_allow_html=True)
    if st.button("✕ Limpar banco vetorial", use_container_width=True):
        with st.spinner("Limpando..."):
            try:
                resultado = limpar_banco()
                st.warning(resultado["mensagem"])
            except Exception as e:
                st.error(f"Erro: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🗑 Limpar conversa", use_container_width=True):
        st.session_state.historico = []
        st.rerun()

    st.markdown(
        "<div style='position:fixed;bottom:1.5rem;font-size:0.7rem;color:#334155;'>"
        "TheElectron</div>",
        unsafe_allow_html=True,
    )


# ───────────────────────────────────────────────────────────── Chat ─────────────────────────────────────────────────────────────

mode_class = "on" if rag_enabled else "off"
mode_label = "RAG ativado — respostas baseadas nos documentos" if rag_enabled else "RAG desativado — apenas modelo base"
mode_icon  = "⬤" if rag_enabled else "⬤"

st.markdown(f"""
<div class="main-header">
  <h1>Chatbot + RAG</h1>
  <span class="mode-pill {mode_class}">{mode_icon} &nbsp;{mode_label}</span>
</div>
""", unsafe_allow_html=True)

# Renderiza o histórico da conversa
for msg in st.session_state.historico:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("fontes"):
            with st.expander("📄 Fontes consultadas"):
                for fonte in msg["fontes"]:
                    st.caption(f"`{fonte}`")

if prompt := st.chat_input("Faça uma pergunta sobre os documentos..."):

    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.historico.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                resultado = enviar_mensagem(prompt, rag_enabled)
            except httpx.ConnectError:
                st.error(
                    "Não foi possível conectar ao backend.\n\n"
                    "```\nuvicorn backend:app --reload --port 8000\n```"
                )
                st.session_state.historico.pop()
                st.stop()
            except Exception as e:
                st.error(f"Erro ao processar a resposta: {e}")
                st.session_state.historico.pop()
                st.stop()

        resposta: str = resultado["resposta"]
        fontes: list[str] = resultado.get("fontes", [])

        st.markdown(resposta)

        if fontes:
            with st.expander("📄 Fontes consultadas"):
                for fonte in fontes:
                    st.caption(f"`{fonte}`")

    st.session_state.historico.append({"role": "assistant", "content": resposta, "fontes": fontes})
