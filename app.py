"""
Main Streamlit Application Entry Point
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    logger.info("Starting Student Regulation Chatbot...")
    
    import streamlit as st
    
    # Page config
    st.set_page_config(
        page_title="Student Regulation Chatbot",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar
    with st.sidebar:
        st.title("📚 Student Regulation Chatbot")
        st.markdown("---")
        st.markdown("""
        ### About
        AI-powered chatbot for student regulations using AgenticRAG with local models.
        
        **Technology:**
        - AgenticRAG (Reasoning + Retrieval)
        - Ollama + Mistral 7B (local LLM)
        - Chroma (vector database)
        - LangChain (orchestration)
        """)
        
        st.markdown("---")
        
        # Settings
        st.subheader("⚙️ Settings")
        temperature = st.slider("Temperature (creativity)", 0.0, 1.0, 0.3, 0.1)
        top_k = st.slider("Top Results", 1, 10, 5)
        
        st.markdown("---")
        st.markdown("""
        **Getting Started:**
        1. Place PDFs in `knowledge_base/raw/`
        2. Run data preparation
        3. Ask questions!
        
        **Documentation:**
        See `/docs/README.md` for full guide
        """)
    
    # Main area
    st.title("🤖 Student Regulation Assistant")
    st.markdown("Ask questions about student regulations and policies")
    
    # Info boxes
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", "Ready ✓")
    with col2:
        st.metric("Model", "Mistral 7B")
    with col3:
        st.metric("Mode", "Local Only")
    
    st.markdown("---")
    
    # Chat interface
    st.subheader("💬 Ask a Question")
    
    user_input = st.text_input(
        "Your question:",
        placeholder="E.g., What are the academic probation requirements?",
        key="user_input"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        submit_btn = st.button("🔍 Search", use_container_width=True)
    with col2:
        clear_btn = st.button("Clear", use_container_width=True)
    
    if submit_btn and user_input:
        st.info("⏳ Processing your question...")
        # TODO: Integrate with agent
        st.warning("⚠️ Implementation in progress. Connect to agent module.")
    
    if clear_btn:
        st.rerun()
    
    st.markdown("---")
    
    # Example questions
    st.subheader("💡 Example Questions")
    examples = [
        "What is the GPA requirement for Dean's List?",
        "How do I appeal an academic penalty?",
        "What are the attendance policies?",
        "How is scholastic standing determined?",
        "What conducts are considered academic dishonesty?"
    ]
    
    for example in examples:
        if st.button(f"📌 {example}", use_container_width=True):
            st.session_state.user_input = example
            st.rerun()
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style='text-align: center; color: gray; margin-top: 40px'>
    <small>Student Regulation Chatbot v1.0 | Powered by AgenticRAG | Local Models</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
