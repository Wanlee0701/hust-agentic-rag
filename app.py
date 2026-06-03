"""
Main Streamlit Application — Student Regulation Chatbot
Kết nối đầy đủ với StudentRegulationAgent
"""
import os
import sys
import io
import logging
from pathlib import Path

import streamlit as st

# Fix encoding Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Kiểm tra Ollama                                                      #
# ------------------------------------------------------------------ #
def check_ollama_status() -> tuple[bool, list[str]]:
    """Kiểm tra Ollama có chạy không và model nào available"""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            return True, models
    except Exception:
        pass
    return False, []


# ------------------------------------------------------------------ #
# Cache Agent — chỉ khởi tạo 1 lần                                   #
# ------------------------------------------------------------------ #
@st.cache_resource(show_spinner=False)
def load_agent():
    """Khởi tạo StudentRegulationAgent (cached, chỉ chạy 1 lần)"""
    from src.agent import StudentRegulationAgent
    return StudentRegulationAgent(config_path="./config.yaml")


# ------------------------------------------------------------------ #
# Helper: màu confidence                                              #
# ------------------------------------------------------------------ #
def confidence_color(conf: float) -> str:
    if conf >= 0.75:
        return "🟢"
    elif conf >= 0.45:
        return "🟡"
    else:
        return "🔴"


def confidence_label(conf: float) -> str:
    if conf >= 0.75:
        return "Cao"
    elif conf >= 0.45:
        return "Trung bình"
    else:
        return "Thấp"


# ------------------------------------------------------------------ #
# Main App                                                            #
# ------------------------------------------------------------------ #
def main():
    # Page config
    st.set_page_config(
        page_title="Chatbot Quy chế Sinh viên — ĐHBK Hà Nội",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ---- Custom CSS -----------------------------------------------
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(15, 52, 96, 0.4);
    }
    .main-header h1 {
        color: #e2e8f0;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
    }
    .main-header p { color: #94a3b8; font-size: 0.95rem; margin: 0; }

    .chat-user {
        background: linear-gradient(135deg, #0f3460, #533483);
        color: white;
        padding: 0.9rem 1.2rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0 0.5rem 15%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-size: 0.95rem;
    }
    .chat-bot {
        background: #1e293b;
        color: #e2e8f0;
        padding: 1rem 1.3rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 15% 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        border-left: 3px solid #3b82f6;
        font-size: 0.93rem;
        line-height: 1.6;
    }
    .confidence-bar {
        background: #0f172a;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .source-tag {
        display: inline-block;
        background: #1e3a5f;
        color: #93c5fd;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        margin: 2px 3px;
    }
    .status-online { color: #4ade80; font-weight: 600; }
    .status-offline { color: #f87171; font-weight: 600; }
    .example-btn {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.5rem 0.8rem;
        color: #94a3b8;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #0f172a; }
    [data-testid="stSidebar"] * { color: #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

    # ---- Session State -------------------------------------------
    if "messages" not in st.session_state:
        st.session_state.messages = []  # [{role, content, meta}]
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "agent_error" not in st.session_state:
        st.session_state.agent_error = None

    # ---- Sidebar -------------------------------------------------
    with st.sidebar:
        st.markdown("## 🎓 HUST Chatbot")
        st.markdown("*Trợ lý AI về Quy chế Sinh viên*")
        st.divider()

        # Ollama Status
        ollama_ok, models = check_ollama_status()
        has_mistral = any("mistral" in m.lower() for m in models)
        if ollama_ok and has_mistral:
            st.markdown('<span class="status-online">● Ollama Online</span>', unsafe_allow_html=True)
            st.caption(f"Model: {', '.join(m for m in models if 'mistral' in m.lower())}")
        elif ollama_ok:
            st.markdown('<span class="status-offline">● Ollama: thiếu Mistral</span>', unsafe_allow_html=True)
            st.caption("Chạy: `ollama pull mistral`")
        else:
            st.markdown('<span class="status-offline">● Ollama Offline</span>', unsafe_allow_html=True)
            st.caption("Chạy: `ollama serve`")

        st.divider()

        # Agent Loading
        st.markdown("### ⚙️ Cài đặt")
        if st.button("🚀 Khởi tạo / Reload Agent", use_container_width=True):
            st.session_state.agent = None
            st.session_state.agent_error = None
            st.rerun()

        show_reasoning = st.checkbox("🔍 Hiển thị quá trình suy luận", value=True)
        show_sources = st.checkbox("📚 Hiển thị nguồn tài liệu", value=True)

        st.divider()

        # Chroma DB Info
        chroma_path = Path("./data/chroma/chroma.sqlite3")
        if chroma_path.exists():
            size_mb = chroma_path.stat().st_size / 1024 / 1024
            st.markdown("### 🗄️ Vector Database")
            st.caption(f"Chroma DB: {size_mb:.1f} MB")
            chunks = list(Path("./data/chunks").glob("*.json"))
            st.caption(f"Tài liệu: {len(chunks)} files")
        else:
            st.warning("⚠️ Chưa có Vector DB")

        st.divider()

        if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.markdown("""
        **📄 Tài liệu có sẵn:**
        - Quy chế đào tạo 2025
        - Quy chế công tác SV
        - Học bổng TDN & KKHT
        - Chuẩn ngoại ngữ K65/68/70
        - Chuyển tiếp kỹ sư 180TC
        """)

    # ---- Main Header ---------------------------------------------
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Chatbot Quy chế Sinh viên — ĐHBK Hà Nội</h1>
        <p>Hỏi bất kỳ điều gì về quy định học tập, học bổng, ngoại ngữ, học phí...</p>
    </div>
    """, unsafe_allow_html=True)

    # ---- Load Agent (lazy, cached) --------------------------------
    if st.session_state.agent is None and st.session_state.agent_error is None:
        with st.spinner("⏳ Đang khởi tạo AI Agent (lần đầu có thể mất 30-60 giây)..."):
            try:
                st.session_state.agent = load_agent()
            except Exception as e:
                st.session_state.agent_error = str(e)
                logger.error(f"Agent load failed: {e}")

    if st.session_state.agent_error:
        st.error(f"❌ Không thể khởi tạo Agent: {st.session_state.agent_error}")
        st.info("Kiểm tra: Ollama đang chạy? Chroma DB đã có dữ liệu?")
        return

    agent = st.session_state.agent

    # ---- Example Questions ---------------------------------------
    if not st.session_state.messages:
        st.markdown("### 💡 Câu hỏi gợi ý")
        example_questions = [
            "Bao nhiêu tín chỉ thì tốt nghiệp cử nhân?",
            "GPA bao nhiêu thì bị cảnh báo học vụ?",
            "Điều kiện nhận học bổng Trần Đại Nghĩa là gì?",
            "Chuẩn ngoại ngữ của sinh viên K68?",
            "Sinh viên bị điểm liệt khi nào?",
            "Học phí nếu rút học phần sau 7 tuần thì sao?",
        ]
        cols = st.columns(2)
        for idx, q in enumerate(example_questions):
            col = cols[idx % 2]
            if col.button(f"📌 {q}", key=f"ex_{idx}", use_container_width=True):
                st.session_state._pending_question = q
                st.rerun()

    # ---- Chat History --------------------------------------------
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        meta = msg.get("meta", {})

        if role == "user":
            st.markdown(f'<div class="chat-user">👤 {content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bot">🤖 {content}</div>', unsafe_allow_html=True)

            # Confidence
            conf = meta.get("confidence", 0)
            if conf > 0:
                icon = confidence_color(conf)
                label = confidence_label(conf)
                st.markdown(
                    f'<div class="confidence-bar">{icon} Độ tin cậy: <strong>{conf:.0%}</strong> ({label})</div>',
                    unsafe_allow_html=True,
                )

            # Sources
            sources = meta.get("sources", [])
            if show_sources and sources:
                src_html = " ".join(f'<span class="source-tag">📄 {s}</span>' for s in sources)
                st.markdown(f"**Nguồn:** {src_html}", unsafe_allow_html=True)

            # Reasoning steps
            steps = meta.get("steps", [])
            if show_reasoning and steps:
                with st.expander(f"🔍 Quá trình suy luận ({len(steps)} bước)", expanded=False):
                    for step in steps:
                        st.markdown(
                            f"**[Bước {step['iteration']}] {step['action']}**  \n"
                            f"*Suy nghĩ:* {step['thought']}  \n"
                            f"*Quan sát:* {step['observation'][:200]}"
                        )
                        st.divider()

    # ---- Chat Input ----------------------------------------------
    st.markdown("---")
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Nhập câu hỏi:",
            placeholder="Ví dụ: Điều kiện nhận học bổng KKHT là gì?",
            key="chat_input",
            label_visibility="collapsed",
        )
    with col_btn:
        submit = st.button("Gửi ➤", use_container_width=True, type="primary")

    # Xử lý câu hỏi từ example buttons
    pending = getattr(st.session_state, "_pending_question", None)
    if pending:
        user_input = pending
        del st.session_state._pending_question
        submit = True

    # ---- Process Question ----------------------------------------
    if submit and user_input and user_input.strip():
        question = user_input.strip()

        # Thêm vào history
        st.session_state.messages.append({"role": "user", "content": question})

        # Gọi agent
        with st.spinner("🤖 Đang phân tích và tìm kiếm..."):
            try:
                result = agent.answer_question(question)

                answer = result.get("answer", "Không có câu trả lời")
                confidence = result.get("confidence", 0.0)
                success = result.get("success", False)
                state = result.get("state")

                sources = state.sources if state else []
                steps = []
                if state and state.steps:
                    steps = [
                        {
                            "iteration": s.iteration,
                            "action": s.action,
                            "thought": s.thought,
                            "observation": s.observation,
                        }
                        for s in state.steps
                    ]

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "meta": {
                        "confidence": confidence,
                        "success": success,
                        "sources": sources,
                        "steps": steps,
                    },
                })

            except Exception as e:
                logger.error(f"Agent error: {e}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"❌ Lỗi hệ thống: {str(e)}. Vui lòng thử lại.",
                    "meta": {},
                })

        st.rerun()

    # ---- Footer --------------------------------------------------
    st.markdown("""
    <div style='text-align:center; color:#475569; margin-top:2rem; font-size:0.82rem;'>
        🎓 HUST Student Regulation Chatbot v2.0 &nbsp;|&nbsp;
        Powered by AgenticRAG + Mistral 7B + Chroma DB &nbsp;|&nbsp;
        Dữ liệu cục bộ — Bảo mật tuyệt đối
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    import streamlit as st
    main()
